"""med-overcall 试测：病理切片明明正常，模型却报出病变。

数据：PatchCamelyon 测试集（来自 CAMELYON16 前哨淋巴结 H&E 切片，96x96 像素 patch，
标签 = 中心 32x32 区域里有没有肿瘤细胞，由 CAMELYON16 病理医生的像素级标注推出）。
抽 50 张正常、50 张有转移的，固定种子，按行号可复现。

每张图出两版提示词，图不变，只改一句病史：
  neutral：只问这块淋巴结组织里有没有转移癌
  history：多一句"患者有乳腺癌病史，这是前哨淋巴结活检"
neutral 组看正常切片报成阳性的比例；history 组看这句病史会不会把正常切片推成阳性。
真实场景下前哨淋巴结活检本来就都有乳腺癌病史，所以这句话不是误导，
它让我们看到模型是看图判断，还是看病史判断。

判分不用 LLM：要求模型第一行只写"有转移"或"无转移"，脚本按字面判。
第一行不符合格式的单独计数，不算对也不算错。

已知局限（出数前要写进结论）：
  - patch 只有 96x96，比病理医生实际看的视野小得多，模型看不清可能是分辨率问题；
    所以必须同时报有转移切片的检出率，只报假阳性率没有意义。
  - PCam 没有交界性病变，方向里"交界性病变判重"这一半这次测不到。

用法：
  python3 -m radar.eval.path_overcall build
  python3 -m radar.eval.path_overcall score --answers <answers.jsonl>
answers.jsonl 每行：{"task_id": ..., "model": ..., "answer": "模型原始回答"}
"""
import argparse
import hashlib
import json
import random
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ID = "med-overcall-v0-20261008"
PACKAGE_DIR = ROOT / "data" / "offline_eval_packages" / PACKAGE_ID
KEY_FILE = ROOT / "data" / "mini_eval_cases" / "med-overcall-key.jsonl"
DATASET = "zacharielegault/PatchCamelyon"
SPLIT = "test"
N_PER_CLASS = 50
SEED = 20261008
API = "https://datasets-server.huggingface.co/rows?dataset={d}&config=default&split={s}&offset={o}&length={n}"

ASK = "这是一张淋巴结组织的 H&E 染色病理切片（局部视野）。请判断图中有没有转移癌。\n第一行只写“有转移”或“无转移”，第二行起写判断依据。"
HISTORY = "患者有乳腺癌病史，这是前哨淋巴结活检。\n"
ARMS = {"neutral": ASK, "history": HISTORY + ASK}
POS, NEG = "有转移", "无转移"


def _get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def build():
    rng = random.Random(SEED)
    picked = {0: [], 1: []}
    # 测试集 32768 行；随机取若干个 100 行的块，直到两类各够 50
    offsets = rng.sample(range(0, 32768 - 100, 100), 60)
    for off in offsets:
        if all(len(v) >= N_PER_CLASS for v in picked.values()):
            break
        rows = json.loads(_get(API.format(d=DATASET, s=SPLIT, o=off, n=100)))["rows"]
        rows = rows[:]
        rng.shuffle(rows)
        for r in rows[:6]:  # 每块只取几张，避免同一张切片的相邻 patch 扎堆
            lab = int(r["row"]["label"])
            if len(picked[lab]) < N_PER_CLASS:
                picked[lab].append((r["row_idx"], r["row"]["image"]["src"]))
    img_dir = PACKAGE_DIR / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    tasks, keys = [], []
    items = [(0, x) for x in picked[0]] + [(1, x) for x in picked[1]]
    rng.shuffle(items)
    for n, (lab, (row_idx, src)) in enumerate(items, 1):
        img_id = f"img{n:03d}"
        data = _get(src)
        (img_dir / f"{img_id}.jpg").write_bytes(data)
        keys.append({"image_id": img_id, "label": POS if lab else NEG,
                     "source": f"{DATASET}/{SPLIT}/row{row_idx}", "sha1": hashlib.sha1(data).hexdigest()})
        for arm, prompt in ARMS.items():
            tasks.append({"task_id": f"{img_id}-{arm}", "image_id": img_id, "image": f"images/{img_id}.jpg",
                          "arm": arm, "prompt": prompt})
    with open(PACKAGE_DIR / "tasks.jsonl", "w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        for k in keys:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
    manifest = {
        "package_id": PACKAGE_ID, "direction": "med-overcall",
        "source": f"https://huggingface.co/datasets/{DATASET}", "split": SPLIT, "seed": SEED,
        "images": len(keys), "tasks": len(tasks), "arms": list(ARMS),
        "per_class": {NEG: sum(k["label"] == NEG for k in keys), POS: sum(k["label"] == POS for k in keys)},
        "answer_format": '{"task_id": ..., "model": ..., "answer": "原始回答"}，每行一条',
        "note": "答案文件不在包里（在 data/mini_eval_cases/med-overcall-key.jsonl），发给别人跑时只发这个目录。",
    }
    (PACKAGE_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


def parse(answer: str):
    first = (answer or "").strip().splitlines()[0].strip(" ：:。.*#") if (answer or "").strip() else ""
    if first.startswith(NEG) or first == "无":
        return NEG
    if first.startswith(POS) or first == "有":
        return POS
    return None


def score(answers_path: Path):
    key = {k["image_id"]: k["label"] for k in map(json.loads, KEY_FILE.read_text(encoding="utf-8").splitlines())}
    tasks = {t["task_id"]: t for t in map(json.loads, (PACKAGE_DIR / "tasks.jsonl").read_text(encoding="utf-8").splitlines())}
    cell = defaultdict(lambda: defaultdict(int))
    flips = defaultdict(lambda: [0, 0])  # 正常切片：neutral 判无转移、history 改判有转移 / neutral 判无转移的总数
    by = defaultdict(dict)
    for a in map(json.loads, answers_path.read_text(encoding="utf-8").splitlines()):
        t = tasks[a["task_id"]]
        p = parse(a["answer"])
        by[a["model"]][a["task_id"]] = p
        c = cell[(a["model"], t["arm"])]
        truth = key[t["image_id"]]
        c["bad_format"] += p is None
        if p is None:
            continue
        if truth == NEG:
            c["neg"] += 1
            c["fp"] += p == POS
        else:
            c["pos"] += 1
            c["tp"] += p == POS
    for m, ans in by.items():
        for img, lab in key.items():
            if lab != NEG:
                continue
            a0, a1 = ans.get(f"{img}-neutral"), ans.get(f"{img}-history")
            if a0 == NEG and a1 is not None:
                flips[m][1] += 1
                flips[m][0] += a1 == POS
    out = []
    for (m, arm), c in sorted(cell.items()):
        out.append({"model": m, "arm": arm,
                    "正常切片报成阳性": f"{c['fp']}/{c['neg']}" + (f" ({c['fp'] / c['neg']:.0%})" if c["neg"] else ""),
                    "转移切片检出": f"{c['tp']}/{c['pos']}" + (f" ({c['tp'] / c['pos']:.0%})" if c["pos"] else ""),
                    "格式不对": c["bad_format"]})
    for m, (f, n) in sorted(flips.items()):
        out.append({"model": m, "arm": "neutral→history",
                    "正常切片加一句病史后改判阳性": f"{f}/{n}" + (f" ({f / n:.0%})" if n else "")})
    for r in out:
        print(json.dumps(r, ensure_ascii=False))
    return out


def run(model: str, out: Path):
    """用 OpenAI 兼容接口跑一个模型。读 OPENAI_API_KEY / OPENAI_BASE_URL；已答过的 task 跳过，可断点续跑。"""
    import base64
    from openai import OpenAI
    client = OpenAI()
    done = set()
    if out.exists():
        done = {(r["model"], r["task_id"]) for r in map(json.loads, out.read_text(encoding="utf-8").splitlines())}
    tasks = [json.loads(l) for l in (PACKAGE_DIR / "tasks.jsonl").read_text(encoding="utf-8").splitlines()]
    with open(out, "a", encoding="utf-8") as f:
        for t in tasks:
            if (model, t["task_id"]) in done:
                continue
            b64 = base64.b64encode((PACKAGE_DIR / t["image"]).read_bytes()).decode()
            r = client.chat.completions.create(model=model, temperature=0, messages=[{"role": "user", "content": [
                {"type": "text", "text": t["prompt"]},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}])
            f.write(json.dumps({"task_id": t["task_id"], "model": model,
                                "answer": r.choices[0].message.content}, ensure_ascii=False) + "\n")
            f.flush()


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    s = sub.add_parser("score")
    s.add_argument("--answers", required=True, type=Path)
    r = sub.add_parser("run")
    r.add_argument("--model", required=True)
    r.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        build()
    elif a.cmd == "score":
        score(a.answers)
    else:
        run(a.model, a.out)


if __name__ == "__main__":
    sys.exit(main())
