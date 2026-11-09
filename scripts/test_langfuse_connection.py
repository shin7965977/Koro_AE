"""
Verification script for Langfuse cloud connection and tracing end-to-end.
"""

from ai.telemetry import LakehouseTelemetry


def main():
    print("🚀 Initializing LakehouseTelemetry...")
    t = LakehouseTelemetry.get_instance()
    print(f"Is active: {t.is_active}")
    assert t.is_active, "Langfuse client should be active with valid credentials."

    # 1. Create a test trace
    trace = t.create_trace(
        name="koro-lakehouse-init-verification",
        user_id="lead_analytics_engineer",
        session_id="session_init_test",
        tags=["verification", "smoke_test"],
        input_data={"goal": "Verify Langfuse cloud connectivity and grounding check"},
    )
    print("Created trace:", trace.id if trace else "None")

    # 2. Log a child span
    span = t.log_span(
        trace=trace,
        name="socratic_memo_generation",
        input_data={"chat_turns": 3, "intent": "Almond Cashew DE August"},
        output_data={"memo": "Structured Requirement Memo locked"},
        metadata={"step": "memo_synthesis"},
    )
    print("Created span:", span.id if span else "None")

    # 3. Log a generation
    gen = t.log_generation(
        trace=trace,
        name="dynamic_dbt_sql_compiler",
        model="gemini-3.8-flash",
        input_prompt="Synthesize DuckDB mart with Nuts & Butters filtering",
        output_completion="SELECT * FROM mart_product_price_return_performance_de WHERE p.category_name = 'Nuts & Butters'",
        usage={"input_tokens": 150, "output_tokens": 80, "total_tokens": 230},
    )
    print("Created generation:", gen.id if gen else "None")

    # 4. Evaluate grounding
    score = t.evaluate_grounding(
        trace=trace,
        expected_filters=["Nuts & Butters", "2026-08"],
        generated_sql="SELECT * FROM main_gold.mart WHERE category_name = 'Nuts & Butters' AND month = '2026-08'",
    )
    print(f"Evaluated grounding score: {score}")

    # 5. Flush to server
    t.flush()
    print("✅ All traces, spans, and scores successfully flushed to Langfuse Cloud!")
    print(f"👉 View your trace in Langfuse UI: https://cloud.langfuse.com/project/trace/{trace.id if trace else ''}")


if __name__ == "__main__":
    main()
