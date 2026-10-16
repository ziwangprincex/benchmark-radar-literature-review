"""网页任务临时存储：仅内存，不创建文件；长期状态由浏览器 IndexedDB 保存。"""
from __future__ import annotations

import json
import threading
import time
from copy import deepcopy
from typing import Any

LOCK = threading.RLock()
_FILES: dict[str, dict[str, str]] = {}
_SEEN: dict[str, float] = {}
_ABANDONED: set[str] = set()
FILES = frozenset({"cards.json", "taxonomy.json", "review.json", "review.md", "review_body.md", "status.json",
                   "week/taxonomy.json", "week/review.json", "week/review.md", "week/review_body.md", "week/status.json"})
MAX_BYTES = 40 * 1024 * 1024


def read(sid: str, name: str, default: str = "") -> str:
    with LOCK:
        return _FILES.get(sid, {}).get(name, default)


def write(sid: str, name: str, text: str) -> None:
    with LOCK:
        if sid in _ABANDONED:
            raise RuntimeError("页面已关闭，任务已终止")
        _FILES.setdefault(sid, {})[name] = text
        _SEEN[sid] = time.monotonic()


def touch(sid: str) -> None:
    with LOCK:
        if sid in _FILES:
            _SEEN[sid] = time.monotonic()


def exists(sid: str) -> bool:
    with LOCK:
        return sid in _FILES


def snapshot(sid: str, domain: str) -> dict[str, str]:
    prefix = domain + "/"
    with LOCK:
        return {k[len(prefix):]: v for k, v in _FILES.get(sid, {}).items()
                if k.startswith(prefix) and k[len(prefix):] in FILES}


def validate(files: Any) -> dict[str, str]:
    if not isinstance(files, dict) or any(k not in FILES or not isinstance(v, str) for k, v in files.items()):
        raise ValueError("本地结果格式无效")
    if sum(len(v.encode("utf-8")) for v in files.values()) > MAX_BYTES:
        raise ValueError("本地结果超过大小限制")
    for name, text in files.items():
        if name.endswith(".json"):
            try:
                value = json.loads(text)
            except (ValueError, TypeError) as exc:
                raise ValueError("本地结果包含无效 JSON") from exc
            if not isinstance(value, dict):
                raise ValueError("本地结果 JSON 必须为对象")
    return deepcopy(files)


def restore(sid: str, domain: str, files: Any) -> None:
    data = validate(files)
    with LOCK:
        _ABANDONED.discard(sid)
        delete_domain(sid, domain)
        _FILES.setdefault(sid, {}).update({domain + "/" + k: v for k, v in data.items()})
        _SEEN[sid] = time.monotonic()


def delete_domain(sid: str, domain: str, week_only: bool = False) -> None:
    prefix = domain + ("/week/" if week_only else "/")
    with LOCK:
        for k in list(_FILES.get(sid, {})):
            if k.startswith(prefix):
                del _FILES[sid][k]
        if sid in _FILES and not _FILES[sid]:
            _FILES.pop(sid, None)
            _SEEN.pop(sid, None)


def forget(sid: str, busy: bool = False) -> None:
    with LOCK:
        _FILES.pop(sid, None)
        _SEEN.pop(sid, None)
        if busy:
            _ABANDONED.add(sid)
        else:
            _ABANDONED.discard(sid)


def abandoned(sid: str) -> bool:
    with LOCK:
        return sid in _ABANDONED


def finish(sid: str) -> None:
    with LOCK:
        _ABANDONED.discard(sid)


def cleanup(max_age_s: float, busy: set[str]) -> int:
    with LOCK:
        old = [s for s, t in _SEEN.items() if s not in busy and time.monotonic() - t > max_age_s]
        for sid in old:
            forget(sid)
        return len(old)
