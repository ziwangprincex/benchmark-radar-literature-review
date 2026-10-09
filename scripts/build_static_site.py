"""把网页导出成静态站点，给 GitHub Pages 用。

用法: python3 scripts/build_static_site.py [输出目录，默认 site]

做法：用 Flask 测试客户端把网页要读的接口逐个请求一遍，存成 JSON；
页面里的 /api/* 请求由 static/static_shim.js 换成读这些文件。
只导出"看"需要的数据；跑模型、重建索引等写操作网页版不支持。
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from radar.review.corpus import REVIEW_DOMAINS  # noqa: E402
from radar.web.app import app  # noqa: E402

GET_ENDPOINTS = ["reading", "dashboard", "ideas", "sources", "signals", "review/config"] + \
                [f"review/{d}" for d in REVIEW_DOMAINS]


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "site").resolve()
    if out.exists():
        shutil.rmtree(out)
    (out / "api" / "review").mkdir(parents=True)
    shutil.copytree(ROOT / "radar" / "web" / "static", out / "static")

    client = app.test_client()
    sizes = {}
    for ep in GET_ENDPOINTS:
        url = f"/api/{ep}" + ("?limit=20" if ep == "signals" else "")
        r = client.get(url)
        if r.status_code != 200:
            raise SystemExit(f"{url} 返回 {r.status_code}: {r.get_data(as_text=True)[:200]}")
        data = r.get_json()
        if ep == "review/config":  # 不把本机的模型设置带到公开网页上
            data["llm"] = {"base_url": "", "model": "", "max_tokens": 0, "api_key_set": False,
                           "api_key_hint": "", "ready": False}
        path = out / "api" / f"{ep}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        sizes[ep] = path.stat().st_size

    html = client.get("/").get_data(as_text=True).replace('"/static/', '"static/')
    html = html.replace('<script src="static/app.js', '<script src="static/static_shim.js"></script>\n  <script src="static/app.js', 1)
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(json.dumps({"out": str(out), "kb": {k: v // 1024 for k, v in sizes.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
