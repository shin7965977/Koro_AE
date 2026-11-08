"""Deterministic Medallion Data Engine conforming to Ralph Kimball Dimensional Modeling.

Bronze Layer:
  - raw_shopware_orders: Ingested order headers
  - raw_koro_products: Ingested raw catalog
  - raw_return_logs: Ingested return claims and inspection records

Silver Layer (Strict Star Schema):
  - dim_products: Conformed product dimension (SKU grain)
  - dim_categories: Conformed category hierarchy dimension
  - dim_customers: Customer market & segment dimension
  - fct_orders: Order grain transaction fact
  - fct_order_items: Line-item grain transaction fact (lowest grain)
  - fct_returns: Event grain return & defect inspection fact

Note: In accordance with Kimball methodology, Gold Mart aggregations
(mart_product_performance, mart_category_daily) are dynamically compiled
downstream from Silver facts & dimensions rather than stored as hardcoded static tables.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd


def build_koro_medallion_data(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, pd.DataFrame]:
    """Generate deterministic Bronze raw tables and Silver Kimball Star Schema DataFrames."""
    rng = np.random.default_rng(42)

    # =========================================================================
    # 1. BRONZE LAYER: Raw Catalog (`raw_koro_products`)
    # =========================================================================
    catalog_rows = [
        # Nuts & Butters
        ("KORO-NUT-001", "Organic Cashews Bulk", "Nuts & Butters", "1kg", 15.50, 9.80, True, 420),
        ("KORO-NUT-002", "Roasted Pistachios in Shell", "Nuts & Butters", "1kg", 22.00, 14.10, True, 310),
        ("KORO-NUT-003", "Creamy Peanut Butter", "Nuts & Butters", "500g", 6.50, 3.80, True, 890),
        ("KORO-NUT-004", "Crunchy Almond Butter", "Nuts & Butters", "500g", 11.00, 6.90, True, 540),
        ("KORO-NUT-005", "Whole Macadamia Nuts", "Nuts & Butters", "1kg", 26.50, 18.20, False, 0),
        # Dried Fruits
        ("KORO-FRU-001", "Brooks Mango Strips", "Dried Fruits", "1kg", 16.00, 9.20, True, 760),
        ("KORO-FRU-002", "Medjool Dates Premium", "Dried Fruits", "1kg", 14.50, 8.40, True, 680),
        ("KORO-FRU-003", "Freeze-Dried Strawberries", "Dried Fruits", "250g", 12.50, 7.10, True, 190),
        # Superfoods & Seeds
        ("KORO-SUP-001", "Organic Chia Seeds", "Superfoods & Seeds", "1kg", 9.50, 5.10, True, 920),
        ("KORO-SUP-002", "Organic Hemp Seeds Peeled", "Superfoods & Seeds", "500g", 8.90, 4.90, True, 410),
        # Snacks & Bars
        ("KORO-SNK-001", "Vegan Protein Bar Hazelnut", "Snacks & Bars", "250g", 13.90, 7.80, True, 630),
        ("KORO-SNK-002", "Dark Chocolate Pretzel Bites", "Snacks & Bars", "500g", 10.50, 5.90, True, 510),
    ]
    raw_koro_products = pd.DataFrame(
        catalog_rows,
        columns=[
            "product_id",
            "product_name",
            "category_name",
            "packaging_size",
            "unit_price_eur",
            "unit_cost_eur",
            "is_available",
            "stock_on_hand",
        ],
    )

    # =========================================================================
    # 2. SILVER DIMENSIONS: Conformed Dimensions (`dim_products`, `dim_categories`, `dim_customers`)
    # =========================================================================
    category_mapping = {
        "Nuts & Butters": {"category_id": "CAT-NUT", "department": "Food & Pantry"},
        "Dried Fruits": {"category_id": "CAT-FRU", "department": "Food & Pantry"},
        "Superfoods & Seeds": {"category_id": "CAT-SUP", "department": "Health & Nutrition"},
        "Snacks & Bars": {"category_id": "CAT-SNK", "department": "Snacking"},
    }

    dim_categories = pd.DataFrame(
        [
            {
                "category_id": v["category_id"],
                "category_name": k,
                "department": v["department"],
            }
            for k, v in category_mapping.items()
        ]
    )

    dim_products = raw_koro_products.copy()
    dim_products["category_id"] = dim_products["category_name"].map(
        lambda c: category_mapping[c]["category_id"]
    )
    dim_products = dim_products[
        [
            "product_id",
            "product_name",
            "category_id",
            "category_name",
            "packaging_size",
            "unit_price_eur",
            "unit_cost_eur",
            "is_available",
            "stock_on_hand",
        ]
    ]

    markets = ["DE", "AT", "FR", "NL"]
    segments = ["D2C Repeat", "D2C First-Time", "B2B Office"]
    customers_data = []
    c_idx = 1
    for m in markets:
        for s in segments:
            customers_data.append(
                {
                    "customer_id": f"CUST-{c_idx:03d}",
                    "market_country": m,
                    "customer_segment": s,
                }
            )
            c_idx += 1
    dim_customers = pd.DataFrame(customers_data)

    # =========================================================================
    # 3. DATE BOUNDARY & SIMULATION TARGETS
    # =========================================================================
    base_start = date(2026, 8, 3)
    base_end = date(2026, 10, 31)
    eff_start = max(base_start, start_date) if start_date else base_start
    eff_end = min(base_end, end_date) if end_date else base_end
    if eff_start > eff_end:
        eff_start, eff_end = base_start, base_end

    total_days = (base_end - base_start).days + 1
    all_dates = [base_start + timedelta(days=i) for i in range(total_days)]

    sku_targets = {
        "KORO-NUT-001": {"sold": 5000, "ret": 260, "disc_rate": 0.06},  # Outlier 5.20% return rate
        "KORO-NUT-002": {"sold": 3200, "ret": 112, "disc_rate": 0.05},
        "KORO-NUT-003": {"sold": 6400, "ret": 96, "disc_rate": 0.04},
        "KORO-NUT-004": {"sold": 4100, "ret": 74, "disc_rate": 0.05},
        "KORO-NUT-005": {"sold": 1800, "ret": 63, "disc_rate": 0.04},
        "KORO-FRU-001": {"sold": 5500, "ret": 99, "disc_rate": 0.07},
        "KORO-FRU-002": {"sold": 4800, "ret": 82, "disc_rate": 0.06},
        "KORO-FRU-003": {"sold": 2900, "ret": 35, "disc_rate": 0.05},
        "KORO-SUP-001": {"sold": 6100, "ret": 61, "disc_rate": 0.04},
        "KORO-SUP-002": {"sold": 3400, "ret": 41, "disc_rate": 0.04},
        "KORO-SNK-001": {"sold": 4600, "ret": 69, "disc_rate": 0.08},
        "KORO-SNK-002": {"sold": 3800, "ret": 57, "disc_rate": 0.07},
    }

    # =========================================================================
    # 4. SILVER FACTS: `fct_order_items`, `fct_orders`, `fct_returns`
    # =========================================================================
    order_items_rows = []
    return_rows = []
    item_seq = 100001
    ret_seq = 50001
    ord_seq = 10001

    # Deterministic generation across all dates
    for d_idx, cur_date in enumerate(all_dates):
        daily_order_count = 110  # ~110 orders per day across markets
        orders_for_day = [f"SW6-{ord_seq + i}" for i in range(daily_order_count)]
        ord_seq += daily_order_count

        # Distribute SKU sales across orders
        for _, prod in raw_koro_products.iterrows():
            pid = prod["product_id"]
            spec = sku_targets[pid]
            base_s = spec["sold"] // total_days
            rem_s = spec["sold"] % total_days
            s_units = base_s + (1 if d_idx < rem_s else 0)

            base_r = spec["ret"] // total_days
            rem_r = spec["ret"] % total_days
            r_units = base_r + (1 if d_idx < rem_r else 0)

            unit_price = float(prod["unit_price_eur"])
            unit_cost = float(prod["unit_cost_eur"])

            # Create line items
            if s_units > 0:
                assigned_order = orders_for_day[d_idx % len(orders_for_day)]
                assigned_cust = customers_data[(d_idx + int(pid[-1:])) % len(customers_data)]["customer_id"]
                gross = round(s_units * unit_price, 2)
                disc = round(gross * spec["disc_rate"], 2)
                refund = round(r_units * unit_price, 2)
                net = round(gross - disc - refund, 2)
                cogs = round(s_units * unit_cost, 2)

                order_items_rows.append(
                    {
                        "item_id": f"ITEM-{item_seq}",
                        "order_id": assigned_order,
                        "customer_id": assigned_cust,
                        "order_date": cur_date,
                        "product_id": pid,
                        "quantity_sold": int(s_units),
                        "unit_price_eur": unit_price,
                        "unit_cost_eur": unit_cost,
                        "line_gross_eur": gross,
                        "line_discount_eur": disc,
                        "line_refund_eur": refund,
                        "line_net_eur": net,
                        "cogs_eur": cogs,
                    }
                )
                item_seq += 1

    reason_shares_1kg_nut = [
        ("Vacuum Packaging Defect", 0.78),
        ("Shipping Damage", 0.12),
        ("Taste/Quality", 0.06),
        ("Wrong Item", 0.04),
    ]
    reason_shares_other = [
        ("Vacuum Packaging Defect", 0.22),
        ("Shipping Damage", 0.43),
        ("Taste/Quality", 0.25),
        ("Wrong Item", 0.10),
    ]

    ret_seq = 50001
    for _, prod in raw_koro_products.iterrows():
        pid = prod["product_id"]
        spec = sku_targets[pid]
        tot_ret = spec["ret"]
        shares = (
            reason_shares_1kg_nut
            if (prod["category_name"] == "Nuts & Butters" and prod["packaging_size"] == "1kg")
            else reason_shares_other
        )
        unit_price = float(prod["unit_price_eur"])

        # Allocate exact counts across reasons
        alloc = 0
        reason_counts = []
        for idx_sh, (r_name, r_share) in enumerate(shares):
            if idx_sh == len(shares) - 1:
                cnt = max(0, tot_ret - alloc)
            else:
                cnt = int(round(tot_ret * r_share))
                alloc += cnt
            reason_counts.append((r_name, cnt))

        # Distribute into return rows across dates
        cur_r_idx = 0
        rem_in_reason = reason_counts[cur_r_idx][1] if reason_counts else 0

        for d_idx, cur_date in enumerate(all_dates):
            base_r = spec["ret"] // total_days
            rem_r = spec["ret"] % total_days
            r_units = base_r + (1 if d_idx < rem_r else 0)

            while r_units > 0 and cur_r_idx < len(reason_counts):
                take = min(r_units, rem_in_reason)
                if take > 0:
                    r_name = reason_counts[cur_r_idx][0]
                    return_rows.append(
                        {
                            "return_id": f"RET-2026-{ret_seq:05d}",
                            "order_id": f"SW6-{10001 + d_idx * 110}",
                            "customer_id": customers_data[(d_idx + int(pid[-1:])) % len(customers_data)]["customer_id"],
                            "return_date": cur_date,
                            "product_id": pid,
                            "return_reason": r_name,
                            "returned_units": int(take),
                            "refunded_eur": round(take * unit_price, 2),
                        }
                    )
                    ret_seq += 1
                    r_units -= take
                    rem_in_reason -= take

                if rem_in_reason == 0:
                    cur_r_idx += 1
                    if cur_r_idx < len(reason_counts):
                        rem_in_reason = reason_counts[cur_r_idx][1]

    df_order_items = pd.DataFrame(order_items_rows)
    df_returns = pd.DataFrame(return_rows)

    # Filter to requested date window
    mask_items = (df_order_items["order_date"] >= eff_start) & (df_order_items["order_date"] <= eff_end)
    fct_order_items = df_order_items[mask_items].copy().reset_index(drop=True)

    mask_ret = (df_returns["return_date"] >= eff_start) & (df_returns["return_date"] <= eff_end)
    fct_returns = df_returns[mask_ret].copy().reset_index(drop=True)

    # Roll up fct_orders from line items
    fct_orders = (
        fct_order_items.groupby(["order_id", "customer_id", "order_date"], as_index=False)
        .agg(
            total_items_count=("quantity_sold", "sum"),
            total_gross_eur=("line_gross_eur", "sum"),
            total_discount_eur=("line_discount_eur", "sum"),
            total_refund_eur=("line_refund_eur", "sum"),
            total_net_eur=("line_net_eur", "sum"),
            total_cogs_eur=("cogs_eur", "sum"),
        )
        .sort_values(["order_date", "order_id"])
        .reset_index(drop=True)
    )

    # =========================================================================
    # 5. BRONZE LAYER: Raw Headers & Logs (`raw_shopware_orders`, `raw_return_logs`)
    # =========================================================================
    cust_map = {c["customer_id"]: c for c in customers_data}
    raw_orders_rows = []
    for _, ord_row in fct_orders.iterrows():
        c_info = cust_map.get(ord_row["customer_id"], {"market_country": "DE", "customer_segment": "D2C Repeat"})
        raw_orders_rows.append(
            {
                "order_id": ord_row["order_id"],
                "order_date": ord_row["order_date"],
                "market_country": c_info["market_country"],
                "customer_segment": c_info["customer_segment"],
                "order_gross_eur": ord_row["total_gross_eur"],
                "discount_eur": ord_row["total_discount_eur"],
                "order_net_eur": ord_row["total_net_eur"],
            }
        )
    raw_shopware_orders = pd.DataFrame(raw_orders_rows)

    raw_return_logs = fct_returns[
        ["return_id", "order_id", "product_id", "return_date", "return_reason", "returned_units", "refunded_eur"]
    ].copy()

    # =========================================================================
    # RETURN KIMBALL STRUCTURE (Zero hardcoded Gold Marts!)
    # =========================================================================
    return {
        # Bronze Ingestion Layer
        "raw_koro_products": raw_koro_products,
        "raw_shopware_orders": raw_shopware_orders,
        "raw_return_logs": raw_return_logs,
        # Silver Conformed Star Schema Layer (Kimball Core)
        "dim_products": dim_products,
        "dim_categories": dim_categories,
        "dim_customers": dim_customers,
        "fct_orders": fct_orders,
        "fct_order_items": fct_order_items,
        "fct_returns": fct_returns,
    }
