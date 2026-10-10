"""文献综述：按写综述的步骤分三步，每一步的结果都存下来，能在页面上看、能改。

  ① 逐篇抽卡  每篇摘要 → 测什么、输入、怎么判分、数据、主要发现、作者承认的局限（原话）
  ② 分类      根据卡片按"测什么"分类，并说明为什么这么分；你可以在页面上调整
  ③ 写综述    第一节（分类）和第五节（边界）由程序按数据生成，第二到四节由模型综合
  批注改稿    你写批注，模型照着改第二到四节

程序只做"不许编造"的核对：编号要存在，「」里的原话要在所引论文的摘要里。
没过就把问题列给模型改一次；还没过照样保存，但在页面上标出来。不打分。

两种范围（scope）：
  all   全部综述：该领域收进来的全部论文，按上面三步写
  week  本周小结：只看最近一周新收的论文。卡片和全部综述共用（不重复抽）；分类时先往全部综述的
        已有类里放，放不进的才算新方向；小结只写本周带来了什么变化：新方向、补上了哪些空白、
        和"我们能研究什么"撞车的

产物在 reports/lit_review/<领域>/：
  cards.json     每篇的卡片（按摘要内容缓存，新论文进来只抽新的；全部和本周共用）
  taxonomy.json  分类（by=model 或 by=user）
  review.md      完整综述；review_body.md 是模型写的第二到四节
  review.json    核对结果、生成时间、批注记录
  status.json    运行状态（网页轮询用）
  week/<周一日期>/  本周小结：taxonomy.json、review.md、review_body.md、review.json
  week/status.json  本周小结的运行状态
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
from radar.review.corpus import REVIEW_DOMAINS, SCOPES, corpus_text, latest_week, load_corpus, skipped_count
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
_TL = threading.local()  # 当前线程在跑哪个范围，决定状态写到哪


def _scope() -> str:
    return getattr(_TL, "scope", "all")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def out_dir(domain: str) -> Path:
    return OUT_ROOT / domain


def week_dir(domain: str, wk: str | None = None) -> Path:
    return OUT_ROOT / domain / "week" / (wk or latest_week() or "none")


def _status_path(domain: str, scope: str) -> Path:
    return out_dir(domain) / ("week" if scope == "week" else "") / "status.json"


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
    p = _status_path(domain, _scope())
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
    cats, no_ids = [], []
    for c in data.get("categories") or []:
        if not isinstance(c, dict):
            continue
        got = take(c.get("ids"))
        name = str(c.get("name") or "").strip()[:40]
        if name and not got:
            no_ids.append(name)
        if got and name:
            cats.append({"name": name, "tests": str(c.get("tests") or "").strip(),
                         "why": str(c.get("why") or "").strip(), "ids": got})
    outside = []
    for o in data.get("outside") or []:
        if isinstance(o, dict):
            got = take([o.get("id")])
            if got:
                outside.append({"id": got[0], "reason": str(o.get("reason") or "").strip()})
    return {"categories": cats, "outside": outside, "missing": sorted(ids - seen), "no_ids": no_ids}


def _ask_taxonomy(domain: str, msg: str, ids: set[int], chat_fn: ChatFn) -> dict[str, Any]:
    """让模型分类；有论文没出现就把漏的列给它补一次，还漏的放进"不算"并注明。"""
    raw = _ask(chat_fn, msg)
    tax = normalize_taxonomy(extract_json(raw), ids)
    if tax["missing"]:
        # 把模型原始回复和具体问题发回去，不要发整理后的结果（没有 ids 的类会被整理掉，模型看不出错在哪）
        why = []
        if tax["no_ids"]:
            why.append("这些类没有写 ids（每一类都必须有 \"ids\": [编号, …]，列出归到这一类的论文编号）："
                       + "、".join(tax["no_ids"]))
        why.append("这些编号一次都没出现：" + "、".join(f"#{i}" for i in tax["missing"]))
        fix = (msg + "\n\n---\n\n你上一次的回复：\n" + raw[:6000] + "\n\n问题：\n" + "\n".join(why)
               + "\n\n每篇必须出现一次。改正后输出完整的 JSON，格式和上面要求的一样。")
        try:
            tax2 = normalize_taxonomy(extract_json(_ask(chat_fn, fix)), ids)
            if len(tax2["missing"]) < len(tax["missing"]) and tax2["categories"]:
                tax = tax2
        except Exception:
            pass
    tax.pop("no_ids", None)
    if not tax["categories"]:
        raise ValueError("分类失败：模型两次都没给出可用的分类（类里没有论文编号）。可以重试，或换个模型")
    for i in tax.pop("missing"):
        tax["outside"].append({"id": i, "reason": "模型没归类，需要你手动放进某一类"})
    return tax


def make_taxonomy(domain: str, papers: list[dict[str, Any]], cards: dict[str, Any], chat_fn: ChatFn) -> dict[str, Any]:
    use = [p for p in papers if str(p["id"]) in cards]
    if not use:
        raise ValueError("还没有卡片，先抽卡")
    _status(domain, stage="taxonomy", step="分类", done=0, total=len(use))
    msg = (f"{prompt('taxonomy')}\n\n---\n\n领域：{DOMAIN_CN[domain]}，共 {len(use)} 篇。\n\n"
           + "\n".join(_card_line(cards[str(p["id"])], p) for p in use))
    tax = _ask_taxonomy(domain, msg, {p["id"] for p in use}, chat_fn)
    tax.update(by="model", updated_at=_now())
    _write(out_dir(domain) / "taxonomy.json", tax)
    _status(domain, done=len(use))
    return tax


def _mark_new(tax: dict[str, Any], base: dict[str, Any] | None) -> dict[str, Any]:
    """本周的类在全部综述里没有的，标 new。"""
    names = {c["name"] for c in (base or {}).get("categories", [])}
    for c in tax["categories"]:
        c["new"] = c["name"] not in names
    return tax


def make_week_taxonomy(domain: str, papers: list[dict[str, Any]], cards: dict[str, Any], chat_fn: ChatFn,
                       wk: str) -> dict[str, Any]:
    use = [p for p in papers if str(p["id"]) in cards]
    if not use:
        raise ValueError("本周论文还没有卡片，先抽卡")
    base = _read(out_dir(domain) / "taxonomy.json", None)
    if base:
        btxt = "已有分类（全部综述里的类，能放进去的就照抄类名）：\n" + "\n".join(
            f"- {c['name']}：{c['tests']}" for c in base["categories"])
    else:
        btxt = "还没有已有分类（全部综述还没写），请自己分类。"
    _status(domain, stage="taxonomy", step="分类", done=0, total=len(use))
    msg = (prompt("week_taxonomy").replace("{base}", btxt)
           + f"\n\n---\n\n领域：{DOMAIN_CN[domain]}，本周（{wk} 起）共 {len(use)} 篇。\n\n"
           + "\n".join(_card_line(cards[str(p["id"])], p) for p in use))
    tax = _mark_new(_ask_taxonomy(domain, msg, {p["id"] for p in use}, chat_fn), base)
    tax.update(by="model", updated_at=_now(), week=wk, base_at=(base or {}).get("updated_at"))
    _write(week_dir(domain, wk) / "taxonomy.json", tax)
    _status(domain, done=len(use))
    return tax


def save_taxonomy(domain: str, payload: dict[str, Any], scope: str = "all") -> dict[str, Any]:
    papers = load_corpus(domain, scope=scope) if scope == "week" else load_corpus(domain)
    tax = normalize_taxonomy(payload, {p["id"] for p in papers})
    tax.pop("missing")
    tax.pop("no_ids", None)
    if not tax["categories"]:
        raise ValueError("至少要有一类")
    tax.update(by="user", updated_at=_now())
    if scope == "week":
        wk = latest_week()
        old = _read(week_dir(domain, wk) / "taxonomy.json", {})
        _mark_new(tax, _read(out_dir(domain) / "taxonomy.json", None))
        tax.update(week=wk, base_at=old.get("base_at"))
        _write(week_dir(domain, wk) / "taxonomy.json", tax)
    else:
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


def _only_body(md: str, drop=("一", "五")) -> str:
    """只留模型写的那几节，丢掉它多写的程序负责的节（默认第一、五节）和前后的解释。"""
    out, keep = [], False
    for line in md.splitlines():
        if line.startswith("## "):
            h = line[3:].strip()
            keep = not any(h.startswith(x) for x in drop)
        if keep:
            out.append(line)
    return ("\n".join(out).strip() or md.strip()) + "\n"


def _ask_checked(domain: str, msg: str, papers: list[dict], tax: dict[str, Any], chat_fn: ChatFn,
                 sections=C.BODY_SECTIONS, keep=("一", "五"), what: str = "第二到四节") -> tuple[str, dict, bool]:
    """让模型写，程序核对；没过就把问题列给模型改一次，改完问题没变多就用改过的。"""
    body = _only_body(strip_fence(_ask(chat_fn, msg)), keep)
    rep = C.check_body(body, papers, tax, sections)
    fixed = False
    if not rep["ok"]:
        _status(domain, step="核对没过，让模型改一次")
        fix = (msg + "\n\n---\n\n你写的这一版：\n\n" + body + "\n\n---\n\n程序核对发现这些问题：\n"
               + C.problems_text(rep) + f"\n\n改正后输出完整的{what}，没问题的内容不要动。")
        try:
            body2 = _only_body(strip_fence(_ask(chat_fn, fix)), keep)
            rep2 = C.check_body(body2, papers, tax, sections)
            n = lambda r: sum(len(v) for v in r["problems"].values())  # noqa: E731
            if n(rep2) <= n(rep):
                body, rep, fixed = body2, rep2, True
        except Exception:
            pass
    return body, rep, fixed


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
    body, rep, fixed = _ask_checked(domain, msg, papers, tax, chat_fn)
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


# ---------- 本周小结 ----------

def render_week_section1(tax: dict[str, Any], by: dict[int, dict], cards: dict[str, Any], has_base: bool) -> str:
    cats = tax["categories"]
    n = sum(len(c["ids"]) for c in cats)
    newn = sum(1 for c in cats if c.get("new"))
    head = f"## 一、本周新论文分几类：{n} 篇分 {len(cats)} 类"
    if has_base:
        head += f"，{newn} 类是全部综述里没有的" if newn else "，都能放进全部综述已有的类"
    if has_base:
        L = [head, "", "| 类别 | 篇数 | 全部综述里 | 测什么 |", "|---|---|---|---|"]
        L += [f"| {_cell(c['name'])} | {len(c['ids'])} | {'新' if c.get('new') else '已有'} | {_cell(c['tests'])} |"
              for c in cats]
    else:  # 没有全部综述就没法判断新不新，不显示这一列
        L = [head, "", "| 类别 | 篇数 | 测什么 |", "|---|---|---|"]
        L += [f"| {_cell(c['name'])} | {len(c['ids'])} | {_cell(c['tests'])} |" for c in cats]
    for c in cats:
        L += ["", f"### {c['name']}（{len(c['ids'])} 篇{'，新' if c.get('new') and has_base else ''}）", ""]
        for i in c["ids"]:
            if i in by:
                task = cards.get(str(i), {}).get("task", "")
                L.append(f"- {by[i]['title']} [#{i}]" + (f"：{task}" if task else ""))
    if tax["outside"]:
        L += ["", f"### 没算进来的（{len(tax['outside'])} 篇）", ""]
        L += [f"- {by[o['id']]['title']} [#{o['id']}]：{o['reason'] or '不是 Benchmark'}" for o in tax["outside"]
              if o["id"] in by]
    return "\n".join(L)


def render_week_section4(domain: str, wk: str, papers: list[dict], base_meta: dict | None, model: str) -> str:
    L = ["## 四、这份小结的边界", "",
         f"- 资料：{wk} 那周新收的{DOMAIN_CN[domain]}领域 arXiv 论文 {len(papers)} 篇，只读了标题和摘要。"
         "补进来的历史论文不算本周。",
         (f"- 对比用的是 {base_meta['built_at'][:10]} 写的全部综述（{base_meta.get('papers', '?')} 篇）。"
          "全部综述之后改过的分类和内容，这里没有跟着变。") if base_meta else
         "- 这个领域还没写全部综述，所以没法判断哪些是新方向、补上了哪些空白。先写全部综述再更新小结。",
         f"- 第二、三节由 {model or '模型'} 生成。用之前请自己读一遍，点 #编号 能打开原文。"]
    return "\n".join(L)


def _base_sections(domain: str) -> str:
    """全部综述里模型写的第三、四节（还没研究什么、我们能研究什么），给本周小结比对用。"""
    p = out_dir(domain) / "review_body.md"
    if not p.exists():
        return ""
    out, keep = [], False
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            h = line[3:].strip()
            keep = h.startswith("三") or h.startswith("四")
        if keep:
            out.append(line)
    return "\n".join(out).strip()


def write_week(domain: str, wk: str, papers: list[dict], cards: dict[str, Any], tax: dict[str, Any],
               chat_fn: ChatFn, notes: str | None = None) -> dict[str, Any]:
    d = week_dir(domain, wk)
    meta = _read(d / "review.json", {})
    prev = (d / "review_body.md").read_text(encoding="utf-8") if (d / "review_body.md").exists() else ""
    base_meta = _read(out_dir(domain) / "review.json", None)
    base = _base_sections(domain)
    mat = _material(tax, papers, cards).replace("### 分类", "### 本周分类（标\"新\"的是全部综述里没有的类）")
    for c in tax["categories"]:
        if c.get("new"):
            mat = mat.replace(f". {c['name']}（", f". {c['name']}【新】（", 1)
    msg = (f"{prompt('week')}\n\n---\n\n领域：{DOMAIN_CN[domain]}，本周（{wk} 起）\n\n{mat}\n\n---\n\n"
           + (f"### 全部综述的第三、四节\n\n{base}" if base else "### 全部综述\n\n还没有全部综述。"))
    if notes and prev:
        _status(domain, stage="review", step="按批注改稿", done=0, total=1)
        msg += ("\n\n---\n\n上一版的第二、三节：\n\n" + prev + "\n\n---\n\n读者的批注：\n" + notes
                + "\n\n请按批注改，输出完整的第二、三节。批注和资料冲突时以资料为准。批注没提到的内容尽量不动。")
    else:
        _status(domain, stage="review", step="写本周小结", done=0, total=1)
    body, rep, fixed = _ask_checked(domain, msg, papers, tax, chat_fn, sections=C.WEEK_SECTIONS,
                                    keep=("一", "四", "五"), what="第二、三节")
    rep["warnings"]["categories_not_discussed"] = []  # 本周一类常只有一篇，不要求每类都写到
    by = {p["id"]: p for p in papers}
    model = load_config().get("model", "")
    full = "\n\n".join([render_week_section1(tax, by, cards, bool(base_meta)), body.strip(),
                         render_week_section4(domain, wk, papers, base_meta, model)]) + "\n"
    d.mkdir(parents=True, exist_ok=True)
    (d / "review_body.md").write_text(body, encoding="utf-8")
    (d / "review.md").write_text(full, encoding="utf-8")
    hist = meta.get("notes", [])
    if notes:
        hist.append({"at": _now(), "text": notes})
    meta = {"check": rep, "fixed_once": fixed, "built_at": _now(), "model": model, "week": wk,
            "taxonomy_at": tax.get("updated_at"), "papers": len(papers), "notes": hist,
            "base_at": (base_meta or {}).get("built_at")}
    _write(d / "review.json", meta)
    _status(domain, done=1)
    return meta


# ---------- 运行 ----------

def run(domain: str, start: str = "cards", force_cards: bool = False, notes: str | None = None,
        chat_fn: ChatFn | None = None, scope: str = "all") -> dict[str, Any]:
    if scope not in SCOPES:
        raise ValueError(f"范围只能是 {'、'.join(SCOPES)}")
    with _RUN_LOCK:
        if domain in _RUNNING:  # 全部和本周共用卡片，同一领域一次只跑一个
            raise RuntimeError(f"{DOMAIN_CN.get(domain, domain)}的综述正在生成，等它跑完")
        _RUNNING.add(domain)
    _TL.scope = scope
    try:
        fn = _run_week if scope == "week" else _run
        return fn(domain, start, force_cards, notes, chat_fn or (lambda m: chat(m)))
    finally:
        _TL.scope = "all"
        with _RUN_LOCK:
            _RUNNING.discard(domain)


def _begin(domain, start, notes):
    if notes:
        start = "review"  # 按批注改稿只动模型写的那几节，不能重新分类覆盖你的调整
    if start not in STAGES:
        raise ValueError(f"start 只能是 {', '.join(STAGES)}")
    out_dir(domain).mkdir(parents=True, exist_ok=True)
    _status(domain, state="running", stage=start, step="准备资料", done=0, total=0, error=None,
            started_at=_now(), finished_at=None, model=load_config().get("model", ""))
    return STAGES[STAGES.index(start):]


def _run(domain, start, force_cards, notes, chat_fn):
    papers = load_corpus(domain)
    if not papers:
        raise ValueError(f"{DOMAIN_CN[domain]}领域没有可用的论文")
    todo = _begin(domain, start, notes)
    d = out_dir(domain)
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


def _run_week(domain, start, force_cards, notes, chat_fn):
    wk = latest_week()
    papers = load_corpus(domain, scope="week")
    if not papers:
        raise ValueError(f"{DOMAIN_CN[domain]}领域本周没有新论文")
    todo = _begin(domain, start, notes)
    cards = _read(out_dir(domain) / "cards.json", {}).get("cards", {})
    if "cards" in todo:  # 只抽本周论文的卡，存进全部综述共用的 cards.json
        cards = make_cards(domain, papers, chat_fn, force_cards)["cards"]
    tax = _read(week_dir(domain, wk) / "taxonomy.json", None)
    if "taxonomy" in todo:
        tax = make_week_taxonomy(domain, papers, cards, chat_fn, wk)
    if not tax:
        raise ValueError("本周还没分类，先分类")
    write_week(domain, wk, papers, cards, tax, chat_fn, notes)
    return _status(domain, state="done", step="完成", finished_at=_now())


def start_background(domain: str, scope: str = "all", **kw: Any) -> dict[str, Any]:
    if domain in _RUNNING:
        raise RuntimeError(f"{DOMAIN_CN.get(domain, domain)}的综述正在生成，等它跑完")

    def work():
        try:
            run(domain, scope=scope, **kw)
        except Exception as e:
            _TL.scope = scope
            _status(domain, state="error", step="出错", error=str(e)[:500], finished_at=_now(),
                    trace=traceback.format_exc()[-1500:])
            _TL.scope = "all"

    threading.Thread(target=work, daemon=True).start()
    return {"started": True, "domain": domain, "scope": scope}


# ---------- 读取 ----------

def _state(domain: str, scope: str) -> dict[str, Any]:
    st = _read(_status_path(domain, scope), {})
    if st.get("state") == "running" and domain not in _RUNNING:
        st["state"] = "stale"  # 服务重启过，后台任务已经不在了
    return st


def summary(domain: str, scope: str = "all") -> dict[str, Any]:
    d = out_dir(domain) if scope == "all" else week_dir(domain)
    cards = _read(out_dir(domain) / "cards.json", {}).get("cards", {})
    tax = _read(d / "taxonomy.json", None)
    meta = _read(d / "review.json", None)
    return {"state": _state(domain, scope).get("state"), "cards": len(cards),
            "categories": len(tax["categories"]) if tax else 0,
            "reviewed": bool(meta), "review_ok": bool(meta and meta["check"]["ok"])}


def domain_list() -> list[dict[str, Any]]:
    return [{"domain": dm, "label": DOMAIN_CN[dm], "papers": len(load_corpus(dm)),
             "week_papers": len(load_corpus(dm, scope="week")), **summary(dm),
             "week": summary(dm, "week")}
            for dm in REVIEW_DOMAINS]


def load_result(domain: str, scope: str = "all") -> dict[str, Any]:
    if scope not in SCOPES:
        raise ValueError(f"范围只能是 {'、'.join(SCOPES)}")
    wk = latest_week() if scope == "week" else None
    d = week_dir(domain, wk) if scope == "week" else out_dir(domain)
    papers = load_corpus(domain, scope="week") if scope == "week" else load_corpus(domain)
    cards = _read(out_dir(domain) / "cards.json", {}).get("cards", {})
    tax = _read(d / "taxonomy.json", None)
    meta = _read(d / "review.json", None)
    review = (d / "review.md").read_text(encoding="utf-8") if (d / "review.md").exists() else ""
    fresh = {str(p["id"]) for p in papers if cards.get(str(p["id"]), {}).get("hash") == paper_hash(p)}
    placed = ({i for c in tax["categories"] for i in c["ids"]} | {o["id"] for o in tax["outside"]}) if tax else set()
    out = {
        "domain": domain, "label": DOMAIN_CN[domain], "scope": scope, "status": _state(domain, scope),
        "papers": [{k: p[k] for k in ("id", "title", "url", "date")} for p in papers],
        "cards": {k: v for k, v in cards.items() if k in fresh},
        "taxonomy": tax, "review": review, "meta": meta,
        "pending": {
            "no_card": len(papers) - len(fresh),
            "not_classified": sum(1 for p in papers if str(p["id"]) in fresh and p["id"] not in placed),
            "taxonomy_newer": bool(tax and meta and tax.get("updated_at") != meta.get("taxonomy_at")),
        },
    }
    if scope == "week":
        base_meta = _read(out_dir(domain) / "review.json", None)
        out["week"] = wk
        out["base"] = {"reviewed": bool(base_meta), "built_at": (base_meta or {}).get("built_at"),
                       "papers": (base_meta or {}).get("papers")}
        out["pending"]["base_newer"] = bool(meta and base_meta and meta.get("base_at") != base_meta.get("built_at"))
        wroot = out_dir(domain) / "week"
        out["history"] = sorted([p.name for p in wroot.iterdir() if (p / "review.md").exists()],
                                reverse=True) if wroot.exists() else []
    return out
