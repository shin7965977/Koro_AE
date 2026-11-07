"""Regression tests for Ticket #05: 12-question AI Benchmark Evaluation & CI compliance."""

from __future__ import annotations

import os

from evaluation.evaluation import run_benchmark_evaluation


def test_benchmark_evaluation_achieves_100_percent_accuracy() -> None:
    """Verify all 12 benchmark business questions pass spec lock, SQL parity, and ground-truth accuracy."""
    summary = run_benchmark_evaluation(write_report=True)
    assert summary["total_questions"] == 12
    assert summary["passed_questions"] == 12
    assert summary["accuracy_pct"] == 100.0
    assert summary["contract_compliance_pct"] == 100.0

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    report_path = os.path.join(root, "evaluation", "evaluation_report.md")
    assert os.path.exists(report_path)
