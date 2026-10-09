from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from radar.evidence.evidence_quality import claim_quality_summary, review_claim_evidence, sync_idea_quality
from radar.evidence.evidence_retrieval import retrieval_log, run_retrieval
from radar.core.radar_core import (
    BASE_DIR,
    add_failure_cases,
    add_mini_eval,
    coverage_matrix,
    dashboard,
    extract_pending,
    generate_ideas,
    get_idea,
    import_items,
    init_db,
    insert_source_item,
    list_failure_cases,
    list_ideas,
    list_signals,
    override_scores,
    run_pipeline,
    source_config,
    upsert_coverage_entry,
    weekly_report,
)

app = Flask(__name__)
app.json.ensure_ascii = False
init_db()


@app.get("/")
def home():
    import os
    static = os.path.join(os.path.dirname(__file__), "static")
    asset_v = int(max(os.path.getmtime(os.path.join(static, f)) for f in ("app.js", "review.js", "styles.css")))
    resp = app.make_response(render_template("index.html", asset_v=asset_v))
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/insights/")
@app.get("/insights/<path:filename>")
def insights(filename: str = "index.html"):
    return send_from_directory(BASE_DIR / "outputs" / "insights", filename)


@app.get("/api/dashboard")
def api_dashboard():
    return jsonify(dashboard())


@app.get("/api/sources")
def api_sources():
    return jsonify(source_config())


@app.post("/api/source-items")
def api_source_items():
    payload = request.get_json(force=True)
    items = payload if isinstance(payload, list) else [payload]
    try:
        stats = import_items(items)
        result = run_pipeline(collect=False) if request.args.get("process", "1") == "1" else {}
        return jsonify({"ok": True, "import": stats, "pipeline": result})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/signals")
def api_signals():
    return jsonify(list_signals(request.args.get("limit", 100, type=int), request.args.get("radar")))


@app.post("/api/failures")
def api_failures():
    payload = request.get_json(force=True)
    payload["radar"] = "model_failure"
    payload.setdefault("source_id", "human-feedback")
    try:
        stats = import_items([payload])
        return jsonify({"ok": True, "import": stats, "pipeline": run_pipeline(False)})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/failure-cases")
def api_failure_cases():
    return jsonify(list_failure_cases(
        idea_id=request.args.get("idea_id", type=int),
        model=request.args.get("model"),
        failure_type=request.args.get("failure_type"),
        severity=request.args.get("severity"),
        benchmark=request.args.get("benchmark"),
        limit=request.args.get("limit", 500, type=int),
    ))


@app.post("/api/ideas/<int:idea_id>/failure-cases")
def api_add_failure_cases(idea_id: int):
    payload = request.get_json(force=True)
    cases = payload.get("cases") if isinstance(payload, dict) else payload
    if not isinstance(cases, list):
        return jsonify({"error": "cases must be an array"}), 400
    source_item_id = payload.get("source_item_id") if isinstance(payload, dict) else None
    try:
        if not source_item_id:
            first = cases[0] if cases else {}
            source_item_id, _ = insert_source_item({
                "radar": "model_failure",
                "source_id": payload.get("source_id", "benchmark-run"),
                "title": payload.get("title", f"Failure Cases for Idea {idea_id}"),
                "content": payload.get("content", first.get("error_analysis") or first.get("failure_type") or "逐Case失败证据"),
                "url": payload.get("url", f"internal://failure-cases/{idea_id}"),
                "published_at": payload.get("run_date"),
                "evidence_role": "raw_source",
                "source_type": payload.get("source_type", "eval_run"),
                "run_id": payload.get("run_id", f"failure-cases-{idea_id}"),
                "cases": cases,
            })
            extract_pending()
            generate_ideas()
        ids = add_failure_cases(idea_id, cases, source_item_id=source_item_id)
        return jsonify({"ok": True, "inserted_case_ids": ids, "source_item_id": source_item_id})
    except KeyError:
        return jsonify({"error": "idea not found"}), 404
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/scout/run")
def api_scout_run():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"ok": True, "result": run_pipeline(collect=bool(payload.get("collect", False)))})
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503


@app.post("/api/demo/load")
def api_demo_load():
    path = BASE_DIR / "data" / "sample_source_items.json"
    stats = import_items(json.loads(path.read_text(encoding="utf-8")))
    return jsonify({"ok": True, "import": stats, "pipeline": run_pipeline(False)})


@app.get("/api/ideas")
def api_ideas():
    return jsonify(list_ideas(request.args.get("status"), request.args.get("domain"), request.args.get("q")))


@app.get("/api/ideas/<int:idea_id>")
def api_idea(idea_id: int):
    item = get_idea(idea_id)
    return jsonify(item) if item else (jsonify({"error": "not found"}), 404)


@app.patch("/api/ideas/<int:idea_id>/scores")
def api_scores(idea_id: int):
    payload = request.get_json(force=True)
    try:
        return jsonify(override_scores(idea_id, payload.get("scores", {}), payload.get("status")))
    except KeyError:
        return jsonify({"error": "not found"}), 404
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/ideas/<int:idea_id>/mini-evals")
def api_mini_eval(idea_id: int):
    try:
        return jsonify(add_mini_eval(idea_id, request.get_json(force=True)))
    except KeyError:
        return jsonify({"error": "not found"}), 404
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/ideas/<int:idea_id>/coverage-matrix")
def api_coverage_matrix(idea_id: int):
    return jsonify(coverage_matrix(idea_id))


@app.post("/api/ideas/<int:idea_id>/coverage-matrix")
def api_upsert_coverage(idea_id: int):
    try:
        entry_id = upsert_coverage_entry(idea_id, request.get_json(force=True))
        sync_idea_quality(idea_id)
        return jsonify({"ok": True, "entry_id": entry_id, "matrix": coverage_matrix(idea_id)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/ideas/<int:idea_id>/evidence-quality")
def api_evidence_quality(idea_id: int):
    try:
        sync_idea_quality(idea_id)
        return jsonify(claim_quality_summary(idea_id))
    except KeyError:
        return jsonify({"error": "idea not found"}), 404


@app.patch("/api/claim-evidence/<int:link_id>")
def api_review_claim_evidence(link_id: int):
    payload = request.get_json(force=True)
    try:
        return jsonify(review_claim_evidence(
            link_id, payload.get("support_relation", ""), payload.get("evidence_status", ""),
            payload.get("verifier", ""), payload.get("rationale", ""),
        ))
    except KeyError:
        return jsonify({"error": "claim-evidence link not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/ideas/<int:idea_id>/retrieve-evidence")
def api_retrieve_evidence(idea_id: int):
    payload = request.get_json(silent=True) or {}
    claim_types = set(payload.get("claim_types") or []) or None
    try:
        return jsonify({"ok": True, "retrieval": run_retrieval(idea_id, claim_types), "log": retrieval_log(idea_id)})
    except KeyError:
        return jsonify({"error": "idea not found"}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.get("/api/ideas/<int:idea_id>/retrieval-log")
def api_retrieval_log(idea_id: int):
    return jsonify(retrieval_log(idea_id))


@app.get("/api/evaluation-runs/<run_id>")
def api_evaluation_run(run_id: str):
    from radar.core.radar_core import db
    with db() as conn:
        run = conn.execute("SELECT * FROM evaluation_runs WHERE run_id=?", (run_id,)).fetchone()
        if not run:
            return jsonify({"error": "evaluation run not found"}), 404
        payload = dict(run)
        payload["protocol"] = json.loads(payload.pop("protocol_json") or "{}")
        payload["cases"] = [dict(x) for x in conn.execute(
            "SELECT * FROM failure_cases WHERE eval_run_id=? ORDER BY external_case_id,model_name", (run["id"],)
        ).fetchall()]
        return jsonify(payload)


@app.get("/api/weekly")
def api_weekly():
    return jsonify(weekly_report())


@app.get("/api/gap-candidates")
def api_gap_candidates():
    from radar.core import lit_index
    from radar.core.radar_core import db
    with db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='gap_candidates'").fetchone()
        meta = conn.execute("SELECT MAX(built_at) FROM gap_candidates").fetchone()[0] if exists else None
    cards = lit_index.load_cards() if exists else []
    return jsonify({"version": lit_index.LIT_VERSION, "built_at": meta, "cards": cards})


@app.get("/api/research-map")
def api_research_map():
    from radar.core.lit_index import research_map
    return jsonify(research_map())


@app.post("/api/gap-candidates/rebuild")
def api_gap_candidates_rebuild():
    from radar.core.lit_index import run as lit_run
    return jsonify({"ok": True, "stats": lit_run(BASE_DIR)})


@app.get("/api/reading")
def api_reading():
    from radar.core.reading import reading_list
    return jsonify(reading_list())


@app.put("/api/reading/batch")
def api_reading_batch():
    from radar.core.reading import set_state_many
    payload = request.get_json(force=True) or {}
    try:
        return jsonify(set_state_many(payload.get("ids") or [], payload.get("state", "")))
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.put("/api/reading/<int:item_id>")
def api_reading_set(item_id: int):
    from radar.core.reading import set_state
    try:
        return jsonify(set_state(item_id, (request.get_json(force=True) or {}).get("state", "")))
    except KeyError:
        return jsonify({"error": "not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


# ---------- 文献综述（需接入模型接口） ----------

def _review_domain_ok(domain: str) -> bool:
    from radar.review.corpus import REVIEW_DOMAINS
    return domain in REVIEW_DOMAINS


@app.get("/api/review/config")
def api_review_config():
    from radar.review.llm import public_config
    from radar.review.pipeline import PROMPTS, domain_list
    return jsonify({"llm": public_config(), "domains": domain_list(),
                    "prompts_path": str(PROMPTS.relative_to(BASE_DIR))})


@app.put("/api/review/config")
def api_review_config_set():
    from radar.review.llm import save_config
    return jsonify({"llm": save_config(request.get_json(force=True) or {})})


@app.post("/api/review/ping")
def api_review_ping():
    from radar.review.llm import LLMError, ping
    try:
        return jsonify(ping())
    except LLMError as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/review/<domain>")
def api_review_get(domain: str):
    from radar.review.pipeline import load_result
    if not _review_domain_ok(domain):
        return jsonify({"error": "未知领域"}), 400
    return jsonify(load_result(domain))


@app.post("/api/review/<domain>/run")
def api_review_run(domain: str):
    """从某一步开始往后跑：cards（逐篇抽卡，默认只抽新论文）/ taxonomy（分类）/ review（写综述）。
    带 notes 时只做"按批注改稿"。"""
    from radar.review.llm import public_config
    from radar.review.pipeline import STAGES, start_background
    if not _review_domain_ok(domain):
        return jsonify({"error": "未知领域"}), 400
    if not public_config()["ready"]:
        return jsonify({"error": "还没接入模型：先填接口地址、密钥和模型名"}), 400
    payload = request.get_json(force=True) or {}
    notes = (payload.get("notes") or "").strip() or None
    start = "review" if notes else payload.get("start", "cards")
    if start not in STAGES:
        return jsonify({"error": "start 不对"}), 400
    try:
        return jsonify(start_background(domain, start=start, force_cards=bool(payload.get("force_cards")),
                                        notes=notes))
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 409


@app.put("/api/review/<domain>/taxonomy")
def api_review_taxonomy(domain: str):
    from radar.review.pipeline import save_taxonomy
    if not _review_domain_ok(domain):
        return jsonify({"error": "未知领域"}), 400
    try:
        return jsonify({"taxonomy": save_taxonomy(domain, request.get_json(force=True) or {})})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    import os
    app.run(host=os.environ.get("RADAR_HOST", "127.0.0.1"), port=int(os.environ.get("RADAR_PORT", "5000")), debug=False)
