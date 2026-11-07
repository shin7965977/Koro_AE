# 05: End-to-end AI benchmark evaluation suite and CI workflow

**What to build:**
Build an automated Benchmark Evaluation suite (`evaluation/`) with 12 realistic e-commerce business questions and ground-truth specs/metrics, plus a GitHub Actions CI workflow (`.github/workflows/ci.yml`) and documentation (`docs/`) to validate 100% contract compliance, SQL executability, and metric accuracy.

**Blocked by:** 03

**Status:** done

- [x] Create `evaluation/benchmark_questions.json` (12 questions) and `evaluation/ground_truth.json`.
- [x] Implement `evaluation/evaluation.py` to run all 12 benchmark questions through the spec engine and compiler, outputting `evaluation/evaluation_report.md`.
- [x] Create `.github/workflows/ci.yml` and complete architectural documentation in `docs/`.
- [x] Verify 100% pass rate across all 12 benchmark questions via regression tests.
