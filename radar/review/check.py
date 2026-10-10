"""防编造的核对。只管"不许编"，不打分，也不判断写得好不好。

硬性问题（会打回给模型改一次，改完还有就在页面上标红）：
  - 引用了资料里不存在的编号
  - 「」里的原话在同一行所引论文的摘要里找不到
  - 缺少第二、三、四节

提醒（不打回，只在页面上提示）：
  - 分类里有某一类，第二节没写到
"""
from __future__ import annotations

import re
from typing import Any

CITE_RE = re.compile(r"\[#\s*(\d+(?:\s*[,，、]\s*#?\s*\d+)*)\s*\]")
QUOTE_RE = re.compile(r"「([^」]{4,})」")
BODY_SECTIONS = [("二", "各类做到哪、共同短板"), ("三", "大家还没研究什么"), ("四", "我们能研究什么")]
WEEK_SECTIONS = [("二", "本周新论文说明了什么"), ("三", "和全部综述比")]


BARE_RE = re.compile(r"(?<![\[\w#])#(\d{2,6})\b")  # 模型有时不加方括号，直接写 #1672


def cites(text: str) -> list[int]:
    out: list[int] = []
    for m in CITE_RE.finditer(text):
        out += [int(x) for x in re.findall(r"\d+", m.group(1))]
    out += [int(x) for x in BARE_RE.findall(CITE_RE.sub("", text))]
    return out


def norm(s: str) -> str:
    s = s.lower()
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r"[\u2010-\u2015]", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,;:")


def quote_in(quote: str, paper: dict[str, Any]) -> bool:
    q = norm(quote)
    return len(q) >= 8 and q in norm(paper["title"] + " " + paper["abstract"])


def _section_key(line: str, sections=BODY_SECTIONS) -> str | None:
    if not line.startswith("## "):
        return None
    head = line[3:].strip()
    for key, _ in sections:
        if head.startswith(key):
            return key
    return "_other"


def check_body(body: str, papers: list[dict[str, Any]], taxonomy: dict[str, Any] | None,
               sections=BODY_SECTIONS) -> dict[str, Any]:
    """sections 默认是全部综述的第二到四节；本周小结传 WEEK_SECTIONS（第二、三节）。"""
    by_id = {p["id"]: p for p in papers}
    lines = body.splitlines()
    present = {k for k in (_section_key(x, sections) for x in lines) if k}
    missing = [f"{k}、{w}" for k, w in sections if k not in present]
    invalid = sorted({i for i in cites(body) if i not in by_id})

    fake, ok = [], 0
    for line in lines:
        for q in QUOTE_RE.findall(line):
            ids = [i for i in cites(line) if i in by_id]
            if ids and any(quote_in(q, by_id[i]) for i in ids):
                ok += 1
            else:
                fake.append({"quote": q[:240], "cited": ids,
                             "reason": "这一行没标出处" if not ids else "所引论文的摘要里找不到这句"})

    # 第二节写到了哪些类
    heads, cur = [], None
    for line in lines:
        k = _section_key(line, sections)
        if k:
            cur = k
        elif cur == "二" and (line.startswith("### ") or line.startswith("#### ")):
            # 两层分类：### QA 类 / ### Agent 类，下面 #### 主题名
            heads.append(re.sub(r"[（(].*?[）)]", "", line.lstrip("#")).strip())
    not_discussed = []
    for c in (taxonomy or {}).get("categories", []):
        n = c["name"]
        if not any(n in h or (h and h in n) for h in heads):
            not_discussed.append(n)

    return {
        "ok": not (missing or invalid or fake),
        "quotes_ok": ok,
        "cited": sorted({i for i in cites(body) if i in by_id}),
        "problems": {"missing_sections": missing, "invalid_ids": invalid, "fake_quotes": fake},
        "warnings": {"categories_not_discussed": not_discussed},
    }


def problems_text(rep: dict[str, Any]) -> str:
    p = rep["problems"]
    L = []
    if p["missing_sections"]:
        L.append("缺少这些节：" + "、".join(p["missing_sections"]) + "。标题要按要求写。")
    if p["invalid_ids"]:
        L.append("这些编号资料里没有，删掉或改成正确的编号：" + "、".join(f"#{i}" for i in p["invalid_ids"]))
    if p["fake_quotes"]:
        L.append("这些原话对不上（只能照抄卡片里的作者原话，一字不改，并在同一行标出处），改正或删掉：")
        L += [f"- 「{q['quote']}」：{q['reason']}" for q in p["fake_quotes"][:40]]
    return "\n".join(L)
