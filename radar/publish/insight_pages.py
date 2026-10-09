from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from radar.evidence.evidence_retrieval import retrieval_log
from radar.core.radar_core import BASE_DIR, get_idea, init_db, list_failure_cases, list_ideas, source_claim_trace, strip_feed_prefix

OUTPUT_DIR = BASE_DIR / "outputs" / "insights"
RADAR_LABELS = {
    "benchmark": "Benchmark Scout",
    "workflow": "Expert Workflow Scout",
    "product_agent": "Product / Agent Scout",
    "model_failure": "Model Failure Scout",
}
RADAR_COLORS = {
    "benchmark": "#3157a4",
    "workflow": "#087a61",
    "product_agent": "#8655a8",
    "model_failure": "#b5483f",
}
SCORE_LABELS = {
    "real_world_value": ("Real-world Value", 20),
    "model_weakness": ("Model Weakness", 20),
    "model_differentiation": ("Model Differentiation", 15),
    "novelty": ("Novelty", 15),
    "evaluability": ("Evaluability", 15),
    "data_feasibility": ("Data Feasibility", 10),
    "expert_cost": ("Expert Cost", 5),
}


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def slugify(value: str) -> str:
    ascii_slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return ascii_slug[:48] or "idea"


def is_public_link(url: str) -> bool:
    return urlparse(url or "").scheme in {"http", "https"}


def public_base() -> str:
    config_path = BASE_DIR / "config" / "deployment.json"
    if config_path.exists():
        configured = json.loads(config_path.read_text(encoding="utf-8")).get("public_base_url", "").strip().rstrip("/")
        if configured:
            return configured
    configured = os.getenv("RADAR_PUBLIC_BASE_URL", "").strip().rstrip("/")
    return configured or "http://127.0.0.1:5000/insights"


def insight_filename(idea: dict) -> str:
    return f"idea-{idea['id']}-{slugify(idea['idea_name'])}.html"


def insight_url(idea: dict, base_url: str | None = None) -> str:
    return f"{(base_url or public_base()).rstrip('/')}/{insight_filename(idea)}"


def evidence_filename(idea_id: int, source_item_id: int) -> str:
    return f"idea-{idea_id}-evidence-{source_item_id}.html"


def group_filename(idea_id: int, radar: str) -> str:
    return f"idea-{idea_id}-evidence-{radar}.html"


def raw_filename(source_item_id: int) -> str:
    return f"raw-source-{source_item_id}.html"


def failure_case_filename(case_id: int) -> str:
    return f"failure-case-{case_id}.html"


def retrieval_filename(idea_id: int) -> str:
    return f"idea-{idea_id}-retrieval-log.html"


def coverage_filename(idea_id: int) -> str:
    return f"idea-{idea_id}-coverage-matrix.html"


def cite(ids: list[str], links: dict[str, str] | None = None) -> str:
    unique = list(dict.fromkeys(ids))
    return " ".join(
        f'<a class="citation" href="{esc((links or {}).get(x, "#" + x))}">[{esc(x)}]</a>'
        for x in unique
    )


def evidence_map(idea: dict) -> tuple[list[dict], dict[str, list[dict]]]:
    evidence = []
    groups: dict[str, list[dict]] = defaultdict(list)
    raw_records = [
        x for x in idea.get("evidence", [])
        if x.get("evidence_role") == "raw_source" and x.get("validation_status") in {"verified_source", "internal_record"}
    ]
    independent_records = []
    seen = set()
    for record in raw_records:
        independence_key = record.get("canonical_source_id") or record.get("canonical_url") or record.get("duplicate_group_id") or record["source_item_id"]
        if independence_key in seen:
            continue
        seen.add(independence_key)
        independent_records.append(record)
    for index, record in enumerate(independent_records, 1):
        item = dict(record)
        item["citation_id"] = f"S{index}"
        evidence.append(item)
        groups[item["radar"]].append(item)
    return evidence, groups


def citations_for(groups: dict[str, list[dict]], *radars: str) -> list[str]:
    return [x["citation_id"] for radar in radars for x in groups.get(radar, [])]


def evidence_cards(idea: dict, groups: dict[str, list[dict]]) -> str:
    cards = []
    for radar in ["benchmark", "workflow", "product_agent", "model_failure"]:
        records = groups.get(radar, [])
        color = RADAR_COLORS[radar]
        status = (idea.get("evidence_quality") or {}).get("radar_status", {}).get(radar, "unsupported")
        symbol = {"verified": "✓", "partial": "△", "hypothesis": "?", "unsupported": "×"}[status]
        group_link = group_filename(idea["id"], radar)
        if records:
            snippets = []
            for x in records[:5]:
                signal = strip_feed_prefix(x["failure_pattern"] or x["evaluation_gap"] or x["real_world_task"] or x["content"])
                snippets.append(
                    f'<li><span>{esc(signal[:240])}</span> '
                    f'<a class="citation" href="{evidence_filename(idea["id"], x["source_item_id"])}">查看证据 [{x["citation_id"]}] →</a></li>'
                )
            body = f'<ul>{"".join(snippets)}</ul>'
        else:
            body = '<p class="empty">当前未命中该 Radar；这是后续补证据的明确缺口。</p>'
        cards.append(
            f'<article class="radar-card" style="--radar:{color}">'
            f'<header><span></span><a href="{group_link}"><strong>{RADAR_LABELS[radar]}</strong></a><b>{symbol} {status.title()} · {len(records)}</b></header>'
            f'{body}<a href="{group_link}">查看该 Radar 全部证据 →</a></article>'
        )
    return "".join(cards)


def source_rows(idea: dict, evidence: list[dict]) -> str:
    rows = []
    for item in evidence:
        url = item.get("url") or ""
        if is_public_link(url):
            source_title = f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(item["title"])}</a>'
            link = f'<a href="{esc(url)}" target="_blank" rel="noopener">打开原始来源 ↗</a>'
        else:
            source_title = esc(item["title"])
            link = '<span class="internal">内部证据记录</span>'
        provenance = {
            "source_item_id": item["source_item_id"],
            "signal_id": item["signal_id"],
            "source_id": item["source_id"],
            "source_type": item.get("source_type"),
            "source_quality": item.get("source_quality"),
            "source_version": item.get("source_version"),
            "retrieved_at": item.get("retrieved_at"),
            "last_verified_at": item.get("last_verified_at"),
            "validation_status": item.get("validation_status"),
            "locator": item.get("locator"),
            "extractor": item["extractor_version"],
            "confidence": item["confidence"],
        }
        rows.append(
            f'<article class="source" id="{item["citation_id"]}">'
            f'<div class="source-id">[{item["citation_id"]}]</div><div><div class="source-meta">'
            f'<span style="color:{RADAR_COLORS[item["radar"]]}">{RADAR_LABELS[item["radar"]]}</span>'
            f' · {esc(item.get("published_at") or "日期未知")}</div><h3>{source_title}</h3>'
            f'<p>{esc(item["content"][:700])}</p><details><summary>Provenance 元数据</summary>'
            f'<pre>{esc(json.dumps(provenance, ensure_ascii=False, indent=2))}</pre></details>'
            f'<a href="{evidence_filename(idea["id"], item["source_item_id"])}">查看 Evidence Detail →</a> · '
            f'<a href="{raw_filename(item["source_item_id"])}">查看 Raw Source →</a> · {link}</div></article>'
        )
    return "".join(rows) or '<p class="empty">暂无来源。该 Idea 不应进入正式评审。</p>'


def render_detail(idea: dict, base_url: str) -> str:
    evidence, groups = evidence_map(idea)
    analysis_inputs = [
        x for x in idea.get("evidence", [])
        if x.get("evidence_role") != "raw_source" or x.get("validation_status") not in {"verified_source", "internal_record"}
    ]
    evidence_links = {
        x["citation_id"]: evidence_filename(idea["id"], x["source_item_id"])
        for x in evidence
    }
    benchmark_ids = citations_for(groups, "benchmark")
    workflow_ids = citations_for(groups, "workflow")
    failure_ids = citations_for(groups, "model_failure")
    why_ids = citations_for(groups, "product_agent", "model_failure", "benchmark")
    core_ids = list(dict.fromkeys(workflow_ids + failure_ids + benchmark_ids))
    failures = idea.get("expected_failure", [])
    quality = idea.get("evidence_quality") or {}
    radar_status = quality.get("radar_status") or {}
    status_symbol = {"verified": "✓", "partial": "△", "hypothesis": "?", "unsupported": "×"}
    radar_summary = " · ".join(
        f'{RADAR_LABELS[radar].replace(" Scout", "")} {status_symbol.get(radar_status.get(radar), "?")} {radar_status.get(radar, "unsupported").title()}'
        for radar in RADAR_LABELS
    )
    claim_blocks = []
    # claim 可能引用未通过校验或被去重的来源，这些来源没有 evidence 页，不能加链接
    published_sources = {x["source_item_id"] for x in evidence}
    for claim in quality.get("claims", []):
        evidence_rows = []
        for link in claim.get("evidence", []):
            source_id = link.get("source_item_id")
            label = f'[{esc(link.get("field_name") or "Evidence")}] {esc(link.get("title"))}'
            anchor = (
                f'<a href="{evidence_filename(idea["id"], source_id)}">{label}</a>'
                if source_id in published_sources else f'<span class="muted">{label}（来源未通过校验，未发布）</span>'
            )
            evidence_rows.append(
                f'<li>{anchor} '
                f'<span class="tag">{esc(link.get("support_relation"))}</span> '
                f'<span class="tag">{esc(link.get("evidence_status"))}</span> '
                f'<span class="tag">{esc(link.get("source_quality"))}</span><br><span class="muted">{esc(link.get("rationale"))}</span></li>'
            )
        evidence_markup = "".join(evidence_rows) or '<li class="muted">暂无有效Evidence，当前为Hypothesis / Unsupported。</li>'
        claim_blocks.append(
            f'<article class="evidence"><strong>{esc(claim["claim_type"])} · {esc(claim["status"].upper())}</strong>'
            f'<p>{esc(claim["claim_text"])}</p><ul>{evidence_markup}</ul></article>'
        )
    claims_by_type = {x["claim_type"]: x for x in quality.get("claims", [])}
    def claim_display(claim_type: str, fallback: str) -> str:
        claim = claims_by_type.get(claim_type) or {"claim_text": fallback, "status": "hypothesis"}
        status = claim.get("status", "hypothesis")
        prefix = "" if status == "verified" else f'{status.upper()} / 待验证：'
        return f'<span class="tag">{esc(status.upper())}</span> {esc(prefix + claim["claim_text"])}'
    core_claim_html = claim_display("core_insight", f'{idea["idea_name"]}值得作为独立Benchmark方向验证。')
    why_claim_html = claim_display("why_now", "相关能力正在进入应用阶段，应验证真实表现与边界。")
    gap_claim_html = claim_display("evaluation_gap", idea["evaluation_gap"])
    failure_claim_html = claim_display("model_failure", "当前模型可能存在可复现失败模式，需要Mini Eval验证。")
    mini = idea.get("mini_evals", [])
    latest = mini[0] if mini else None
    score_rows = []
    for key, (label, maximum) in SCORE_LABELS.items():
        value = idea.get("scores", {}).get(key, 0)
        width = max(0, min(100, value / maximum * 100))
        score_rows.append(
            f'<div class="score-row"><span>{label}</span><div class="score-track"><i style="width:{width}%"></i></div><b>{value}/{maximum}</b></div>'
        )
    failure_html = "".join(
        f'<li><strong>{esc(x.get("type"))}</strong> — {esc(x.get("description"))}</li>' for x in failures
    ) or '<li>等待 Mini Eval 验证失败模式。</li>'
    benchmark_html = "".join(f'<span class="chip">{esc(x)}</span>' for x in idea.get("existing_benchmark", [])) or '<span class="chip">暂无直接对标</span>'
    if latest:
        mini_result = (
            f'<div class="metric-grid"><div><small>题量</small><b>{latest["sample_size"]}</b></div>'
            f'<div><small>模型数</small><b>{latest["model_count"]}</b></div>'
            f'<div><small>SOTA</small><b>{latest["sota_score"]}%</b></div>'
            f'<div><small>模型极差</small><b>{latest["score_range"]}pt</b></div>'
            f'<div><small>Failure</small><b>{latest["reproducible_failure"]}</b></div>'
            f'<div><small>Judge一致性</small><b>{latest["judge_agreement"]}</b></div></div>'
        )
    else:
        mini_result = '<p class="empty">尚未执行 Mini Eval；以下为建议设计。</p>'
    missing = quality.get("missing_evidence", [])
    verification_html = ""
    if quality.get("needs_verification") or quality.get("conflicts"):
        missing_rows = "".join(f'<li>× {esc(x)} Evidence</li>' for x in missing)
        conflict_note = f'<p><strong>Source Conflict：</strong>{quality.get("conflicts")} 条Evidence与Claim冲突，必须人工审核；Raw Source优先。</p>' if quality.get("conflicts") else ""
        recommendations = "".join(
            f'<li>{esc(x)}</li>' for x in quality.get("recommended_validation", []) if x
        )
        verification_html = (
            '<section class="section ai-panel"><span class="evidence-label ai-label">NEEDS VERIFICATION</span>'
            f'<h2>Evidence不足或冲突，不自动补造证据</h2>{conflict_note}<ul>{missing_rows}</ul>'
            f'<p><strong>Recommended Validation：</strong></p><ul>{recommendations}</ul></section>'
        )
    page_url = insight_url(idea, base_url)
    analysis_notice = ""
    if analysis_inputs:
        rows = "".join(
            f'<li><strong>{esc(x["title"])}</strong> — 仅作为 Analysis Input，未计入 Raw Evidence；需补充原始记录、URL、Page/Section/Case ID 或附件。</li>'
            for x in analysis_inputs
        )
        analysis_notice = f'<section class="section ai-panel"><span class="evidence-label ai-label">ANALYSIS INPUT · 非原始证据</span><h2>待补 Provenance</h2><ul>{rows}</ul></section>'
    provenance_badge = "PROVENANCE READY" if evidence else "PROVENANCE INCOMPLETE"
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(idea['idea_name'])} · Benchmark Insight</title>
<style>
:root{{--ink:#152220;--muted:#6b7775;--green:#087a61;--pale:#eaf5f1;--line:#dfe7e4;--bg:#f5f7f6}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"Segoe UI","Microsoft YaHei",sans-serif}}a{{color:var(--green)}}.wrap{{max-width:1100px;margin:auto;padding:38px 24px 80px}}.top{{display:flex;justify-content:space-between;gap:20px;color:var(--muted);font-size:12px}}.hero{{background:linear-gradient(125deg,#102d27,#087a61);color:#fff;border-radius:22px;padding:38px;margin:22px 0;box-shadow:0 20px 50px rgba(7,64,51,.14)}}.eyebrow{{font-size:10px;letter-spacing:.17em;font-weight:800;color:#78d1b7}}h1{{font-size:38px;line-height:1.15;margin:12px 0}}.hero p{{color:#c3ddd5;line-height:1.7;max-width:780px}}.meta{{display:flex;gap:8px;flex-wrap:wrap}}.tag,.chip{{display:inline-block;padding:6px 9px;border-radius:7px;background:rgba(255,255,255,.12);font-size:11px}}.chip{{background:#edf3f1;margin:0 5px 5px 0}}.score{{font-size:34px;font-weight:900;color:#8ce1c6}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.section{{background:#fff;border:1px solid var(--line);border-radius:15px;padding:23px;margin-top:16px}}.section h2{{font-size:19px;margin:0 0 15px}}.section p,.section li{{line-height:1.7;color:#425451}}.citation{{font-size:11px;font-weight:800;text-decoration:none;background:#e8f1ee;padding:2px 5px;border-radius:4px}}.radars{{display:grid;grid-template-columns:1fr 1fr;gap:11px}}.radar-card{{border:1px solid var(--line);border-top:4px solid var(--radar);border-radius:11px;padding:15px}}.radar-card header{{display:flex;align-items:center;gap:8px}}.radar-card header span{{width:8px;height:8px;background:var(--radar);border-radius:50%}}.radar-card header b{{margin-left:auto}}.radar-card ul{{padding-left:18px}}.empty{{color:#899492!important;font-style:italic}}.proposal{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.proposal div{{background:#f4f7f6;padding:14px;border-radius:9px}}.proposal small,.metric-grid small{{display:block;color:var(--muted);margin-bottom:5px}}.score-row{{display:grid;grid-template-columns:175px 1fr 55px;gap:12px;align-items:center;margin:11px 0;font-size:12px}}.score-track{{height:8px;background:#ecf0ef;border-radius:10px;overflow:hidden}}.score-track i{{display:block;height:100%;background:linear-gradient(90deg,#087a61,#4fc49e)}}.metric-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-bottom:15px}}.metric-grid div{{background:#f0f6f4;padding:13px;border-radius:9px}}.metric-grid b{{font-size:18px}}.source{{display:grid;grid-template-columns:48px 1fr;gap:10px;border-top:1px solid var(--line);padding:20px 0;scroll-margin-top:15px}}.source:first-of-type{{border-top:0}}.source-id{{font-weight:900;color:var(--green)}}.source-meta{{font-size:11px;color:var(--muted)}}.source h3{{font-size:15px;margin:6px 0}}.source p{{font-size:13px}}details{{margin:8px 0}}summary{{cursor:pointer;color:var(--muted);font-size:11px}}pre{{overflow:auto;background:#102521;color:#d6ebe4;padding:12px;border-radius:8px;font-size:11px}}.internal{{font-size:11px;color:#9a6c28}}footer{{margin-top:25px;color:var(--muted);font-size:11px;text-align:center}}@media(max-width:760px){{.grid,.radars,.proposal{{grid-template-columns:1fr}}h1{{font-size:29px}}.hero{{padding:26px}}.score-row{{grid-template-columns:130px 1fr 45px}}}}
</style></head><body><div class="wrap">
<div class="top"><span>Benchmark Idea Radar · Insight Drill-down</span><span>更新于 {esc(idea['updated_at'])}</span></div>
<header class="hero"><div class="eyebrow">{esc(idea['domain']).upper()} · {idea['radar_hits']}/4 RADAR CROSS-HIT</div><h1>{esc(idea['idea_name'])}</h1><p>{esc(idea['real_world_task'])}</p><div class="meta"><span class="tag">状态 {esc(idea['status'])}</span><span class="tag">{provenance_badge}</span><span class="tag">Raw Sources {len(evidence)}</span><span class="tag">版本 V{idea['version']}</span>{''.join(f'<span class="tag">{esc(x)}</span>' for x in idea.get('capability', []))}<span class="score">{idea['total_score']:.0f}/100</span></div></header>
<section class="section"><h2>Evidence Confidence</h2><div class="grid"><div class="field"><small>Idea Score</small><strong>{idea['total_score']:.0f}/100</strong><br><span class="muted">如果Idea成立，它有多值得做</span></div><div class="field"><small>Evidence Confidence</small><strong>{esc(quality.get('evidence_confidence', 'Low'))}</strong><br><span class="muted">当前证据对关键Claim的支持程度</span></div></div><p>{esc(radar_summary)}</p><p>Verified Primary：{quality.get('quality_counts', {}).get('primary', 0)} · Verified Internal：{quality.get('quality_counts', {}).get('internal', 0)} · Partial：{quality.get('claim_counts', {}).get('partial', 0)} · Hypothesis：{quality.get('claim_counts', {}).get('hypothesis', 0)} · Conflicts：{quality.get('conflicts', 0)}</p></section>
<div class="grid"><section class="section"><h2>Core Insight</h2><p>{core_claim_html} {cite(core_ids, evidence_links)}</p></section>
<section class="section"><h2>Why Now</h2><p>{why_claim_html} {cite(why_ids, evidence_links)}</p></section></div>
<section class="section"><h2>Claim → Evidence Mapping</h2>{''.join(claim_blocks)}</section>
<section class="section"><h2>四条 Radar Evidence</h2><p class="empty">仅展示可继续追溯到真实原始材料的证据。点击 Radar 分组或具体证据，查看 Evidence Extraction、逐Case失败与 Raw Source。</p><div class="radars">{evidence_cards(idea, groups)}</div></section>
{analysis_notice}
<div class="grid"><section class="section"><h2>Existing Benchmark</h2><p>{benchmark_html}</p><p>用于研究 taxonomy、task design 与已知 failure，而不是照搬题目。 {cite(benchmark_ids, evidence_links)}</p></section>
<section class="section"><h2>Evaluation Gap</h2><p>{gap_claim_html} {cite(benchmark_ids, evidence_links)}</p><a href="{coverage_filename(idea['id'])}">查看 Benchmark Coverage Matrix →</a></section></div>
<section class="section"><h2>Model Failure</h2><p>{failure_claim_html} {cite(failure_ids, evidence_links)}</p>{'<ul>' + failure_html + '</ul>' if claims_by_type.get('model_failure', {}).get('status') == 'verified' else '<p class="empty">当前无足够Case级Eval Run，不展示未经验证的具体失败数字。</p>'}</section>
<section class="section"><h2>Benchmark Proposal</h2><div class="proposal"><div><small>Input</small>{esc(idea['input_desc'])}</div><div><small>Expected Output</small>{esc(idea['expected_output'])}</div><div><small>Evaluation Method</small>{esc(idea['evaluation_method'])}</div><div><small>Data Source</small>{esc(idea['data_source'])}</div></div><p>{cite(core_ids, evidence_links)}</p></section>
<section class="section"><h2>Mini Eval Design</h2>{mini_result}<p><strong>建议：</strong>{esc(idea['mvp_plan'])} {cite(workflow_ids + failure_ids, evidence_links)}</p></section>
{verification_html}
<section class="section"><h2>Score Breakdown</h2>{''.join(score_rows)}<p class="empty">自动评分用于排序，Radar Hits 作为额外信号；人工覆盖与 Mini Eval 回流均保留版本记录。</p></section>
<section class="section"><h2>Evidence Retrieval Log</h2><p>查看系统搜索了什么、返回哪些候选、选中了什么、拒绝了什么以及拒绝原因。</p><a href="{retrieval_filename(idea['id'])}">查看完整 Retrieval Log →</a></section>
<section class="section"><h2>Raw Source Links & Provenance</h2><p>正文中的 [S#] 会进入独立 Evidence Item，再继续下钻 Raw Source。仅列出具备真实URL或可定位原始记录的证据；人工/LLM总结不计为Raw Evidence。</p>{source_rows(idea, evidence)}</section>
<footer>页面地址：{esc(page_url)} · Generated by Benchmark Idea Radar · {datetime.now().isoformat(timespec='seconds')}</footer>
</div></body></html>'''


def page_shell(title: str, breadcrumb: str, body: str, script: str = "") -> str:
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>
:root{{--ink:#152220;--muted:#687673;--green:#087a61;--line:#dce5e2;--bg:#f4f7f6;--red:#b5483f}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"Segoe UI","Microsoft YaHei",sans-serif}}main{{max-width:1050px;margin:auto;padding:34px 22px 70px}}a{{color:var(--green)}}.crumb{{font-size:12px;color:var(--muted);margin-bottom:18px}}.hero{{background:#10352d;color:#fff;border-radius:17px;padding:29px;margin-bottom:15px}}.hero small{{color:#83d8be;text-transform:uppercase;letter-spacing:.12em}}.hero h1{{margin:9px 0 5px;font-size:30px}}.hero p{{color:#bdd8d0;line-height:1.6}}.panel{{background:#fff;border:1px solid var(--line);border-radius:13px;padding:21px;margin-top:13px}}.panel h2{{font-size:18px;margin-top:0}}.panel h3{{font-size:14px;margin:12px 0 6px}}p,li{{line-height:1.7}}.muted{{color:var(--muted)}}.meta{{display:flex;gap:7px;flex-wrap:wrap}}.tag{{padding:5px 8px;background:#e7f2ee;color:#176550;border-radius:6px;font-size:11px}}.evidence{{border-top:1px solid var(--line);padding:16px 0}}.evidence:first-of-type{{border-top:0}}.evidence strong{{display:block;margin-bottom:6px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.field{{background:#f4f7f6;border-radius:9px;padding:13px}}.field small{{display:block;color:var(--muted);margin-bottom:5px}}pre{{white-space:pre-wrap;word-break:break-word;background:#102521;color:#d9eee7;padding:14px;border-radius:9px;overflow:auto}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border-top:1px solid var(--line);text-align:left;font-size:12px}}th{{color:var(--muted)}}.severity-critical,.severity-high{{color:#a32d25;font-weight:800}}.severity-medium{{color:#9b690e;font-weight:800}}.controls{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px}}select{{padding:9px;border:1px solid var(--line);border-radius:7px;background:#fff}}.count{{font-weight:900;color:var(--green)}}.raw-panel{{border-left:5px solid #3157a4}}.extract-panel{{border-left:5px solid #087a61}}.ai-panel{{border-left:5px solid #8655a8}}.evidence-label{{display:inline-block;font-size:10px;font-weight:900;letter-spacing:.12em;padding:5px 8px;border-radius:5px;margin-bottom:10px}}.raw-label{{background:#e5ecfa;color:#3157a4}}.extract-label{{background:#e2f2ed;color:#087a61}}.ai-label{{background:#f0e8f6;color:#754797}}.case-card{{border:1px solid var(--line);border-radius:9px;padding:13px;margin-top:9px}}@media(max-width:720px){{.grid,.controls{{grid-template-columns:1fr}}}}
</style></head><body><main><div class="crumb">{breadcrumb}</div>{body}</main>{script}</body></html>'''


def render_raw_source(idea: dict, item: dict, published_ids: set[int] | None = None) -> str:
    original = item.get("url") or ""
    external = f'<a href="{esc(original)}" target="_blank" rel="noopener">打开真实原始材料 ↗</a>' if is_public_link(original) else '<span class="muted">内部原始记录，通过 Record / Run / Case ID 定位</span>'
    provenance = dict(item.get("provenance") or {})
    provenance["locator"] = item.get("locator") or {}
    trace = source_claim_trace(item["source_item_id"])
    # 同一来源可能还被 superseded Idea 引用，那些 Idea 没有页面，只显示名字
    def idea_cell(x):
        if published_ids is None or x["idea_id"] in published_ids:
            return f'<a href="{insight_filename({"id": x["idea_id"], "idea_name": x["idea_name"]})}">{esc(x["idea_name"])}</a>'
        return f'<span class="muted">{esc(x["idea_name"])}（未发布）</span>'
    trace_rows = "".join(
        f'<tr><td>{idea_cell(x)}</td>'
        f'<td>{esc(x["claim_type"])}</td><td>{esc(x["claim_text"])}</td><td>{esc(x["field_name"])}</td>'
        f'<td>{esc(x["support_relation"])}</td><td>{esc(x["evidence_status"])}</td></tr>'
        for x in trace
    )
    body = f'''<header class="hero"><small>RAW SOURCE · SourceItem #{item['source_item_id']}</small><h1>{esc(item['title'])}</h1><p>未经系统二次总结的原始来源入口与采集快照。</p></header>
<section class="panel raw-panel"><span class="evidence-label raw-label">RAW SOURCE</span><h2>原始材料</h2><div class="grid"><div class="field"><small>Source Type</small>{esc(item.get('source_type'))}</div><div class="field"><small>Evidence Role</small>{esc(item.get('evidence_role'))}</div><div class="field"><small>Title</small>{esc(item['title'])}</div><div class="field"><small>Published At</small>{esc(item.get('published_at'))}</div><div class="field"><small>Section / Page / Case / Run</small>{esc(json.dumps(item.get('locator') or {}, ensure_ascii=False))}</div><div class="field"><small>Original URL</small>{esc(original)}</div></div><p>{esc(item['content'])}</p>{external}</section>
<section class="panel"><h2>Raw Payload</h2><pre>{esc(json.dumps(item.get('raw_data') or {{}}, ensure_ascii=False, indent=2))}</pre></section>
<section class="panel"><h2>完整 Provenance</h2><pre>{esc(json.dumps(provenance, ensure_ascii=False, indent=2))}</pre></section>
<section class="panel"><h2>Reverse Trace · Raw Source → Claim → Idea</h2><div style="overflow:auto"><table><thead><tr><th>Idea</th><th>Claim Type</th><th>Claim</th><th>Extraction</th><th>Relation</th><th>Status</th></tr></thead><tbody>{trace_rows}</tbody></table></div></section>'''
    return page_shell(f"Raw Source · {item['title']}", f'<a href="{insight_filename(idea)}">{esc(idea["idea_name"])}</a> / <a href="{evidence_filename(idea["id"], item["source_item_id"])}">Evidence Extraction</a> / Raw Source', body)


def attachment_html(case: dict) -> str:
    items = []
    for attachment in case.get("attachments", []):
        if isinstance(attachment, str):
            label, url = attachment, attachment
        else:
            label = attachment.get("name") or attachment.get("title") or attachment.get("url") or attachment.get("path") or "附件"
            url = attachment.get("published_url") or attachment.get("url") or ""
        if is_public_link(url) or str(url).startswith("attachments/"):
            items.append(f'<li><a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a></li>')
        else:
            items.append(f'<li>{esc(label)} <span class="muted">（未发布路径：{esc(url)}）</span></li>')
    return f'<ul>{"".join(items)}</ul>' if items else '<p class="muted">无附件</p>'


def render_failure_case(case: dict, idea: dict, evidence: dict | None) -> str:
    fields = [
        ("Eval Run ID", case.get("run_id")), ("Failure Case ID", case.get("external_case_id")),
        ("Task / Prompt", case.get("task_prompt")), ("Input", case.get("input_data")),
        ("Reference Answer", case.get("reference_answer")), ("Rubric", case.get("rubric")),
        ("Model", f'{case.get("model_name", "")} {case.get("model_version", "")}'),
        ("Model Response", case.get("model_response")), ("Score / Pass-Fail", f'{case.get("score", "N/A")} / {"PASS" if case.get("passed") else "FAIL" if case.get("passed") is False else "N/A"}'),
        ("Failure Type", case.get("failure_type")), ("Severity", case.get("severity")),
        ("Error Analysis", case.get("error_analysis")), ("Judge Result", case.get("judge_result")),
        ("Benchmark", case.get("benchmark_name")), ("Run Date", case.get("run_date")),
    ]
    blocks = ''.join(f'<div class="field"><small>{esc(k)}</small>{esc(v)}</div>' for k, v in fields)
    raw_link = f'<a href="{raw_filename(evidence["source_item_id"])}">查看关联 Raw Source →</a>' if evidence else '<span class="muted">未关联 SourceItem</span>'
    run_link = f'<a href="eval-run-{esc(case.get("run_id"))}.html">查看完整 Eval Run 与全部 Cases →</a>' if case.get("run_id") else '<span class="muted">未关联可验证 Eval Run</span>'
    body = f'''<header class="hero"><small>Model Failure Case #{case['id']}</small><h1>{esc(case.get('failure_type'))}</h1><p>{esc(idea['idea_name'])} · {esc(case.get('model_name'))} · {esc(case.get('severity'))}</p></header>
<section class="panel"><h2>Case Detail</h2><div class="grid">{blocks}</div><p>{run_link}</p></section>
<section class="panel"><h2>原始附件 / 数据</h2>{attachment_html(case)}<details><summary>Raw Case JSON</summary><pre>{esc(json.dumps(case.get('raw_data') or case, ensure_ascii=False, indent=2))}</pre></details>{raw_link}</section>'''
    parent = evidence_filename(idea["id"], evidence["source_item_id"]) if evidence else insight_filename(idea)
    return page_shell(f"Failure Case · {case.get('failure_type')}", f'<a href="{insight_filename(idea)}">{esc(idea["idea_name"])}</a> / <a href="{parent}">Evidence</a> / Failure Case #{case["id"]}', body)


def render_evidence_item(idea: dict, item: dict) -> str:
    signal = item["failure_pattern"] or item["evaluation_gap"] or item["real_world_task"] or item["content"]
    cases = item.get("failure_cases", [])
    case_cards = ''.join(
        f'<article class="case-card"><strong>{esc(case["model_name"])} {esc(case.get("model_version"))}</strong>'
        f'<p>Prompt：{esc(case.get("task_prompt"))}</p><p>Reference：{esc(case.get("reference_answer"))}</p>'
        f'<p>Response：{esc(case.get("model_response"))}</p><p>Error：{esc(case.get("failure_type"))} · '
        f'Judge：{esc(case.get("judge_result"))}</p><a href="{failure_case_filename(case["id"])}">查看完整 Case 与附件 →</a></article>'
        for case in cases
    ) or '<p class="muted">当前为聚合 Failure Signal，尚未回流逐Case的 Prompt / Reference / Response / Judge 数据。</p>'
    provenance = {
        "source_item_id": item["source_item_id"], "signal_id": item["signal_id"], "source_id": item["source_id"],
        "extractor_version": item["extractor_version"], "confidence": item["confidence"],
        "published_at": item.get("published_at"), "collected_at": item.get("collected_at"),
    }
    external = f'<a href="{esc(item["url"])}" target="_blank" rel="noopener">外部 Raw Source ↗</a>' if is_public_link(item.get("url")) else '<span class="muted">内部来源</span>'
    raw_titles = {
        "benchmark": "Original Benchmark / Paper / GitHub / Leaderboard",
        "workflow": "Original Workflow / SOP / Interview",
        "product_agent": "Official Release / Blog / Demo",
        "model_failure": "Original Prompt / Reference / Model Response / Judge Record",
    }
    analysis = item.get("ai_analysis") or {
        "theme": item["theme"], "capabilities": item["capability"],
        "real_world_task": item["real_world_task"], "evaluation_gap": item["evaluation_gap"],
        "failure_pattern": item["failure_pattern"],
    }
    analysis_fields = ''.join(
        f'<div class="field"><small>{esc(key.replace("_", " ").title())}</small>'
        f'{esc(" / ".join(value) if isinstance(value, list) else value)}</div>'
        for key, value in analysis.items() if key != "analysis_type"
    )
    body = f'''<header class="hero"><small>{RADAR_LABELS[item['radar']]} · Evidence Item</small><h1>{esc(item['title'])}</h1><p>{esc(signal)}</p></header>
<section class="panel raw-panel"><span class="evidence-label raw-label">RAW SOURCE · 未经二次总结</span><h2>{raw_titles[item['radar']]}</h2><p>{esc(item['content'])}</p><div class="grid"><div class="field"><small>Source Type</small>{esc(item.get('source_type'))}</div><div class="field"><small>Locator（Section / Page / Case ID）</small>{esc(json.dumps(item.get('locator') or {}, ensure_ascii=False))}</div></div><p><a href="{raw_filename(item['source_item_id'])}">查看完整 Raw Source 与原始 Payload →</a> · {external}</p></section>
<section class="panel extract-panel"><span class="evidence-label extract-label">EVIDENCE EXTRACTION · 从原文提取</span><h2>可核对的证据字段</h2><div class="grid"><div class="field"><small>Theme</small>{esc(item['theme'])}</div><div class="field"><small>Capabilities</small>{esc(' / '.join(item['capability']))}</div><div class="field"><small>Real-world Task</small>{esc(item['real_world_task'])}</div><div class="field"><small>Extracted Failure</small>{esc(item['failure_pattern'])}</div></div><p class="muted">该层只做定位和字段抽取，不包含Gap判断或价值判断。</p></section>
<section class="panel ai-panel"><span class="evidence-label ai-label">AI ANALYSIS · 系统推断</span><h2>分析与判断</h2><div class="grid">{analysis_fields}<div class="field"><small>Extraction Confidence</small>{item['confidence']:.0%}</div></div><p class="muted">以上内容由 {esc(item['extractor_version'])} 基于 Evidence Extraction 生成，必须回看 Raw Source 复核。</p></section>
<section class="panel"><h2>Model Failure Cases</h2>{case_cards}</section>
<section class="panel"><h2>Provenance</h2><pre>{esc(json.dumps(provenance, ensure_ascii=False, indent=2))}</pre><p><a href="{raw_filename(item['source_item_id'])}">查看 Raw Source →</a> · {external}</p></section>'''
    return page_shell(f"Evidence · {item['title']}", f'<a href="{insight_filename(idea)}">{esc(idea["idea_name"])}</a> / <a href="{group_filename(idea["id"], item["radar"])}">{RADAR_LABELS[item["radar"]]}</a> / Evidence', body)


def render_evidence_group(idea: dict, radar: str, records: list[dict]) -> str:
    items = []
    for record in records:
        analysis = record.get("ai_analysis") or {}
        analysis_text = "；".join(
            f'{key.replace("_", " ")}：{" / ".join(value) if isinstance(value, list) else value}'
            for key, value in analysis.items() if key != "analysis_type" and value
        )
        items.append(f'''<article class="evidence"><strong><a href="{evidence_filename(idea['id'], record['source_item_id'])}">{esc(record['title'])}</a></strong><p><span class="evidence-label raw-label">RAW EVIDENCE</span> {esc(record['content'][:320])}</p><p><span class="evidence-label ai-label">AI ANALYSIS</span> {esc(analysis_text[:320])}</p><div class="meta"><span class="tag">Source #{record['source_item_id']}</span><span class="tag">Signal #{record['signal_id']}</span><span class="tag">{record['confidence']:.0%}</span></div></article>''')
    body = f'''<header class="hero"><small>Evidence Group</small><h1>{RADAR_LABELS[radar]}</h1><p>{esc(idea['idea_name'])} · 共 {len(records)} 条证据</p></header><section class="panel"><h2>Evidence Items</h2>{''.join(items) or '<p class="muted">该Radar尚无证据。</p>'}</section>'''
    return page_shell(f"{RADAR_LABELS[radar]} · {idea['idea_name']}", f'<a href="{insight_filename(idea)}">{esc(idea["idea_name"])}</a> / {RADAR_LABELS[radar]}', body)


def render_eval_run(run_id: str, cases: list[dict]) -> str:
    first = cases[0] if cases else {}
    models = sorted({x.get("model_name") for x in cases if x.get("model_name")})
    stats = []
    for model in models:
        subset = [x for x in cases if x.get("model_name") == model]
        passed = sum(1 for x in subset if x.get("passed") is True)
        accuracy = passed / len(subset) * 100 if subset else 0
        stats.append((model, passed, len(subset), accuracy))
    max_gap = (max((x[3] for x in stats), default=0) - min((x[3] for x in stats), default=0)) if stats else 0
    stat_rows = ''.join(f'<tr><td>{esc(model)}</td><td>{passed}</td><td>{total}</td><td>{accuracy:.1f}%</td></tr>' for model, passed, total, accuracy in stats)
    case_rows = ''.join(f'<tr><td><a href="{failure_case_filename(x["id"])}">{esc(x.get("external_case_id"))}</a></td><td>{esc(x.get("model_name"))}</td><td>{esc(x.get("score"))}</td><td>{"PASS" if x.get("passed") else "FAIL"}</td><td>{esc(x.get("failure_type"))}</td></tr>' for x in cases)
    run_meta = {k: first.get(k) for k in ["run_id","dataset_version","dataset_hash","prompt_version","rubric_version","judge_type","judge_name","judge_version","artifact_url","protocol"]}
    body = f'''<header class="hero"><small>EVAL RUN</small><h1>{esc(run_id)}</h1><p>可追溯到全部Cases、Prompt、Reference、Model Response与Judge Result。</p></header>
<section class="panel"><h2>Run Provenance</h2><pre>{esc(json.dumps(run_meta, ensure_ascii=False, indent=2))}</pre></section>
<section class="panel"><h2>Model Statistics</h2><table><thead><tr><th>Model</th><th>Correct</th><th>Total</th><th>Accuracy</th></tr></thead><tbody>{stat_rows}</tbody></table><p><strong>Max Gap = {max_gap:.1f}pp</strong></p></section>
<section class="panel"><h2>Cases</h2><table><thead><tr><th>Case ID</th><th>Model</th><th>Score</th><th>Pass/Fail</th><th>Failure Type</th></tr></thead><tbody>{case_rows}</tbody></table></section>'''
    return page_shell(f"Eval Run · {run_id}", '<a href="failure-evidence.html">Failure Explorer</a> / Eval Run', body)


def render_failure_index(cases: list[dict]) -> str:
    def options(field):
        values = sorted({str(x.get(field) or "未标注") for x in cases})
        return ''.join(f'<option value="{esc(x)}">{esc(x)}</option>' for x in values)
    rows = []
    for case in cases:
        rows.append(f'''<tr class="case-row" data-model="{esc(case.get('model_name') or '未标注')}" data-type="{esc(case.get('failure_type') or '未标注')}" data-severity="{esc(case.get('severity') or '未标注')}" data-benchmark="{esc(case.get('benchmark_name') or '未标注')}"><td><a href="{failure_case_filename(case['id'])}">#{case['id']} {esc(case['idea_name'])}</a></td><td>{esc(case.get('model_name'))}<br><span class="muted">{esc(case.get('model_version'))}</span></td><td>{esc(case.get('failure_type'))}</td><td class="severity-{esc(case.get('severity'))}">{esc(case.get('severity'))}</td><td>{esc(case.get('benchmark_name'))}</td><td>{esc(case.get('score'))} / {'PASS' if case.get('passed') else 'FAIL' if case.get('passed') is False else 'N/A'}</td><td>{esc(case.get('run_date'))}</td></tr>''')
    body = f'''<header class="hero"><small>MODEL FAILURE EVIDENCE</small><h1>Failure Case Explorer</h1><p>按 Model、Failure Type、Severity、Benchmark 聚合和筛选；每条记录可继续下钻到原始附件与数据。</p></header><section class="panel"><div class="controls"><select id="model"><option value="">全部 Model</option>{options('model_name')}</select><select id="type"><option value="">全部 Failure Type</option>{options('failure_type')}</select><select id="severity"><option value="">全部 Severity</option>{options('severity')}</select><select id="benchmark"><option value="">全部 Benchmark</option>{options('benchmark_name')}</select></div><p>显示 <span class="count" id="count">{len(cases)}</span> / {len(cases)} Cases</p><div style="overflow:auto"><table><thead><tr><th>Case / Idea</th><th>Model</th><th>Failure Type</th><th>Severity</th><th>Benchmark</th><th>Score</th><th>Run Date</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>'''
    script = '''<script>const filters=['model','type','severity','benchmark'];function apply(){let n=0;document.querySelectorAll('.case-row').forEach(r=>{const ok=filters.every(k=>!document.getElementById(k).value||r.dataset[k]===document.getElementById(k).value);r.style.display=ok?'':'none';if(ok)n++});document.getElementById('count').textContent=n}filters.forEach(k=>document.getElementById(k).addEventListener('change',apply));</script>'''
    return page_shell("Failure Case Explorer", '<a href="index.html">Insight Index</a> / Model Failure Evidence', body, script)


def render_coverage_matrix(idea: dict) -> str:
    rows = []
    for item in idea.get("coverage_matrix", []):
        source = f'<a href="{esc(item.get("source_url"))}" target="_blank" rel="noopener">Raw Source ↗</a>' if is_public_link(item.get("source_url")) else '<span class="muted">Source pending</span>'
        rows.append(
            f'<tr><td><strong>{esc(item["benchmark_name"])}</strong><br>{source}</td>'
            f'<td>{esc(item["task_definition"])}</td><td>{esc(item["dataset_description"])}</td>'
            f'<td>{esc(item["input_format"])}</td><td>{esc(item["output_format"])}</td>'
            f'<td>{esc(item["evaluation_protocol"])}</td><td>{esc(" / ".join(item["metrics"]))}</td>'
            f'<td>{esc(" / ".join(item["capabilities"]))}</td><td><span class="tag">{esc(item["target_coverage"])}</span></td>'
            f'<td>{esc(item["verification_status"])}</td></tr>'
        )
    summary = (idea.get("evidence_quality") or {}).get("coverage_matrix_summary") or {}
    body = f'''<header class="hero"><small>BENCHMARK COVERAGE MATRIX</small><h1>{esc(idea['idea_name'])}</h1><p>逐项核验已有Benchmark测了什么、没测什么，以及目标Idea的新覆盖。</p></header>
<section class="panel"><h2>Coverage Summary</h2><pre>{esc(json.dumps(summary, ensure_ascii=False, indent=2))}</pre></section>
<section class="panel"><div style="overflow:auto"><table><thead><tr><th>Benchmark</th><th>Task</th><th>Dataset</th><th>Input</th><th>Output</th><th>Evaluation Protocol</th><th>Metric</th><th>Capabilities</th><th>Target Coverage</th><th>Verification</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>'''
    return page_shell(f"Coverage Matrix · {idea['idea_name']}", f'<a href="{insight_filename(idea)}">{esc(idea["idea_name"])}</a> / Coverage Matrix', body)


def render_retrieval_log(idea: dict, runs: list[dict]) -> str:
    run_blocks = []
    for run in runs:
        rows = []
        for result in run.get("results", []):
            decision = "Selected" if result.get("selected") else "Rejected"
            reason = result.get("rejection_reason") or "Selected as relevant candidate"
            source_link = f'<a href="{esc(result["url"])}" target="_blank" rel="noopener">{esc(result["title"])}</a>' if is_public_link(result.get("url")) else esc(result.get("title"))
            rows.append(f'<tr><td>{result.get("rank")}</td><td>{source_link}</td><td>{esc(result.get("source_quality"))}</td><td>{decision}</td><td>{esc(reason)}</td></tr>')
        error_markup = f'<pre>{esc(json.dumps(run.get("error"), ensure_ascii=False, indent=2))}</pre>' if run.get("error") else ""
        run_blocks.append(
            f'<section class="panel"><h2>Query：{esc(run["retrieval_query"])}</h2>'
            f'<p class="muted">Radar {esc(run["radar"])} · {esc(run["retrieved_at"])} · {esc(run["retriever_version"])} · {esc(run["status"])}</p>'
            f'{error_markup}'
            f'<div style="overflow:auto"><table><thead><tr><th>Rank</th><th>Retrieved Source</th><th>Quality</th><th>Decision</th><th>Reason</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>'
        )
    runs_markup = "".join(run_blocks) or '<section class="panel"><p class="muted">尚未执行主动Evidence Retrieval。</p></section>'
    body = f'<header class="hero"><small>EVIDENCE RETRIEVAL QA</small><h1>{esc(idea["idea_name"])}</h1><p>保留 Retrieval Query、全部候选、选中来源、拒绝来源和拒绝原因。</p></header>{runs_markup}'
    return page_shell(f"Retrieval Log · {idea['idea_name']}", f'<a href="{insight_filename(idea)}">{esc(idea["idea_name"])}</a> / Retrieval Log', body)


def render_index(ideas: list[dict], base_url: str) -> str:
    cards = []
    for idea in ideas:
        cards.append(
            f'<a class="card" href="{esc(insight_filename(idea))}"><span>{esc(idea["domain"]).upper()} · {idea["radar_hits"]}/4 RADARS</span>'
            f'<h2>{esc(idea["idea_name"])}</h2><p>{esc(idea["evaluation_gap"][:170])}</p>'
            f'<b>{idea["total_score"]:.0f}/100 · {esc(idea["status"])}</b></a>'
        )
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Benchmark Idea Radar Insights</title><style>body{{margin:0;background:#f4f7f6;color:#172522;font-family:Inter,"Segoe UI","Microsoft YaHei",sans-serif}}main{{max-width:1100px;margin:auto;padding:45px 24px}}header{{background:#10352d;color:white;padding:34px;border-radius:18px;margin-bottom:18px}}header p{{color:#b9d8cf}}header a{{color:#8de0c6}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:13px}}.card{{display:block;background:white;border:1px solid #dfe7e4;border-radius:13px;padding:20px;text-decoration:none;color:inherit}}.card:hover{{border-color:#69af9b;transform:translateY(-2px)}}.card span{{font-size:10px;letter-spacing:.1em;color:#087a61;font-weight:800}}.card h2{{font-size:18px}}.card p{{color:#61716e;line-height:1.5}}.card b{{color:#087a61}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><main><header><h1>Benchmark Idea Radar · Insights</h1><p>从 Weekly 摘要下钻到 Idea Card、Evidence Group、Evidence Item、Failure Case 和 Raw Source。</p><a href="failure-evidence.html">打开 Model Failure Case Explorer →</a></header><div class="grid">{''.join(cards)}</div></main></body></html>'''


def publish_attachments(case: dict) -> None:
    target_dir = OUTPUT_DIR / "attachments"
    target_dir.mkdir(parents=True, exist_ok=True)
    prepared = []
    for index, attachment in enumerate(case.get("attachments", []), 1):
        item = {"name": attachment, "path": attachment} if isinstance(attachment, str) else dict(attachment)
        path_value = item.get("path") or ""
        source = Path(path_value)
        if path_value and not source.is_absolute():
            source = BASE_DIR / source
        if path_value and source.exists() and source.is_file():
            safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", source.name)
            target = target_dir / f"case-{case['id']}-{index}-{safe_name}"
            shutil.copy2(source, target)
            item["published_url"] = f"attachments/{target.name}"
        prepared.append(item)
    case["attachments"] = prepared


# 不发布的 Idea 状态。superseded 是分类规则变更后的归档，已无信号支撑；
# 与 weekly_report 的排除口径保持一致（见 radar_core.weekly_report）。
UNPUBLISHED_STATUSES = {"superseded"}

# 每次生成都由本模块完整重写的产物。清理时只动这些模式，attachments/ 等
# 目录和其他手工放入的文件不受影响。
GENERATED_PATTERNS = ["idea-*.html", "raw-source-*.html", "failure-case-*.html", "eval-run-*.html"]


def prune_stale_outputs(written: set[str]) -> list[str]:
    """删除本次未生成的旧产物。

    generate() 过去只写不删：Idea 被 superseded、证据被移除后，对应页面仍留在
    站点上，旧内容（例如 evaluation_gap 的 arXiv 原文转储）也一直可访问。
    """
    removed = []
    for pattern in GENERATED_PATTERNS:
        for path in OUTPUT_DIR.glob(pattern):
            if path.is_file() and path.name not in written:
                path.unlink()
                removed.append(path.name)
    return sorted(removed)


def generate(base_url: str | None = None) -> dict:
    init_db()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = (base_url or public_base()).rstrip("/")
    ideas = [x for x in list_ideas() if x["status"] not in UNPUBLISHED_STATUSES]
    # 先定发布集合再渲染：raw source 页会交叉链接到其他 Idea，需要事先知道谁有页面
    published_ideas = [
        idea for idea in (get_idea(x["id"]) for x in ideas)
        if idea and idea.get("provenance_ready")
    ]
    published_ids = {x["id"] for x in published_ideas}
    manifest = []
    raw_written: set[int] = set()
    evidence_pages = group_pages = case_pages = 0
    for idea in published_ideas:
        filename = insight_filename(idea)
        (OUTPUT_DIR / filename).write_text(render_detail(idea, base), encoding="utf-8")
        (OUTPUT_DIR / retrieval_filename(idea["id"])).write_text(
            render_retrieval_log(idea, retrieval_log(idea["id"])), encoding="utf-8"
        )
        (OUTPUT_DIR / coverage_filename(idea["id"])).write_text(
            render_coverage_matrix(idea), encoding="utf-8"
        )
        evidence, groups = evidence_map(idea)
        for radar in ["benchmark", "workflow", "product_agent", "model_failure"]:
            (OUTPUT_DIR / group_filename(idea["id"], radar)).write_text(
                render_evidence_group(idea, radar, groups.get(radar, [])), encoding="utf-8"
            )
            group_pages += 1
        evidence_by_source = {x["source_item_id"]: x for x in evidence}
        for item in evidence:
            (OUTPUT_DIR / evidence_filename(idea["id"], item["source_item_id"])).write_text(
                render_evidence_item(idea, item), encoding="utf-8"
            )
            evidence_pages += 1
            if item["source_item_id"] not in raw_written:
                (OUTPUT_DIR / raw_filename(item["source_item_id"])).write_text(
render_raw_source(idea, item, published_ids), encoding="utf-8"
                )
                raw_written.add(item["source_item_id"])
        for case in idea.get("failure_cases", []):
            publish_attachments(case)
            evidence_item = evidence_by_source.get(case.get("source_item_id"))
            (OUTPUT_DIR / failure_case_filename(case["id"])).write_text(
                render_failure_case(case, idea, evidence_item), encoding="utf-8"
            )
            case_pages += 1
        group_files = {radar: group_filename(idea["id"], radar) for radar in RADAR_LABELS}
        evidence_files = [evidence_filename(idea["id"], x["source_item_id"]) for x in evidence]
        raw_files = [raw_filename(x["source_item_id"]) for x in evidence]
        case_files = [failure_case_filename(x["id"]) for x in idea.get("failure_cases", [])]
        manifest.append({
            "idea_id": idea["id"], "idea_name": idea["idea_name"], "file": filename,
            "url": insight_url(idea, base), "sources": len(evidence),
            "evidence_groups": group_files,
            "evidence_items": evidence_files,
            "raw_sources": raw_files,
            "failure_cases": case_files,
            "retrieval_log": retrieval_filename(idea["id"]),
            "retrieval_log_url": f"{base}/{retrieval_filename(idea['id'])}",
            "coverage_matrix": coverage_filename(idea["id"]),
            "coverage_matrix_url": f"{base}/{coverage_filename(idea['id'])}",
            "group_urls": {radar: f"{base}/{path}" for radar, path in group_files.items()},
            "evidence_urls": [f"{base}/{path}" for path in evidence_files],
            "raw_source_urls": [f"{base}/{path}" for path in raw_files],
            "failure_case_urls": [f"{base}/{path}" for path in case_files],
        })
    cases = list_failure_cases(limit=2000)
    # 只收录已发布 Idea 的 Case：否则 Explorer 会链接到未生成的 failure-case 页面
    cases = [x for x in cases if x.get("idea_id") in published_ids]
    eval_runs = defaultdict(list)
    for case in cases:
        if case.get("run_id"):
            eval_runs[case["run_id"]].append(case)
    for run_id, run_cases in eval_runs.items():
        (OUTPUT_DIR / f"eval-run-{run_id}.html").write_text(render_eval_run(run_id, run_cases), encoding="utf-8")
    (OUTPUT_DIR / "failure-evidence.html").write_text(render_failure_index(cases), encoding="utf-8")
    (OUTPUT_DIR / "failure_cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "index.html").write_text(render_index(published_ideas, base), encoding="utf-8")
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    written = {f"eval-run-{run_id}.html" for run_id in eval_runs}
    for item in manifest:
        written.add(item["file"])
        written.add(item["retrieval_log"])
        written.add(item["coverage_matrix"])
        written.update(item["evidence_groups"].values())
        written.update(item["evidence_items"])
        written.update(item["raw_sources"])
        written.update(item["failure_cases"])
    removed = prune_stale_outputs(written)
    return {
        "output": str(OUTPUT_DIR), "base_url": base, "pages": len(manifest),
        "withheld_for_provenance": len(ideas) - len(published_ideas),
        "excluded_statuses": sorted(UNPUBLISHED_STATUSES),
        "stale_pages_removed": len(removed),
        "evidence_group_pages": group_pages, "evidence_item_pages": evidence_pages,
        "raw_source_pages": len(raw_written), "failure_case_pages": case_pages,
        "eval_run_pages": len(eval_runs),
        "manifest": manifest,
    }


def main():
    parser = argparse.ArgumentParser(description="生成 Benchmark Idea Insight 静态页面")
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()
    print(json.dumps(generate(args.base_url), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
