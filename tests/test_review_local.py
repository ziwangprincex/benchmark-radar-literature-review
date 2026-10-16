"""浏览器本地存储与请求模型配置回归测试，不调用真实 API。"""
import importlib.util
import json
import tempfile
import threading
import time
from pathlib import Path
from unittest import mock

from radar.review import pipeline as P
from radar.review import session_store as M
from radar.review import llm

spec = importlib.util.spec_from_file_location("review_fixtures", Path(__file__).with_name("test_review.py"))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def test_request_config_reaches_card_worker_and_no_disk():
    cfg = llm.make_config("https://example.invalid/v1", "test-request-key", "test-request-model")
    main = threading.get_ident()
    calls = []
    fake = fixture.fake_model([])
    def request(messages, passed_cfg):
        calls.append((threading.get_ident(), dict(passed_cfg)))
        return fake(messages)
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(P, "OUT_ROOT", Path(tmp)), \
            mock.patch.object(P, "load_corpus", lambda d, **kw: fixture.PAPERS), \
            mock.patch.object(P, "skipped_count", lambda d: 0), \
            mock.patch.object(P, "chat", request), \
            mock.patch.object(llm, "CONFIG_PATH", Path(tmp) / "must-not-read.json"):
        Path(llm.CONFIG_PATH).write_text(json.dumps({"api_key": "server-key", "model": "server-model"}))
        P.run("legal", sid="localtest001", llm_cfg=cfg)
        assert any(t != main for t, _ in calls)
        assert all(c["api_key"] == cfg["api_key"] and c["model"] == cfg["model"] for _, c in calls)
        assert sorted(p.name for p in Path(tmp).iterdir()) == ["must-not-read.json"]
        files = M.snapshot("localtest001", "legal")
        assert "cards.json" in files and "review.md" in files
        assert cfg["api_key"] not in json.dumps(files)
        assert P.acknowledge("legal", "localtest001")
        assert not M.snapshot("localtest001", "legal")
        restored = P.browser_result("legal", "all", "localtest002", files)
        assert restored["review"]
        assert not M.exists("localtest002")
    P.forget("localtest001")


def test_missing_web_config_never_reads_server_config():
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(P, "OUT_ROOT", Path(tmp)), \
            mock.patch.object(P, "load_config", side_effect=AssertionError("server config read")):
        try:
            P.run("legal", sid="localtest003")
        except ValueError as exc:
            assert "缺少模型配置" in str(exc)
        else:
            raise AssertionError("missing request config accepted")
        assert not list(Path(tmp).iterdir())


def test_local_api_no_cache_and_no_retention():
    from radar.web.app import app
    files = {"cards.json": json.dumps({"cards": {}})}
    with mock.patch.object(P, "load_corpus", lambda d, **kw: fixture.PAPERS):
        c = app.test_client()
        r = c.post("/api/review/legal/local?sid=localtest004", json={"files": files})
        assert r.status_code == 200
        assert r.headers["Cache-Control"] == "no-store"
        assert r.json["files"] == files
        assert not M.exists("localtest004")
        assert c.post("/api/review/legal/local?sid=localtest004", json={"files": {"../../bad": "x"}}).status_code == 400
        assert c.get("/api/review/legal?sid=localtest005").json["cards"] == {}


def test_background_reserves_before_start_and_ack_releases():
    gate = threading.Event()
    def fake_run(domain, **kw):
        gate.wait(2)
        with P.session(kw["sid"]):
            P._status(domain, state="done")
    with mock.patch.object(P, "run", fake_run):
        P.start_background("legal", sid="localtest006", files={})
        try:
            P.start_background("legal", sid="localtest006", files={})
        except RuntimeError:
            pass
        else:
            raise AssertionError("duplicate background task accepted")
        assert not P.acknowledge("legal", "localtest006")
        gate.set()
        for _ in range(100):
            if ("localtest006", "legal") not in P._RUNNING:
                break
            time.sleep(.01)
        assert P.acknowledge("legal", "localtest006")
        assert not M.exists("localtest006")
