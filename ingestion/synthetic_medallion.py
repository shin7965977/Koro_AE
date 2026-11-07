"""Deterministic Medallion Data Engine for KoRo E-Commerce POC.

Generates realistic public catalog attributes and synthetic transactional records
spanning Bronze, Silver, and Gold layers with zero external cloud dependencies.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd


def build_koro_medallion_data(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, pd.DataFrame]:
    """Generate deterministic Bronze, Silver, and Gold DataFrames for KoRo POC."""
    rng = np.random.default_rng(42)

    # 1. Catalog Definition (Bronze: raw_koro_products)
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
    raw_products = pd.DataFrame(
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

    # 2. Daily Order & Line-Item Generation over 90 days (2026-08-03 to 2026-10-31)
    base_start = date(2026, 8, 3)
    base_end = date(2026, 10, 31)
    eff_start = max(base_start, start_date) if start_date else base_start
    eff_end = min(base_end, end_date) if end_date else base_end
    if eff_start > eff_end:
        eff_start, eff_end = base_start, base_end

    total_days = (base_end - base_start).days + 1
    all_dates = [base_start + timedelta(days=i) for i in range(total_days)]

    # Deterministic SKU sales & return parameters
    sku_targets = {
        "KORO-NUT-001": {"sold": 5000, "ret": 260, "disc_rate": 0.06},  # 5.20% return rate!
        "KORO-NUT-002": {"sold": 3200, "ret": 112, "disc_rate": 0.05},  # 3.50% return rate
        "KORO-NUT-003": {"sold": 6400, "ret": 96, "disc_rate": 0.04},   # 1.50% return rate
        "KORO-NUT-004": {"sold": 4100, "ret": 74, "disc_rate": 0.05},   # 1.80% return rate
        "KORO-NUT-005": {"sold": 1800, "ret": 63, "disc_rate": 0.04},   # 3.50% return rate
        "KORO-FRU-001": {"sold": 5500, "ret": 99, "disc_rate": 0.07},   # 1.80% return rate
        "KORO-FRU-002": {"sold": 4800, "ret": 82, "disc_rate": 0.06},   # 1.71% return rate
        "KORO-FRU-003": {"sold": 2900, "ret": 35, "disc_rate": 0.05},   # 1.21% return rate
        "KORO-SUP-001": {"sold": 6100, "ret": 61, "disc_rate": 0.04},   # 1.00% return rate
        "KORO-SUP-002": {"sold": 3400, "ret": 41, "disc_rate": 0.04},   # 1.21% return rate
        "KORO-SNK-001": {"sold": 4600, "ret": 69, "disc_rate": 0.08},   # 1.50% return rate
        "KORO-SNK-002": {"sold": 3800, "ret": 57, "disc_rate": 0.07},   # 1.50% return rate
    }

    # Build daily records per SKU
    daily_records = []
    for _, prod in raw_products.iterrows():
        pid = prod["product_id"]
        spec = sku_targets[pid]
        base_daily_sold = spec["sold"] // total_days
        rem_sold = spec["sold"] % total_days
        base_daily_ret = spec["ret"] // total_days
        rem_ret = spec["ret"] % total_days

        for d_idx, d_val in enumerate(all_dates):
            s_units = base_daily_sold + (1 if d_idx < rem_sold else 0)
            r_units = base_daily_ret + (1 if d_idx < rem_ret else 0)
            gross = round(s_units * float(prod["unit_price_eur"]), 2)
            disc = round(gross * spec["disc_rate"], 2)
            refund = round(r_units * float(prod["unit_price_eur"]), 2)
            net = round(gross - disc - refund, 2)
            cogs = round(s_units * float(prod["unit_cost_eur"]), 2)

            daily_records.append(
                {
                    "order_date": d_val,
                    "product_id": pid,
                    "product_name": prod["product_name"],
                    "category_name": prod["category_name"],
                    "packaging_size": prod["packaging_size"],
                    "unit_price_eur": float(prod["unit_price_eur"]),
                    "unit_cost_eur": float(prod["unit_cost_eur"]),
                    "is_available": bool(prod["is_available"]),
                    "stock_on_hand": int(prod["stock_on_hand"]),
                    "sold_units": int(s_units),
                    "returned_units": int(r_units),
                    "gross_revenue_eur": gross,
                    "discount_eur": disc,
                    "refunded_eur": refund,
                    "net_revenue_eur": net,
                    "cogs_eur": cogs,
                }
            )

    df_daily_sku = pd.DataFrame(daily_records)
    # Apply date window filter
    mask = (df_daily_sku["order_date"] >= eff_start) & (
        df_daily_sku["order_date"] <= eff_end
    )
    df_filtered = df_daily_sku[mask].copy()

    # 3. Gold Layer: mart_product_performance
    grp_cols = [
        "product_id",
        "product_name",
        "category_name",
        "packaging_size",
        "unit_price_eur",
        "unit_cost_eur",
        "is_available",
        "stock_on_hand",
    ]
    mart_prod = (
        df_filtered.groupby(grp_cols, as_index=False)
        .agg(
            sold_units=("sold_units", "sum"),
            returned_units=("returned_units", "sum"),
            gross_revenue_eur=("gross_revenue_eur", "sum"),
            discount_eur=("discount_eur", "sum"),
            refunded_eur=("refunded_eur", "sum"),
            net_revenue_eur=("net_revenue_eur", "sum"),
            cogs_eur=("cogs_eur", "sum"),
        )
        .sort_values("net_revenue_eur", ascending=False)
        .reset_index(drop=True)
    )
    mart_prod["return_rate_pct"] = (
        mart_prod["returned_units"] * 100.0 / mart_prod["sold_units"].replace(0, np.nan)
    ).round(2)
    mart_prod["net_margin_eur"] = (
        mart_prod["net_revenue_eur"] - mart_prod["cogs_eur"]
    ).round(2)
    mart_prod["net_margin_pct"] = (
        mart_prod["net_margin_eur"]
        * 100.0
        / mart_prod["net_revenue_eur"].replace(0, np.nan)
    ).round(2)
    mart_prod["days_of_supply"] = (
        mart_prod["stock_on_hand"]
        / (mart_prod["sold_units"] / max(1, (eff_end - eff_start).days + 1))
    ).round(1)

    # 4. Gold Layer: mart_category_daily
    mart_cat_daily = (
        df_filtered.groupby(["order_date", "category_name"], as_index=False)
        .agg(
            sold_units=("sold_units", "sum"),
            returned_units=("returned_units", "sum"),
            gross_revenue_eur=("gross_revenue_eur", "sum"),
            discount_eur=("discount_eur", "sum"),
            refunded_eur=("refunded_eur", "sum"),
            net_revenue_eur=("net_revenue_eur", "sum"),
            cogs_eur=("cogs_eur", "sum"),
        )
        .sort_values(["order_date", "category_name"])
        .reset_index(drop=True)
    )

    # 5. Silver Layer: int_returns_enriched (Return Reason Breakdown)
    return_rows = []
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

    ret_seq = 1
    for _, row in mart_prod.iterrows():
        pid = row["product_id"]
        total_r = int(row["returned_units"])
        shares = (
            reason_shares_1kg_nut
            if (row["category_name"] == "Nuts & Butters" and row["packaging_size"] == "1kg")
            else reason_shares_other
        )
        allocated = 0
        for idx_r, (reason_name, share) in enumerate(shares):
            if idx_r == len(shares) - 1:
                units_r = max(0, total_r - allocated)
            else:
                units_r = int(round(total_r * share))
                allocated += units_r
            return_rows.append(
                {
                    "return_id": f"RET-2026-{ret_seq:04d}",
                    "product_id": pid,
                    "product_name": row["product_name"],
                    "category_name": row["category_name"],
                    "packaging_size": row["packaging_size"],
                    "return_reason": reason_name,
                    "returned_units": units_r,
                    "refunded_eur": round(units_r * float(row["unit_price_eur"]), 2),
                }
            )
            ret_seq += 1

    int_returns_enriched = pd.DataFrame(return_rows)

    # 6. Bronze Layer: raw_shopware_orders (Order Headers)
    markets = ["DE", "AT", "FR", "NL"]
    segments = ["D2C Repeat", "D2C First-Time", "B2B Office"]
    daily_totals = (
        df_filtered.groupby("order_date", as_index=False)
        .agg(
            gross_revenue_eur=("gross_revenue_eur", "sum"),
            discount_eur=("discount_eur", "sum"),
            net_revenue_eur=("net_revenue_eur", "sum"),
        )
        .sort_values("order_date")
    )

    order_rows = []
    ord_seq = 10001
    for _, d_row in daily_totals.iterrows():
        # Create ~110 synthetic orders per day so AOV is ~62 EUR
        num_orders = 110
        for o_i in range(num_orders):
            share = 1.0 / num_orders
            order_rows.append(
                {
                    "order_id": f"SW6-{ord_seq}",
                    "order_date": d_row["order_date"],
                    "market_country": markets[o_i % len(markets)],
                    "customer_segment": segments[o_i % len(segments)],
                    "order_gross_eur": round(float(d_row["gross_revenue_eur"]) * share, 2),
                    "discount_eur": round(float(d_row["discount_eur"]) * share, 2),
                    "order_net_eur": round(float(d_row["net_revenue_eur"]) * share, 2),
                }
            )
            ord_seq += 1

    raw_shopware_orders = pd.DataFrame(order_rows)

    return {
        "mart_product_performance": mart_prod,
        "mart_category_daily": mart_cat_daily,
        "int_returns_enriched": int_returns_enriched,
        "raw_shopware_orders": raw_shopware_orders,
        "raw_koro_products": raw_products,
    }
