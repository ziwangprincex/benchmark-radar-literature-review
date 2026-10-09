"""MedHELM 公开逐题结果 -> 医疗领域 model_failure 旁证。不调模型。

MedHELM（Stanford CRFM，Nature Medicine 2025）把 13 个模型在每个公开题集上的逐题输出与判分
放在公开存储桶 gs://crfm-helm-public/medhelm/benchmark_output/runs/v4.0.0/，可以直接 HTTP 下载。

只取有确定判分（精确匹配/数值判对）的公开题集，不用 LLM 陪审团打分的开放题，避免"拿模型判模型"：
  medcalc_bench   临床评分/剂量计算        -> 数值/计算
  medec           病历中的诊断/治疗错误识别 -> 安全/风险（漏掉病历里的错误）
  medhallu        判断答案是否有医学幻觉    -> 证据/溯源（答案是否被给定知识支撑）
  race_based_med  识别基于种族的有害医学内容 -> 安全/风险

复现过滤：同一道题被 >= min_fail 个模型做错才算"失败模式"，偶发错误不算。
每个题集入库一条（url 指向该题集的 instances.json），内容写清楚模型数、复现失败题数和代表题。
canonical_url 会去掉 query/fragment，同一题集的逐题条目会被当成重复，所以按题集粒度入库。

用法：python3 -m radar.evidence.import_medhelm [--min-fail 10] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from collections import Counter
from typing import Any

import requests

from radar.core.radar_core import extract_pending, insert_source_item, now_iso

BUCKET = "crfm-helm-public"
RELEASE = "v4.0.0"
PREFIX = f"medhelm/benchmark_output/runs/{RELEASE}/"
LIST_API = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o"
OBJ = f"https://storage.googleapis.com/{BUCKET}/"
LEADERBOARD = f"https://crfm.stanford.edu/helm/medhelm/{RELEASE}/"

SCENARIOS = {
    "medcalc_bench": {"metric": "medcalc_bench_accuracy", "concerns": ["数值/计算"],
                      "tasks": ["推理/计算"], "inputs": ["长文档"],
                      "cn": "MedCalc-Bench：从病历里算临床评分和剂量"},
    "medec": {"metric": "medec_error_flag_accuracy", "concerns": ["安全/风险"],
              "tasks": ["审查/核查"], "inputs": ["长文档"],
              "cn": "MEDEC：找出病历里写错的诊断或治疗"},
    "medhallu": {"metric": "exact_match", "concerns": ["证据/溯源"],
                 "tasks": ["审查/核查"], "inputs": ["多文档/知识库"],
                 "cn": "MedHallu：判断医学回答是否有幻觉（是否被给定知识支撑）"},
    "race_based_med": {"metric": "exact_match", "concerns": ["安全/风险"],
                       "tasks": ["分类/识别"], "inputs": [],
                       "cn": "RaceBasedMed：识别基于种族的有害医学内容"},
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "BenchmarkIdeaRadar/1.0"
    return s


def list_runs(s: requests.Session) -> list[str]:
    out, token = [], None
    while True:
        params = {"prefix": PREFIX, "delimiter": "/", "maxResults": 1000}
        if token:
            params["pageToken"] = token
        d = s.get(LIST_API, params=params, timeout=60).json()
        out += [p[len(PREFIX):].rstrip("/") for p in d.get("prefixes", [])]
        token = d.get("nextPageToken")
        if not token:
            return out


def fetch(s: requests.Session, run: str, name: str) -> Any:
    r = s.get(OBJ + urllib.parse.quote(PREFIX + run + "/" + name), timeout=120)
    r.raise_for_status()
    return r.json()


def model_of(run: str) -> str:
    for part in run.split(":", 1)[1].split(","):
        if part.startswith("model="):
            return part[len("model="):]
    return run


def build(min_fail: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    s = _session()
    runs = list_runs(s)
    items, summary = [], {}
    for scen, cfg in SCENARIOS.items():
        mine = [r for r in runs if r.split(":", 1)[0] == scen]
        if not mine:
            continue
        instances = {x["id"]: x for x in fetch(s, mine[0], "instances.json")}
        fails: dict[str, list[str]] = {}
        acc = {}
        for run in mine:
            preds = [p for p in fetch(s, run, "display_predictions.json") if p.get("train_trial_index", 0) == 0]
            scored = [p for p in preds if cfg["metric"] in p["stats"]]
            if not scored:
                continue
            m = model_of(run)
            acc[m] = round(sum(p["stats"][cfg["metric"]] for p in scored) / len(scored), 3)
            for p in scored:
                if p["stats"][cfg["metric"]] < 1:
                    fails.setdefault(p["instance_id"], []).append(m)
        n_models = len(acc)
        hard = sorted(((iid, ms) for iid, ms in fails.items() if len(ms) >= min(min_fail, n_models)),
                      key=lambda x: -len(x[1]))
        examples = []
        for iid, ms in hard[:3]:
            x = instances.get(iid, {})
            ref = next((r["output"]["text"] for r in x.get("references", []) if "correct" in (r.get("tags") or [])), "")
            examples.append({"instance_id": iid, "failed_models": len(ms),
                             "input": (x.get("input", {}).get("text") or "")[:300], "reference": ref[:200]})
        summary[scen] = {"models": n_models, "instances": len(instances), "reproducible_failures": len(hard),
                         "accuracy": acc, "min_fail": min_fail}
        best = max(acc.items(), key=lambda kv: kv[1]) if acc else ("-", 0)
        worst = min(acc.items(), key=lambda kv: kv[1]) if acc else ("-", 0)
        ex_txt = " ".join(f"[{e['instance_id']}，{e['failed_models']}/{n_models} 个模型做错] 题目：{e['input'][:160]}… 正确答案：{e['reference'][:100]}"
                          for e in examples)
        items.append({
            "radar": "model_failure", "source_id": "medhelm-public-results",
            "title": f"医疗 · MedHELM 公开逐题结果：{cfg['cn']}",
            "content": (f"MedHELM {RELEASE} 公开了 {n_models} 个模型在 {cfg['cn'].split('：')[0]} {len(instances)} 道题上的逐题输出与判分"
                        f"（判分为精确匹配/数值判对，非 LLM 打分）。准确率最高 {best[0]} {best[1]:.0%}，最低 {worst[0]} {worst[1]:.0%}。"
                        f"至少 {min(min_fail, n_models)} 个模型都做错的题 {len(hard)} 道。代表题：{ex_txt}"),
            "url": OBJ + urllib.parse.quote(PREFIX + mine[0] + "/instances.json"),
            "published_at": "2025-10-01", "evidence_role": "raw_source", "source_type": "eval_run_or_case",
            "source_quality": "primary", "http_status": 200, "organization": "Stanford CRFM / MedHELM",
            "source_version": f"MedHELM {RELEASE}", "run_id": f"{RELEASE}/{scen}", "retrieved_at": now_iso(),
            "raw_data": {**summary[scen], "examples": examples, "leaderboard": LEADERBOARD,
                         "concerns": cfg["concerns"], "tasks": cfg["tasks"], "inputs": cfg["inputs"]},
        })
    return items, summary


def run(min_fail: int = 10, dry_run: bool = False) -> dict[str, Any]:
    items, summary = build(min_fail)
    if dry_run:
        return {"dry_run": True, "summary": summary}
    st = Counter(insert_source_item(it)[1] for it in items)
    return {"insert": dict(st), "extract": extract_pending(), "summary": summary}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-fail", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    print(json.dumps(run(a.min_fail, a.dry_run), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
