from __future__ import annotations

import argparse
import json
from pathlib import Path

from radar.evidence.evidence_quality import review_claim_evidence
from radar.core.radar_core import BASE_DIR, db, tokens, weekly_report

OUT = BASE_DIR / "outputs" / "evidence_qa"


def review_top10(apply: bool = False) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    idea_ids = [x["id"] for x in weekly_report()["top10"]]
    if not idea_ids:
        return {"ideas": 0, "links": 0, "flags": 0}
    placeholders = ",".join("?" for _ in idea_ids)
    query = f"""SELECT l.id link_id,i.id idea_id,i.idea_name,c.claim_type,c.claim_text,c.status claim_status,
                       l.support_relation,l.evidence_status,l.source_quality,l.rationale,l.verifier,
                       e.field_name,e.verbatim_quote,e.locator_json,s.radar,s.title source_title,s.url,
                       s.source_type,s.validation_status,s.last_verified_at
                FROM claim_evidence_links l
                JOIN idea_claims c ON c.id=l.claim_id JOIN ideas i ON i.id=c.idea_id
                LEFT JOIN evidence_extractions e ON e.id=l.extraction_id
                LEFT JOIN source_items s ON s.id=e.source_item_id
                WHERE i.id IN ({placeholders}) ORDER BY i.total_score DESC,i.id,c.id,l.id"""
    with db() as conn:
        rows = [dict(x) for x in conn.execute(query, idea_ids).fetchall()]
    reviewed = []
    applied = 0
    for row in rows:
        flags = []
        critical = []
        quote = row.get("verbatim_quote") or ""
        claim = row.get("claim_text") or ""
        overlap = len(tokens(quote) & tokens(claim))
        if row.get("validation_status") not in {"verified_source", "internal_record"}:
            critical.append("source_not_verified")
        if row.get("source_quality") == "ai_generated":
            critical.append("ai_generated_cannot_verify")
        if not quote or len(quote) < 30:
            critical.append("missing_verbatim_evidence_span")
        if row.get("evidence_status") == "verified" and row.get("support_relation") != "supports":
            critical.append("verified_without_supports_relation")
        if row.get("claim_type") == "why_now" and row.get("evidence_status") == "verified" and row.get("source_type") not in {"official_release", "official_documentation", "official_product_page"}:
            critical.append("why_now_not_official_product_source")
        if row.get("claim_type") == "core_insight" and row.get("evidence_status") == "verified" and row.get("source_type") not in {"professional_sop", "expert_interview", "workflow_record"}:
            critical.append("core_value_not_direct_workflow_source")
        if row.get("claim_type") == "evaluation_gap" and row.get("evidence_status") == "verified":
            flags.append("negative_claim_requires_coverage_matrix_review")
        if overlap == 0:
            flags.append("low_lexical_overlap_manual_semantic_review")
        recommendation = "downgrade_to_partial" if critical and row.get("evidence_status") == "verified" else "manual_review" if flags or critical else "keep"
        item = {**row, "critical_flags": critical, "review_flags": flags, "recommendation": recommendation}
        reviewed.append(item)
        if apply and recommendation == "downgrade_to_partial":
            review_claim_evidence(
                row["link_id"], "partially_supports", "partial", "EvidenceQA-V1",
                "Conservative downgrade: " + ", ".join(critical),
            )
            applied += 1
    report = {
        "generated_at": "2026-09-15",
        "idea_ids": idea_ids,
        "links_reviewed": len(reviewed),
        "verified_links": sum(1 for x in reviewed if x["evidence_status"] == "verified"),
        "critical_flags": sum(1 for x in reviewed if x["critical_flags"]),
        "manual_review_flags": sum(1 for x in reviewed if x["review_flags"]),
        "downgrades_applied": applied,
        "items": reviewed,
    }
    (OUT / "top10_claim_evidence_review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {k: v for k, v in report.items() if k != "items"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-conservative", action="store_true")
    args = parser.parse_args()
    print(json.dumps(review_top10(args.apply_conservative), ensure_ascii=False, indent=2))
