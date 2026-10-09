from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from radar.core.radar_core import db, now_iso

RELATIONS = {"supports", "partially_supports", "contradicts", "irrelevant"}
STATUSES = {"verified", "partial", "hypothesis", "unsupported"}
QUALITY = {"primary", "secondary", "internal", "ai_generated"}


def canonical_url(url: str) -> str:
    if not url:
        return ""
    p = urlsplit(url)
    host = p.hostname.lower() if p.hostname else ""
    path = p.path.rstrip("/") or "/"
    return urlunsplit((p.scheme.lower(), host, path, "", ""))


def claim_specs(idea: dict[str, Any]) -> list[tuple[str, str, str]]:
    return [
        ("core_insight", "core_insight", f"{idea['idea_name']} 对应真实任务，值得作为独立 Benchmark 方向验证。"),
        ("why_now", "why_now", "相关模型或产品能力正在进入应用阶段，当前应验证其真实表现与边界。"),
        ("evaluation_gap", "evaluation_gap", idea["evaluation_gap"]),
        ("model_failure", "model_failure", "当前模型在目标任务上存在可复现、可定位的失败模式。"),
    ]


def extraction_specs(source: dict[str, Any]) -> list[tuple[str, str]]:
    raw = source.get("raw_data") or {}
    content = source.get("content") or ""
    locator = source.get("locator") or {}
    quote = raw.get("raw_excerpt") or raw.get("quote") or content
    if not quote:
        return []
    radar = source["radar"]
    if radar == "benchmark":
        fields = [("benchmark_scope", quote)]
        for key in ["task_definition", "dataset", "evaluation_protocol", "coverage_matrix", "leaderboard_results"]:
            if raw.get(key):
                fields.append((key, str(raw[key])))
        return fields
    if radar == "workflow":
        fields = [("workflow_task", quote)]
        for key in ["hardest_step", "hard_step", "common_human_mistakes", "required_expertise"]:
            if raw.get(key):
                fields.append((key, str(raw[key])))
        return fields
    if radar == "product_agent":
        return [("official_capability", quote)]
    if radar == "model_failure":
        return [("failure_observation", quote)]
    return [("fact", quote)]


def derive_relation(claim_type: str, source: dict[str, Any], extraction_field: str) -> tuple[str, str, str]:
    radar = source["radar"]
    quality = source.get("source_quality") or "ai_generated"
    validation = source.get("validation_status") or "unverified"
    source_type = source.get("source_type") or ""
    if source.get("evidence_role") != "raw_source" or quality == "ai_generated":
        return "irrelevant", "unsupported", "该记录不是有效Raw Source，不能验证Claim。"
    if validation in {"verification_failed", "metadata_mismatch", "invalid"}:
        return "irrelevant", "unsupported", f"Raw Source验证失败：{validation}。"
    if validation not in {"verified_source", "internal_record"}:
        return "partially_supports", "partial", "Raw Source尚未完成URL/记录真实性验证。"
    if claim_type == "model_failure":
        if radar != "model_failure":
            return "irrelevant", "unsupported", "非Model Failure来源不能证明模型失败。"
        cases = source.get("failure_cases") or []
        if cases:
            return "supports", "verified", "存在可追溯的Eval Run / Case级失败记录。"
        return "partially_supports", "hypothesis", "只有聚合描述，没有Case级Prompt/Reference/Response/Judge。"
    if claim_type == "evaluation_gap":
        if radar != "benchmark":
            return "irrelevant", "unsupported", "非Benchmark来源不能直接验证覆盖缺口。"
        raw = source.get("raw_data") or {}
        protocol_checked = bool(raw.get("task_definition") or raw.get("evaluation_protocol") or raw.get("dataset") or raw.get("coverage_matrix"))
        if protocol_checked:
            return "supports", "verified", "已检查Task Definition/Dataset/Evaluation Protocol。"
        return "partially_supports", "partial", "来源相关，但未完成Task Definition/Dataset/Protocol覆盖核验。"
    if claim_type == "why_now":
        if radar == "product_agent" and quality == "primary" and source_type in {"official_release", "official_documentation", "official_product_page"}:
            return "supports", "verified", "官方产品/发布材料可直接证明能力已进入产品。"
        if radar in {"benchmark", "workflow"}:
            return "partially_supports", "partial", "可提供背景，但不能单独证明Why Now。"
        return "irrelevant", "unsupported", "与Why Now缺少直接关系。"
    if claim_type == "core_insight":
        if radar == "workflow":
            direct_workflow = source_type in {"professional_sop", "expert_interview", "workflow_record"}
            if direct_workflow and quality in {"primary", "internal"}:
                return "supports", "verified", "原始SOP/访谈/工作流记录可直接证明真实任务价值。"
            return "partially_supports", "partial", "研究论文或间接材料只能部分支持工作流Claim，需补SOP/访谈原始记录。"
        if radar in {"benchmark", "product_agent", "model_failure"}:
            return "partially_supports", "partial", "支持Idea的一部分，但不能单独证明整体价值。"
    return "irrelevant", "unsupported", "未建立直接支持关系。"


def sync_idea_quality(idea_id: int) -> dict[str, Any]:
    from radar.core.radar_core import get_idea

    idea = get_idea(idea_id)
    if not idea:
        raise KeyError(idea_id)
    timestamp = now_iso()
    with db() as conn:
        for key, claim_type, text in claim_specs(idea):
            conn.execute(
                """INSERT INTO idea_claims(idea_id,claim_key,claim_type,claim_text,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?) ON CONFLICT(idea_id,claim_key) DO UPDATE SET
                claim_text=excluded.claim_text,claim_type=excluded.claim_type,updated_at=excluded.updated_at""",
                (idea_id, key, claim_type, text, "hypothesis", timestamp, timestamp),
            )
        claims = {x["claim_type"]: x for x in conn.execute("SELECT * FROM idea_claims WHERE idea_id=?", (idea_id,)).fetchall()}
        conn.execute(
            """DELETE FROM claim_evidence_links WHERE claim_id IN (SELECT id FROM idea_claims WHERE idea_id=?)
               AND (verifier IS NULL OR verifier='rules-v1')""", (idea_id,)
        )
        for source in idea.get("evidence", []):
            locator = source.get("locator") or {}
            for field_name, quote in extraction_specs(source):
                quote = str(quote).strip()
                if not quote:
                    continue
                conn.execute(
                    """INSERT OR IGNORE INTO evidence_extractions
                    (source_item_id,field_name,extracted_value,verbatim_quote,locator_json,extractor_version,confidence,created_at)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (source["source_item_id"], field_name, quote, quote, json.dumps(locator, ensure_ascii=False), source["extractor_version"], source["confidence"], timestamp),
                )
                extraction = conn.execute(
                    "SELECT * FROM evidence_extractions WHERE source_item_id=? AND field_name=? AND verbatim_quote=?",
                    (source["source_item_id"], field_name, quote),
                ).fetchone()
                for claim_type, claim in claims.items():
                    human_review = conn.execute(
                        """SELECT id FROM claim_evidence_links WHERE claim_id=? AND extraction_id=?
                           AND verifier IS NOT NULL AND verifier!='rules-v1' LIMIT 1""",
                        (claim["id"], extraction["id"]),
                    ).fetchone()
                    if human_review:
                        continue
                    relation, status, rationale = derive_relation(claim_type, source, field_name)
                    conn.execute(
                        """INSERT OR REPLACE INTO claim_evidence_links
                        (claim_id,extraction_id,failure_case_id,support_relation,evidence_status,source_quality,rationale,verified_at,verifier)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                        (claim["id"], extraction["id"], None, relation, status, source.get("source_quality") or "ai_generated", rationale, timestamp if status == "verified" else None, "rules-v1"),
                    )
        for claim_type, claim in claims.items():
            links = conn.execute("SELECT evidence_status,support_relation FROM claim_evidence_links WHERE claim_id=?", (claim["id"],)).fetchall()
            statuses = {x["evidence_status"] for x in links if x["support_relation"] != "irrelevant"}
            relations = {x["support_relation"] for x in links}
            if "contradicts" in relations:
                status = "unsupported"
            elif "verified" in statuses:
                status = "verified"
            elif "partial" in statuses:
                status = "partial"
            elif "hypothesis" in statuses:
                status = "hypothesis"
            else:
                status = "unsupported"
            conn.execute("UPDATE idea_claims SET status=?,updated_at=? WHERE id=?", (status, timestamp, claim["id"]))
        radar_rows = conn.execute(
            """SELECT s.radar,l.evidence_status,l.support_relation
               FROM claim_evidence_links l
               JOIN evidence_extractions e ON e.id=l.extraction_id
               JOIN source_items s ON s.id=e.source_item_id
               JOIN idea_claims c ON c.id=l.claim_id
               WHERE c.idea_id=? AND l.support_relation!='irrelevant'""",
            (idea_id,),
        ).fetchall()
        radar_status = {}
        for radar in ["benchmark", "workflow", "product_agent", "model_failure"]:
            statuses = {x["evidence_status"] for x in radar_rows if x["radar"] == radar}
            radar_status[radar] = "verified" if "verified" in statuses else ("partial" if "partial" in statuses else ("hypothesis" if "hypothesis" in statuses else "unsupported"))
        hits = sum(1 for status in radar_status.values() if status == "verified")
        conn.execute("UPDATE ideas SET radar_hits=? WHERE id=?", (hits, idea_id))
    summary = claim_quality_summary(idea_id)
    summary["radar_status"] = radar_status
    summary["verified_radar_hits"] = hits
    with db() as conn:
        idea_row = conn.execute("SELECT * FROM ideas WHERE id=?", (idea_id,)).fetchone()
        if idea_row and summary["evidence_confidence"] == "Low" and idea_row["status"] in {"mini_eval", "approved"}:
            conn.execute("UPDATE ideas SET status=?,version=version+1,updated_at=? WHERE id=?", ("watch", now_iso(), idea_id))
            snapshot = conn.execute("SELECT * FROM ideas WHERE id=?", (idea_id,)).fetchone()
            conn.execute(
                "INSERT INTO idea_history(idea_id,action,snapshot_json,created_at) VALUES(?,?,?,?)",
                (idea_id, "evidence_confidence_downgrade", json.dumps(dict(snapshot), ensure_ascii=False), now_iso()),
            )
            summary["idea_status_changed_to"] = "watch"
    return summary


def claim_quality_summary(idea_id: int) -> dict[str, Any]:
    with db() as conn:
        claims = []
        for claim in conn.execute("SELECT * FROM idea_claims WHERE idea_id=? ORDER BY id", (idea_id,)).fetchall():
            item = dict(claim)
            item["evidence"] = [dict(x) for x in conn.execute(
                """SELECT l.*,e.field_name,e.verbatim_quote,e.locator_json,e.source_item_id,s.title,s.url,
                          s.radar,s.source_type,s.source_quality source_quality_actual,s.last_verified_at,s.source_version,s.validation_status
                   FROM claim_evidence_links l
                   LEFT JOIN evidence_extractions e ON e.id=l.extraction_id
                   LEFT JOIN source_items s ON s.id=e.source_item_id
                   WHERE l.claim_id=? ORDER BY l.evidence_status,l.id""",
                (claim["id"],),
            ).fetchall()]
            claims.append(item)
        counts = defaultdict(int)
        quality_counts = defaultdict(int)
        conflicts = 0
        for claim in claims:
            counts[claim["status"]] += 1
            for ev in claim["evidence"]:
                if ev["evidence_status"] == "verified":
                    quality_counts[ev["source_quality"]] += 1
                if ev["support_relation"] == "contradicts":
                    conflicts += 1
        verified = counts["verified"]
        partial = counts["partial"]
        total = max(1, len(claims))
        if conflicts or verified / total < 0.25:
            confidence = "Low"
        elif verified / total >= 0.75 and partial == 0:
            confidence = "High"
        else:
            confidence = "Medium"
        missing = [x["claim_type"] for x in claims if x["status"] in {"partial", "hypothesis", "unsupported"}]
        # 尚未同步 claim 的 Idea（新生成、还没跑 sync_idea_quality）此前 missing 为空，
        # needs_verification=False，会从周报的"待验证"区静默消失。
        if not claims:
            missing = ["core_insight", "why_now", "evaluation_gap", "model_failure"]
        from radar.core.radar_core import coverage_matrix
        matrix = coverage_matrix(idea_id)
        verified_matrix = [x for x in matrix if x["verification_status"] == "verified" and x.get("source_validation") in {"verified_source", "internal_record"}]
        matrix_unknown = [x for x in matrix if x["target_coverage"] == "unknown" or x["verification_status"] != "verified"]
        coverage_summary = {
            "benchmarks_reviewed": len(matrix),
            "verified_entries": len(verified_matrix),
            "covered": sum(1 for x in verified_matrix if x["target_coverage"] == "covered"),
            "partial": sum(1 for x in verified_matrix if x["target_coverage"] == "partial"),
            "not_covered": sum(1 for x in verified_matrix if x["target_coverage"] == "not_covered"),
            "unknown_or_pending": len(matrix_unknown),
            "status": "verified" if len(matrix) >= 3 and not matrix_unknown else "partial" if matrix else "missing",
        }
        radar_status = {}
        all_evidence = [ev for claim in claims for ev in claim["evidence"] if ev["support_relation"] != "irrelevant"]
        for radar in ["benchmark", "workflow", "product_agent", "model_failure"]:
            statuses = {ev["evidence_status"] for ev in all_evidence if ev.get("radar") == radar}
            radar_status[radar] = "verified" if "verified" in statuses else ("partial" if "partial" in statuses else ("hypothesis" if "hypothesis" in statuses else "unsupported"))
        return {
            "claims": claims,
            "claim_counts": dict(counts),
            "quality_counts": dict(quality_counts),
            "conflicts": conflicts,
            "evidence_confidence": confidence,
            "needs_verification": bool(missing),
            "missing_evidence": missing,
            "coverage_matrix_summary": coverage_summary,
            "recommended_validation": [
                "Run Mini Eval: 30 Cases / 3 representative models" if "model_failure" in missing else "",
                "Complete Benchmark Coverage Matrix: Task / Dataset / I/O / Protocol / Metric / target capability" if "evaluation_gap" in missing else "",
                "Collect raw SOP / Expert Interview Record" if "core_insight" in missing else "",
                "Verify official Product Release / Documentation" if "why_now" in missing else "",
            ],
            "radar_status": radar_status,
            "verified_radar_hits": sum(1 for status in radar_status.values() if status == "verified"),
        }


def review_claim_evidence(
    link_id: int,
    support_relation: str,
    evidence_status: str,
    verifier: str,
    rationale: str,
) -> dict[str, Any]:
    if support_relation not in RELATIONS:
        raise ValueError(f"invalid support_relation: {support_relation}")
    if evidence_status not in STATUSES:
        raise ValueError(f"invalid evidence_status: {evidence_status}")
    if not verifier or not rationale:
        raise ValueError("verifier and rationale are required")
    with db() as conn:
        row = conn.execute(
            """SELECT l.id,c.idea_id FROM claim_evidence_links l
               JOIN idea_claims c ON c.id=l.claim_id WHERE l.id=?""", (link_id,)
        ).fetchone()
        if not row:
            raise KeyError(link_id)
        conn.execute(
            """UPDATE claim_evidence_links SET support_relation=?,evidence_status=?,rationale=?,verified_at=?,verifier=? WHERE id=?""",
            (support_relation, evidence_status, rationale, now_iso(), verifier, link_id),
        )
        idea_id = row["idea_id"]
        claim_ids = [x["id"] for x in conn.execute("SELECT id FROM idea_claims WHERE idea_id=?", (idea_id,)).fetchall()]
        for claim_id in claim_ids:
            links = conn.execute("SELECT support_relation,evidence_status FROM claim_evidence_links WHERE claim_id=?", (claim_id,)).fetchall()
            relations = {x["support_relation"] for x in links}
            statuses = {x["evidence_status"] for x in links if x["support_relation"] != "irrelevant"}
            status = "unsupported" if "contradicts" in relations else ("verified" if "verified" in statuses else ("partial" if "partial" in statuses else ("hypothesis" if "hypothesis" in statuses else "unsupported")))
            conn.execute("UPDATE idea_claims SET status=?,updated_at=? WHERE id=?", (status, now_iso(), claim_id))
        radar_rows = conn.execute(
            """SELECT s.radar,l.evidence_status FROM claim_evidence_links l
               JOIN evidence_extractions e ON e.id=l.extraction_id
               JOIN source_items s ON s.id=e.source_item_id
               JOIN idea_claims c ON c.id=l.claim_id
               WHERE c.idea_id=? AND l.support_relation!='irrelevant'""", (idea_id,)
        ).fetchall()
        hits = sum(1 for radar in ["benchmark", "workflow", "product_agent", "model_failure"] if any(x["radar"] == radar and x["evidence_status"] == "verified" for x in radar_rows))
        conn.execute("UPDATE ideas SET radar_hits=? WHERE id=?", (hits, idea_id))
    return claim_quality_summary(idea_id)


def sync_all_idea_quality() -> dict[str, int]:
    with db() as conn:
        ids = [x["id"] for x in conn.execute("SELECT id FROM ideas").fetchall()]
    for idea_id in ids:
        sync_idea_quality(idea_id)
    return {"ideas_synced": len(ids)}
