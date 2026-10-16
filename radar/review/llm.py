"""模型接口：任何 OpenAI 兼容的 /chat/completions 都行（OpenAI、DeepSeek、混元、本地 vLLM……）。

网页：接口地址、模型名、密钥只存在用户自己浏览器的 localStorage，每次请求放在请求头里带过来，
服务器只在这次任务的内存里用，不写文件、不进日志（use_config）。服务器上不保存任何人的密钥。
命令行：读环境变量 RADAR_LLM_BASE_URL / RADAR_LLM_API_KEY / RADAR_LLM_MODEL（或 OPENAI_*），
或本机 data/llm_config.json（不进 git，只在自己电脑上用）。
只用标准库，不额外装包。
"""
from __future__ import annotations

import json
import os
import re
import threading
import urllib.error
import urllib.request
from typing import Any

from radar.core.radar_core import BASE_DIR

CONFIG_PATH = BASE_DIR / "data" / "llm_config.json"
DEFAULT_BASE = "https://api.openai.com/v1"


_TL = threading.local()


class use_config:
    """在这个线程里用指定的配置（网页请求带来的），不读文件和环境变量。"""

    def __init__(self, cfg: dict[str, Any] | None):
        self.cfg = cfg

    def __enter__(self):
        self.old = getattr(_TL, "cfg", None)
        _TL.cfg = self.cfg
        return self.cfg

    def __exit__(self, *a):
        _TL.cfg = self.old


def _norm_base(base: str) -> str:
    base = (base or DEFAULT_BASE).strip().rstrip("/")
    return re.sub(r"/chat/completions$", "", base)  # 填了完整地址也能用


def make_config(base_url: str, api_key: str, model: str, max_tokens: int = 8000) -> dict[str, Any]:
    return {"base_url": _norm_base(base_url), "api_key": (api_key or "").strip(), "model": (model or "").strip(),
            "max_tokens": int(max_tokens or 8000), "temperature": 0.2}


def load_config() -> dict[str, Any]:
    if getattr(_TL, "cfg", None) is not None:
        return _TL.cfg
    cfg: dict[str, Any] = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cfg = {}
    base = _norm_base(cfg.get("base_url") or os.getenv("RADAR_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "")
    return {
        "base_url": base,
        "api_key": cfg.get("api_key") or os.getenv("RADAR_LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "",
        "model": cfg.get("model") or os.getenv("RADAR_LLM_MODEL") or "",
        "max_tokens": int(cfg.get("max_tokens") or 8000),
        "temperature": float(cfg.get("temperature") if cfg.get("temperature") is not None else 0.2),
    }


def public_config(c: dict[str, Any] | None = None) -> dict[str, Any]:
    c = c or load_config()
    k = c["api_key"]
    return {"base_url": c["base_url"], "model": c["model"], "max_tokens": c["max_tokens"],
            "api_key_set": bool(k), "api_key_hint": (k[:3] + "…" + k[-4:]) if len(k) > 8 else ("已填" if k else ""),
            "ready": bool(k and c["model"])}


class LLMError(RuntimeError):
    pass


def chat(messages: list[dict[str, str]], cfg: dict[str, Any] | None = None, timeout: int = 900) -> str:
    cfg = cfg or load_config()
    if not cfg["api_key"] or not cfg["model"]:
        raise LLMError("还没接入模型：先在页面上填接口地址、密钥和模型名")
    body = json.dumps({"model": cfg["model"], "messages": messages,
                       "temperature": cfg["temperature"], "max_tokens": cfg["max_tokens"]}).encode()
    req = urllib.request.Request(cfg["base_url"] + "/chat/completions", data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {cfg['api_key']}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LLMError(f"接口返回 {e.code}：{e.read().decode('utf-8', 'replace')[:300]}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"连不上接口：{e.reason}") from e
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"接口返回格式不对：{str(data)[:300]}") from e


def extract_json(text: str) -> Any:
    """从模型回复里取出第一个完整的 JSON（允许外面包着 ```json 或几句话）。"""
    t = text.strip()
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", t, re.S)
    if m:
        t = m.group(1)
    dec = json.JSONDecoder()
    tried = 0
    for i, ch in enumerate(t):
        if ch not in "[{":
            continue
        try:
            return dec.raw_decode(t[i:])[0]
        except json.JSONDecodeError:
            tried += 1
            if tried > 20:
                break
    raise LLMError("模型没有按要求返回 JSON：" + text[:200])


def strip_fence(text: str) -> str:
    t = text.strip()
    m = re.match(r"^```(?:markdown|md)?\s*\n(.*)\n```\s*$", t, re.S)
    return (m.group(1) if m else t).strip() + "\n"


def ping(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    out = chat([{"role": "user", "content": "只回复两个字：收到"}], {**(cfg or load_config()), "max_tokens": 20})
    return {"ok": True, "reply": out.strip()[:50]}
