"""End-to-End Analytics Engineering Pipeline Orchestrator.

Orchestrates the entire KoRo Medallion Lakehouse pipeline:
1. Ingestion: Generates Bronze Parquet assets in data/bronze/
2. Transformation: Compiles DuckDB models via dbt run (main_bronze -> main_silver)
3. Quality & Testing: Runs dbt test data contracts (18/18 integrity checks)
4. Verification: Queries data/koro_lakehouse.duckdb to validate table metrics
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def run_cmd(cmd: list[str], cwd: Path | str, stage_name: str) -> None:
    """Execute a shell command with real-time log output and timing."""
    print(f"\n================================================================================")
    print(f"🚀 [{stage_name}] Executing: {' '.join(cmd)}")
    print(f"   Working Dir: {cwd}")
    print(f"================================================================================")
    start_t = time.perf_counter()
    res = subprocess.run(cmd, cwd=str(cwd), text=True)
    dur = time.perf_counter() - start_t
    if res.returncode != 0:
        print(f"❌ [{stage_name}] FAILED with exit code {res.returncode} in {dur:.2f}s")
        sys.exit(res.returncode)
    print(f"✅ [{stage_name}] COMPLETED successfully in {dur:.2f}s\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="KoRo Lakehouse E2E Pipeline Orchestrator")
    parser.add_argument("--reseed", action="store_true", help="Force regenerate Bronze Parquet files")
    parser.add_argument("--test-only", action="store_true", help="Only run dbt test without dbt run")
    args = parser.parse_args()

    bronze_dir = _ROOT / "data" / "bronze"
    dbt_dir = _ROOT / "dbt_koro"
    duckdb_file = _ROOT / "data" / "koro_lakehouse.duckdb"

    pipeline_start = time.perf_counter()
    print("=" * 80)
    print("🌰 KoRo Analytics Engineering Lakehouse Pipeline Orchestrator")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Architecture: Medallion Lakehouse (Bronze -> Silver Kimball Star Schema)")
    print(f"⚙️  Engines: DuckDB v1.11.1 + dbt-core v1.12.6")
    print(f"💾 Storage: {duckdb_file}")
    print("=" * 80)

    # 1. Ingestion Phase: Bronze Parquet
    need_seed = args.reseed or not (bronze_dir / "raw_koro_products.parquet").exists()
    if need_seed:
        print("\n[Phase 1/4] Ingesting Raw E-Commerce Assets to Bronze Layer...")
        from ingestion.seed_bronze import seed_bronze_parquet_files
        seed_bronze_parquet_files(bronze_dir)
    else:
        print(f"\n[Phase 1/4] Bronze Parquet files verified at {bronze_dir} (skipping re-seed)")

    # 2. Transformation Phase: dbt run
    if not args.test_only:
        print("\n[Phase 2/4] Running dbt Transformations into DuckDB...")
        run_cmd(
            [
                sys.executable,
                "-m",
                "dbt.cli.main",
                "run",
                "--project-dir",
                str(dbt_dir),
                "--profiles-dir",
                str(dbt_dir),
            ],
            cwd=dbt_dir,
            stage_name="dbt Transformation (Bronze & Silver)",
        )
    else:
        print("\n[Phase 2/4] Skipping dbt run (--test-only passed)")

    # 3. Quality & Data Contracts Phase: dbt test
    print("\n[Phase 3/4] Running dbt Data Contract Tests & Schema Validations...")
    run_cmd(
        [
            sys.executable,
            "-m",
            "dbt.cli.main",
            "test",
            "--project-dir",
            str(dbt_dir),
            "--profiles-dir",
            str(dbt_dir),
        ],
        cwd=dbt_dir,
        stage_name="dbt Data Quality (Uniqueness, Not-Null, Referential Integrity)",
    )


    # 4. Warehouse Verification Phase: DuckDB Query Inspection
    print("\n[Phase 4/4] Verifying Lakehouse Warehouse State in DuckDB...")
    import duckdb
    con = duckdb.connect(str(duckdb_file), read_only=True)
    try:
        tables = con.execute(
            "SELECT table_schema, table_name, table_type FROM information_schema.tables WHERE table_schema IN ('main_bronze', 'main_silver') ORDER BY table_schema, table_name"
        ).df()
        orders_cnt = con.execute("SELECT COUNT(*) FROM main_silver.fct_orders").fetchone()[0]
        items_cnt = con.execute("SELECT COUNT(*) FROM main_silver.fct_order_items").fetchone()[0]
        returns_cnt = con.execute("SELECT COUNT(*) FROM main_silver.fct_returns").fetchone()[0]
        products_cnt = con.execute("SELECT COUNT(*) FROM main_silver.dim_products").fetchone()[0]
        customers_cnt = con.execute("SELECT COUNT(*) FROM main_silver.dim_customers").fetchone()[0]

        # Cashew hero metric check
        cashew_stats = con.execute("""
            SELECT 
                p.product_id,
                p.product_name,
                SUM(i.quantity_sold) AS sold_units,
                COALESCE(SUM(r.returned_units), 0) AS returned_units,
                ROUND(COALESCE(SUM(r.returned_units), 0) * 100.0 / NULLIF(SUM(i.quantity_sold), 0), 2) AS return_rate_pct
            FROM main_silver.dim_products p
            JOIN main_silver.fct_order_items i USING (product_id)
            LEFT JOIN main_silver.fct_returns r USING (product_id)
            WHERE p.product_id = 'KORO-NUT-001'
            GROUP BY p.product_id, p.product_name
        """).df()
    finally:
        con.close()

    total_dur = time.perf_counter() - pipeline_start
    print("\n" + "=" * 80)
    print("🎉 PIPELINE EXECUTION SUMMARY")
    print("=" * 80)
    print(f"⏱️  Total Duration: {total_dur:.2f}s")
    print(f"📦 Lakehouse Tables Built ({len(tables)} tables):")
    for _, row in tables.iterrows():
        print(f"   • {row['table_schema']}.{row['table_name']} ({row['table_type']})")
    print(f"\n📊 Silver Kimball Star Schema Record Counts:")
    print(f"   - fct_orders:       {orders_cnt:,} orders")
    print(f"   - fct_order_items:  {items_cnt:,} line items")
    print(f"   - fct_returns:      {returns_cnt:,} return logs")
    print(f"   - dim_products:     {products_cnt:,} SKUs")
    print(f"   - dim_customers:    {customers_cnt:,} customers")
    print(f"\n🔍 Hero Diagnostic Verification (1kg Organic Cashews Return Anomaly):")
    for _, row in cashew_stats.iterrows():
        print(f"   - SKU: {row['product_id']} ({row['product_name']})")
        print(f"   - Units Sold: {row['sold_units']:,} | Units Returned: {row['returned_units']:,} | Return Rate: {row['return_rate_pct']}%")
    print("=" * 80)
    print("✅ All systems go! Ready for live demonstration.\n")


if __name__ == "__main__":
    main()
