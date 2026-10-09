"""文献综述：按写综述的步骤分三步，每一步的结果都存下来，能在页面上看、能改。

  ① 逐篇抽卡  每篇摘要 → 测什么、输入、怎么判分、数据、主要发现、作者承认的局限（原话）
  ② 分类      根据卡片按"测什么"分类，并说明为什么这么分；你可以在页面上调整
  ③ 写综述    第一节（分类）和第五节（边界）由程序按数据生成，第二到四节由模型综合
  批注改稿    你写批注，模型照着改第二到四节

程序只做"不许编造"的核对：编号要存在，「」里的原话要在所引论文的摘要里。
没过就把问题列给模型改一次；还没过照样保存，但在页面上标出来。不打分。

产物在 reports/lit_review/<领域>/：
  cards.json     每篇的卡片（按摘要内容缓存，新论文进来只抽新的）
  taxonomy.json  分类（by=model 或 by=user）
  review.md      完整综述；review_body.md 是模型写的第二到四节
  review.json    核对结果、生成时间、批注记录
  status.json    运行状态（网页轮询用）
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from radar.core.radar_core import BASE_DIR
from radar.core.reading import DOMAIN_CN
from radar.review import check as C
from radar.review.corpus import REVIEW_DOMAINS, corpus_text, load_corpus, skipped_count
from radar.review.llm import chat, extract_json, load_config, strip_fence

PROMPTS = Path(__file__).with_name("prompts")
OUT_ROOT = BASE_DIR / "reports" / "lit_review"
BATCH = 10
WORKERS = 4
STAGES = ("cards", "taxonomy", "review")
KINDS = ("Benchmark", "评测研究", "方法", "其他")
CARD_FIELDS = ("kind", "task", "input", "scoring", "data", "finding", "limit_quote", "limit_cn")
SYSTEM = "你是严谨的文献综述作者。只依据给定资料写作，不编造，原话一字不改。"

ChatFn = Callable[[list[dict[str, str]]], str]
_RUN_LOCK = threading.Lock()
_IO_LOCK = threading.Lock()
_RUNNING: set[str] = set()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def out_dir(domain: str) -> Path:
    return OUT_ROOT / domain


def _read(p: Path, default: Any) -> Any:
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def _status(domain: str, **kw: Any) -> dict[str, Any]:
    p = out_dir(domain) / "status.json"
    with _IO_LOCK:
        st = _read(p, {})
        st.update(kw, updated_at=_now())
        _write(p, st)
    return st


def _ask(chat_fn: ChatFn, text: str) -> str:
    return chat_fn([{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}])


def paper_hash(p: dict[str, Any]) -> str:
    return hashlib.sha1((p["title"] + "\n" + p["abstract"]).encode("utf-8")).hexdigest()[:12]


# ---------- ① 逐篇抽卡 ----------

def _clean_card(item: dict[str, Any], p: dict[str, Any]) -> dict[str, Any]:
    c = {k: re.sub(r"\s+", " ", str(item.get(k) or "")).strip() for k in CARD_FIELDS}
    if c["kind"] not in KINDS:
        c["kind"] = "Benchmark" if "bench" in c["kind"].lower() else "其他"
    q = c["limit_quote"].strip(" \"'「」“”")
    c["limit_quote"] = q
    if q and not C.quote_in(q, p):
        # 原话对不上摘要：删掉，留个记录，页面上能看到
        c["quote_dropped"] = q[:300]
        c["limit_quote"] = ""
        c["limit_cn"] = ""
    c["id"] = p["id"]
    c["hash"] = paper_hash(p)
    return c


def _card_batch(batch: list[dict[str, Any]], chat_fn: ChatFn) -> dict[int, dict[str, Any]]:
    data = extract_json(_ask(chat_fn, f"{prompt('cards')}\n\n---\n\n{corpus_text(batch)}"))
    if isinstance(data, dict):
        data = data.get("cards") or data.get("papers") or [data]
    by = {p["id"]: p for p in batch}
    out: dict[int, dict[str, Any]] = {}
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            pid = int(str(item.get("id")).lstrip("#").strip())
        except ValueError:
            continue
        if pid in by:
            out[pid] = _clean_card(item, by[pid])
    return out


def make_cards(domain: str, papers: list[dict[str, Any]], chat_fn: ChatFn, force: bool = False) -> dict[str, Any]:
    path = out_dir(domain) / "cards.json"
    store = _read(path, {"cards": {}})
    cards: dict[str, Any] = store.setdefault("cards", {})
    todo = [p for p in papers if force or cards.get(str(p["id"]), {}).get("hash") != paper_hash(p)]
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    _status(domain, stage="cards", step="逐篇抽卡", done=0, total=len(todo))
    done, errors, got_any = 0, [], False

    def work(b):
        got = _card_batch(b, chat_fn)
        miss = [p for p in b if p["id"] not in got]
        if miss:  # 漏掉的再单独要一次
            try:
                got.update(_card_batch(miss, chat_fn))
            except Exception:
                pass
        return got

    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(work, b): b for b in batches}
        for f in as_completed(futs):
            b = futs[f]
            try:
                got = f.result()
                got_any = got_any or bool(got)
            except Exception as e:  # 单批出错不中断，下次运行会补
                errors.append(str(e)[:300])
                got = {}
            with _IO_LOCK:
                cards.update({str(k): v for k, v in got.items()})
                store["updated_at"] = _now()
                _write(path, store)
            done += len(b)
            _status(domain, done=done)
    if batches and not got_any:
        raise RuntimeError("抽卡全部失败：" + (errors[0] if errors else "模型没有返回卡片"))
    store["errors"] = errors[-5:]
    _write(path, store)
    return store


# ---------- ② 分类 ----------

def _card_line(c: dict[str, Any], p: dict[str, Any]) -> str:
    return (f"#{p['id']}｜{c.get('kind', '')}｜{p['title'][:140]}\n"
            f"  测什么：{c.get('task', '')}｜输入：{c.get('input', '')}｜判分：{c.get('scoring', '')}"
            f"｜发现：{c.get('finding', '')}")


def normalize_taxonomy(data: Any, ids: set[int]) -> dict[str, Any]:
    """清理分类：去掉不存在和重复的编号、空类。返回的 missing 是一篇都没出现的编号。"""
    seen: set[int] = set()

    def take(xs):
        out = []
        for x in xs or []:
            try:
                i = int(str(x).lstrip("#"))
            except ValueError:
                continue
            if i in ids and i not in seen:
                seen.add(i)
                out.append(i)
        return out

    data = data if isinstance(data, dict) else {}
    cats = []
    for c in data.get("categories") or []:
        if not isinstance(c, dict):
            continue
        got = take(c.get("ids"))
        name = str(c.get("name") or "").strip()[:40]
        if got and name:
            cats.append({"name": name, "tests": str(c.get("tests") or "").strip(),
                         "why": str(c.get("why") or "").strip(), "ids": got})
    outside = []
    for o in data.get("outside") or []:
        if isinstance(o, dict):
            got = take([o.get("id")])
            if got:
                outside.append({"id": got[0], "reason": str(o.get("reason") or "").strip()})
    return {"categories": cats, "outside": outside, "missing": sorted(ids - seen)}


def make_taxonomy(domain: str, papers: list[dict[str, Any]], cards: dict[str, Any], chat_fn: ChatFn) -> dict[str, Any]:
    use = [p for p in papers if str(p["id"]) in cards]
    if not use:
        raise ValueError("还没有卡片，先抽卡")
    ids = {p["id"] for p in use}
    _status(domain, stage="taxonomy", step="分类", done=0, total=len(use))
    msg = (f"{prompt('taxonomy')}\n\n---\n\n领域：{DOMAIN_CN[domain]}，共 {len(use)} 篇。\n\n"
           + "\n".join(_card_line(cards[str(p["id"])], p) for p in use))
    tax = normalize_taxonomy(extract_json(_ask(chat_fn, msg)), ids)
    if tax["missing"]:
        fix = (msg + "\n\n---\n\n你上一次的结果：\n" + json.dumps({k: tax[k] for k in ("categories", "outside")},
                                                                ensure_ascii=False)
               + "\n\n这些编号一次都没出现：" + "、".join(f"#{i}" for i in tax["missing"])
               + "\n每篇必须出现一次。把它们放进合适的类或 outside，输出完整的 JSON。")
        try:
            tax2 = normalize_taxonomy(extract_json(_ask(chat_fn, fix)), ids)
            if len(tax2["missing"]) < len(tax["missing"]) and tax2["categories"]:
                tax = tax2
        except Exception:
            pass
    for i in tax.pop("missing"):
        tax["outside"].append({"id": i, "reason": "模型没归类，需要你手动放进某一类"})
    tax.update(by="model", updated_at=_now())
    _write(out_dir(domain) / "taxonomy.json", tax)
    _status(domain, done=len(use))
    return tax


def save_taxonomy(domain: str, payload: dict[str, Any]) -> dict[str, Any]:
    papers = load_corpus(domain)
    tax = normalize_taxonomy(payload, {p["id"] for p in papers})
    tax.pop("missing")
    if not tax["categories"]:
        raise ValueError("至少要有一类")
    tax.update(by="user", updated_at=_now())
    _write(out_dir(domain) / "taxonomy.json", tax)
    return tax


# ---------- ③ 写综述 ----------

def _cell(s: str) -> str:
    return s.replace("|", "／").replace("\n", " ")


def render_section1(tax: dict[str, Any], by: dict[int, dict], cards: dict[str, Any]) -> str:
    cats = tax["categories"]
    n = sum(len(c["ids"]) for c in cats)
    L = [f"## 一、大家在研究什么：{n} 篇分 {len(cats)} 类", "", "| 类别 | 篇数 | 测什么 |", "|---|---|---|"]
    L += [f"| {_cell(c['name'])} | {len(c['ids'])} | {_cell(c['tests'])} |" for c in cats]
    for c in cats:
        L += ["", f"### {c['name']}（{len(c['ids'])} 篇）", ""]
        if c["tests"] or c["why"]:
            L += [c["tests"] + (f" 归为一类的理由：{c['why']}" if c["why"] else ""), ""]
        for i in c["ids"]:
            if i in by:
                task = cards.get(str(i), {}).get("task", "")
                L.append(f"- {by[i]['title']} [#{i}]" + (f"：{task}" if task else ""))
    if tax["outside"]:
        L += ["", f"### 没算进来的（{len(tax['outside'])} 篇）", ""]
        L += [f"- {by[o['id']]['title']} [#{o['id']}]：{o['reason'] or '不是 Benchmark'}" for o in tax["outside"]
              if o["id"] in by]
    return "\n".join(L)


def render_section5(domain: str, papers: list[dict], tax: dict[str, Any], cards: dict[str, Any],
                    skipped: int, model: str) -> str:
    dates = sorted(p["date"] for p in papers if p["date"])
    placed = {i for c in tax["categories"] for i in c["ids"]} | {o["id"] for o in tax["outside"]}
    left = [p for p in papers if p["id"] not in placed]
    L = ["## 五、这份综述的边界", "",
         f"- 资料：Radar 收进来的{DOMAIN_CN[domain]}领域 arXiv 论文 {len(papers)} 篇，只读了标题和摘要，没读全文。"]
    if dates:
        L.append(f"- 时间：{dates[0]} 至 {dates[-1]}。")
    if skipped:
        L.append(f"- 你在待读清单里标为\"不用读\"的 {skipped} 篇没算进来。")
    if left:
        L.append(f"- 有 {len(left)} 篇新论文还没抽卡或没分类，这一版没写到。")
    L += ["- 库里没补进来的经典 Benchmark 不会出现在这里。第三节说的\"还没研究\"只代表这批资料里没有，不代表没人做过。",
          f"- 卡片和第二到四节由 {model or '模型'} 生成，第一节的分类"
          f"{'你调整过' if tax.get('by') == 'user' else '由模型提出'}。用之前请自己读一遍，点 #编号 能打开原文。"]
    return "\n".join(L)


def _material(tax: dict[str, Any], papers: list[dict], cards: dict[str, Any]) -> str:
    by = {p["id"]: p for p in papers}
    L = ["### 分类"]
    for k, c in enumerate(tax["categories"], 1):
        L.append(f"{k}. {c['name']}（{len(c['ids'])} 篇）：{c['tests']}")
        L.append("   编号：" + " ".join(f"#{i}" for i in c["ids"]))
    if tax["outside"]:
        L.append("不算进来的：" + "；".join(f"#{o['id']}（{o['reason']}）" for o in tax["outside"]))
    L += ["", "### 每篇论文的卡片"]
    for i in [i for c in tax["categories"] for i in c["ids"]]:
        p, c = by.get(i), cards.get(str(i), {})
        if not p:
            continue
        L.append(f"#{i}｜{c.get('kind', '')}｜{p['title']}")
        L.append(f"测什么：{c.get('task', '')}；输入：{c.get('input', '')}；判分：{c.get('scoring', '')}；"
                 f"数据：{c.get('data', '')}；发现：{c.get('finding', '')}")
        if c.get("limit_quote"):
            L.append(f"作者原话：「{c['limit_quote']}」（{c.get('limit_cn', '')}）")
        L.append("")
    return "\n".join(L)


def _only_body(md: str) -> str:
    """只留模型写的第二到四节，丢掉它多写的第一、五节和前后的解释。"""
    out, keep = [], False
    for line in md.splitlines():
        if line.startswith("## "):
            h = line[3:].strip()
            keep = not (h.startswith("一") or h.startswith("五"))
        if keep:
            out.append(line)
    return ("\n".join(out).strip() or md.strip()) + "\n"


def write_review(domain: str, papers: list[dict], cards: dict[str, Any], tax: dict[str, Any], chat_fn: ChatFn,
                 notes: str | None = None) -> dict[str, Any]:
    d = out_dir(domain)
    meta = _read(d / "review.json", {})
    prev = (d / "review_body.md").read_text(encoding="utf-8") if (d / "review_body.md").exists() else ""
    base = f"{prompt('review')}\n\n---\n\n领域：{DOMAIN_CN[domain]}\n\n{_material(tax, papers, cards)}"
    if notes and prev:
        _status(domain, stage="review", step="按批注改稿", done=0, total=1)
        msg = (base + "\n\n---\n\n上一版的第二到四节：\n\n" + prev + "\n\n---\n\n读者的批注：\n" + notes
               + "\n\n请按批注改，输出完整的第二到四节。批注和资料冲突时以资料为准，并在相应位置说明。"
                 "批注没提到的内容尽量不动。")
    else:
        _status(domain, stage="review", step="写综述", done=0, total=1)
        msg = base
    body = _only_body(strip_fence(_ask(chat_fn, msg)))
    rep = C.check_body(body, papers, tax)
    fixed = False
    if not rep["ok"]:
        _status(domain, step="核对没过，让模型改一次")
        fix = (msg + "\n\n---\n\n你写的这一版：\n\n" + body + "\n\n---\n\n程序核对发现这些问题：\n"
               + C.problems_text(rep) + "\n\n改正后输出完整的第二到四节，没问题的内容不要动。")
        try:
            body2 = _only_body(strip_fence(_ask(chat_fn, fix)))
            rep2 = C.check_body(body2, papers, tax)
            n = lambda r: sum(len(v) for v in r["problems"].values())  # noqa: E731
            if n(rep2) <= n(rep):
                body, rep, fixed = body2, rep2, True
        except Exception:
            pass
    by = {p["id"]: p for p in papers}
    model = load_config().get("model", "")
    full = "\n\n".join([render_section1(tax, by, cards), body.strip(),
                        render_section5(domain, papers, tax, cards, skipped_count(domain), model)]) + "\n"
    (d / "review_body.md").write_text(body, encoding="utf-8")
    (d / "review.md").write_text(full, encoding="utf-8")
    hist = meta.get("notes", [])
    if notes:
        hist.append({"at": _now(), "text": notes})
    meta = {"check": rep, "fixed_once": fixed, "built_at": _now(), "model": model,
            "taxonomy_at": tax.get("updated_at"), "papers": len(papers), "notes": hist}
    _write(d / "review.json", meta)
    _status(domain, done=1)
    return meta


# ---------- 运行 ----------

def run(domain: str, start: str = "cards", force_cards: bool = False, notes: str | None = None,
        chat_fn: ChatFn | None = None) -> dict[str, Any]:
    with _RUN_LOCK:
        if domain in _RUNNING:
            raise RuntimeError(f"{DOMAIN_CN.get(domain, domain)}的综述正在生成，等它跑完")
        _RUNNING.add(domain)
    try:
        return _run(domain, start, force_cards, notes, chat_fn or (lambda m: chat(m)))
    finally:
        with _RUN_LOCK:
            _RUNNING.discard(domain)


def _run(domain, start, force_cards, notes, chat_fn):
    if notes:
        start = "review"  # 按批注改稿只动第二到四节，不能重新分类覆盖你的调整
    if start not in STAGES:
        raise ValueError(f"start 只能是 {', '.join(STAGES)}")
    papers = load_corpus(domain)
    if not papers:
        raise ValueError(f"{DOMAIN_CN[domain]}领域没有可用的论文")
    d = out_dir(domain)
    d.mkdir(parents=True, exist_ok=True)
    _status(domain, state="running", stage=start, step="准备资料", done=0, total=0, error=None,
            started_at=_now(), finished_at=None, model=load_config().get("model", ""))
    todo = STAGES[STAGES.index(start):]
    cards = _read(d / "cards.json", {}).get("cards", {})
    if "cards" in todo:
        cards = make_cards(domain, papers, chat_fn, force_cards)["cards"]
    tax = _read(d / "taxonomy.json", None)
    if "taxonomy" in todo:
        tax = make_taxonomy(domain, papers, cards, chat_fn)
    if not tax:
        raise ValueError("还没分类，先分类")
    write_review(domain, papers, cards, tax, chat_fn, notes)
    return _status(domain, state="done", step="完成", finished_at=_now())


def start_background(domain: str, **kw: Any) -> dict[str, Any]:
    if domain in _RUNNING:
        raise RuntimeError(f"{DOMAIN_CN.get(domain, domain)}的综述正在生成，等它跑完")

    def work():
        try:
            run(domain, **kw)
        except Exception as e:
            _status(domain, state="error", step="出错", error=str(e)[:500], finished_at=_now(),
                    trace=traceback.format_exc()[-1500:])

    threading.Thread(target=work, daemon=True).start()
    return {"started": True, "domain": domain}


# ---------- 读取 ----------

def summary(domain: str) -> dict[str, Any]:
    d = out_dir(domain)
    st = _read(d / "status.json", {})
    if st.get("state") == "running" and domain not in _RUNNING:
        st["state"] = "stale"
    cards = _read(d / "cards.json", {}).get("cards", {})
    tax = _read(d / "taxonomy.json", None)
    meta = _read(d / "review.json", None)
    return {"state": st.get("state"), "cards": len(cards), "categories": len(tax["categories"]) if tax else 0,
            "reviewed": bool(meta), "review_ok": bool(meta and meta["check"]["ok"])}


def domain_list() -> list[dict[str, Any]]:
    return [{"domain": dm, "label": DOMAIN_CN[dm], "papers": len(load_corpus(dm)), **summary(dm)}
            for dm in REVIEW_DOMAINS]


def load_result(domain: str) -> dict[str, Any]:
    d = out_dir(domain)
    papers = load_corpus(domain)
    st = _read(d / "status.json", {})
    if st.get("state") == "running" and domain not in _RUNNING:
        st["state"] = "stale"  # 服务重启过，后台任务已经不在了
    cards = _read(d / "cards.json", {}).get("cards", {})
    tax = _read(d / "taxonomy.json", None)
    meta = _read(d / "review.json", None)
    review = (d / "review.md").read_text(encoding="utf-8") if (d / "review.md").exists() else ""
    fresh = {str(p["id"]) for p in papers if cards.get(str(p["id"]), {}).get("hash") == paper_hash(p)}
    placed = ({i for c in tax["categories"] for i in c["ids"]} | {o["id"] for o in tax["outside"]}) if tax else set()
    return {
        "domain": domain, "label": DOMAIN_CN[domain], "status": st,
        "papers": [{k: p[k] for k in ("id", "title", "url", "date")} for p in papers],
        "cards": {k: v for k, v in cards.items() if k in fresh},
        "taxonomy": tax, "review": review, "meta": meta,
        "pending": {
            "no_card": len(papers) - len(fresh),
            "not_classified": sum(1 for p in papers if str(p["id"]) in fresh and p["id"] not in placed),
            "taxonomy_newer": bool(tax and meta and tax.get("updated_at") != meta.get("taxonomy_at")),
        },
    }
