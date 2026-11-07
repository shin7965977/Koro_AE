# 04: Multi-scenario presets, dual-mode LLM/fallback router, and New Inquiry state isolation

**What to build:**
Expand the Socratic Spec Engine with two additional high-value e-commerce scenarios ("💰 Category Net Margin & Discount Impact" and "📦 Inventory Availability & Stockout Risk"), dual-mode routing (Live Gemini API when configured + deterministic intent fallback when offline), and complete state isolation when clicking `🔄 New Inquiry`.

**Blocked by:** 03

**Status:** done

- [x] Add 2-round Socratic templates, spec contracts, DuckDB SQL compilers, and Plotly charts for "Category Net Margin Ranking" and "Inventory Availability & Stockout Risk".
- [x] Implement dual-mode routing in `ai/spec_guide.py` supporting live Gemini API structured extraction with automatic fallback to local keyword-intent classification.
- [x] Verify switching across all 3 scenarios and resetting state via integration tests.
