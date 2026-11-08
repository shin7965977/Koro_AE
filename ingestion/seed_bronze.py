"""Seed Bronze Raw Assets into physical Parquet files.

Generates realistic raw e-commerce logs conforming to KoRo's domain model:
1. Shopware 6 Orders API (`raw_shopware_orders.parquet`)
2. Shopware 6 Order Line Items API (`raw_shopware_order_items.parquet`)
3. ERP Catalog Master (`raw_koro_products.parquet`)
4. Warehouse Inspection Return Logs (`raw_return_logs.parquet`)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from ingestion.synthetic_medallion import build_koro_medallion_data


def seed_bronze_parquet_files(output_dir: Path | str = "data/bronze") -> dict[str, Path]:
    """Generate and serialize physical Bronze parquet assets."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Generate source datasets
    medallion = build_koro_medallion_data()

    # 1. Raw Catalog Master
    df_products = medallion["raw_koro_products"].copy()
    products_file = out_path / "raw_koro_products.parquet"
    df_products.to_parquet(products_file, index=False)

    # 2. Raw Orders (Ensure strict 1:1 grain per order_id)
    raw_orders = medallion["raw_shopware_orders"].copy()
    if "customer_id" not in raw_orders.columns:
        fct_ord = medallion["fct_orders"]
        cust_mapping = dict(zip(fct_ord["order_id"], fct_ord["customer_id"]))
        raw_orders["customer_id"] = raw_orders["order_id"].map(cust_mapping).fillna("CUST-0001")

    df_orders = (
        raw_orders.groupby("order_id", as_index=False)
        .agg({
            "order_date": "first",
            "customer_id": "first",
            "market_country": "first",
            "customer_segment": "first",
            "order_gross_eur": "sum",
            "discount_eur": "sum",
            "order_net_eur": "sum",
        })
    )
    orders_file = out_path / "raw_shopware_orders.parquet"
    df_orders.to_parquet(orders_file, index=False)

    # 3. Raw Order Line Items
    df_items = medallion["fct_order_items"].copy()
    if "order_item_id" not in df_items.columns and "item_id" in df_items.columns:
        df_items = df_items.rename(columns={"item_id": "order_item_id"})
    line_item_cols = [
        "order_item_id", "order_id", "order_date", "product_id",
        "quantity_sold", "unit_price_eur", "unit_cost_eur",
        "line_gross_eur", "line_discount_eur", "line_refund_eur",
        "line_net_eur", "cogs_eur"
    ]

    df_items = df_items[[c for c in line_item_cols if c in df_items.columns]]
    items_file = out_path / "raw_shopware_order_items.parquet"
    df_items.to_parquet(items_file, index=False)

    # 4. Raw Inspection Returns
    df_returns = medallion["raw_return_logs"].copy()
    if "defect_severity" not in df_returns.columns:
        df_returns["defect_severity"] = np.where(
            df_returns["return_reason"].str.contains("Vacuum", na=False),
            "High",
            "Medium"
        )
    returns_file = out_path / "raw_return_logs.parquet"
    df_returns.to_parquet(returns_file, index=False)

    print(f"✅ Generated Bronze Parquet Assets in {out_path}:")
    print(f"   - {products_file.name}: {len(df_products)} SKUs")
    print(f"   - {orders_file.name}: {len(df_orders)} orders (unique order_id)")
    print(f"   - {items_file.name}: {len(df_items)} line items")
    print(f"   - {returns_file.name}: {len(df_returns)} return inspection logs")

    return {
        "products": products_file,
        "orders": orders_file,
        "order_items": items_file,
        "returns": returns_file,
    }


if __name__ == "__main__":
    seed_bronze_parquet_files()
