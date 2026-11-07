"""Automated AI Spec Guidance & SQL Traceability Benchmark Evaluator."""

from __future__ import annotations

import json
import os
from typing import Any

from koro_adapter import KoroAdapter


def run_benchmark_evaluation(write_report: bool = True) -> dict[str, Any]:
    """Run all 12 benchmark questions through KoroAdapter's 2-round Socratic engine and compiler."""
    eval_dir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(eval_dir, "benchmark_questions.json"), encoding="utf-8") as f:
        questions = json.load(f)
    with open(os.path.join(eval_dir, "ground_truth.json"), encoding="utf-8") as f:
        ground_truth = json.load(f)

    adapter = KoroAdapter()
    data = adapter.load_domain_data()

    results = []
    passed_count = 0
    compliant_count = 0

    for item in questions:
        qid = item["id"]
        qtext = item["question"]
        gt = ground_truth[qid]

        # Round 1: Initial question
        t1 = adapter.handle_spec_inquiry_turn(
            user_query=qtext,
            current_round=0,
            session_context={},
            is_en=True,
        )
        # Round 2: Confirm standard definitions
        t2 = adapter.handle_spec_inquiry_turn(
            user_query="Yes, confirm governed definitions and last 90 days.",
            current_round=t1["next_round"],
            session_context={"scenario_key": t1["scenario_key"]},
            is_en=True,
        )
        spec = t2["spec_contract"]
        insight = adapter.compile_spec_to_insight(
            spec_contract=spec, data_dict=data, is_en=True
        )

        is_compliant = (
            spec is not None
            and spec.governance_checks.get("contains_pii") is False
            and spec.governance_checks.get("dbt_tested") is True
            and insight is not None
            and not insight.df_snippet.empty
        )
        if is_compliant:
            compliant_count += 1

        is_accurate = (
            is_compliant
            and spec.scenario_key == gt["expected_scenario"]
            and spec.spec_id == gt["expected_spec_id"]
            and spec.target_mart == gt["expected_target_mart"]
            and gt["expected_takeaway_substring"] in insight.executive_takeaway
        )
        if is_accurate:
            passed_count += 1

        results.append(
            {
                "id": qid,
                "role": item["stakeholder_role"],
                "question": qtext,
                "spec_id": spec.spec_id if spec else "NONE",
                "target_mart": spec.target_mart if spec else "NONE",
                "compliant": is_compliant,
                "passed": is_accurate,
            }
        )

    total = len(questions)
    summary = {
        "total_questions": total,
        "passed_questions": passed_count,
        "accuracy_pct": round(passed_count * 100.0 / max(1, total), 2),
        "contract_compliance_pct": round(compliant_count * 100.0 / max(1, total), 2),
        "results": results,
    }

    if write_report:
        lines = [
            "# 📊 KoRo AI Semantic Copilot — Benchmark Evaluation Report",
            "",
            f"- **Total Benchmark Questions**: `{total}`",
            f"- **2-Round Spec Lock & Ground-Truth Accuracy**: `{summary['accuracy_pct']}%` (`{passed_count}/{total}`)",
            f"- **Data Contract & GDPR Compliance Rate**: `{summary['contract_compliance_pct']}%` (`{compliant_count}/{total}`)",
            "",
            "| ID | Stakeholder Role | Business Question | Locked Spec ID | Target Mart | GDPR & FinOps | Status |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for r in results:
            status_badge = "✅ PASS" if r["passed"] else "❌ FAIL"
            comp_badge = "✅ Verified" if r["compliant"] else "⚠️ Unverified"
            lines.append(
                f"| `{r['id']}` | {r['role']} | {r['question']} | `{r['spec_id']}` | `{r['target_mart']}` | {comp_badge} | {status_badge} |"
            )
        report_path = os.path.join(eval_dir, "evaluation_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    return summary


if __name__ == "__main__":
    res = run_benchmark_evaluation(write_report=True)
    print(f"Benchmark Accuracy: {res['accuracy_pct']}% ({res['passed_questions']}/{res['total_questions']})")
