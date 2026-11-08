"""Rebuild Elementary Lineage DAG to strictly match KoRo Medallion Lakehouse Architecture.

Aligns Elementary report with the true 3-tier pipeline:
Bronze Sources -> Staging (Views/Tables) -> Silver Kimball Star Schema -> Gold Marts
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
report_path = _ROOT / "docs" / "elementary_report.html"


def rebuild_elementary() -> None:
    html = report_path.read_text(encoding="utf-8")
    m = re.search(r"atob\('([^']+)'\)", html)
    if not m:
        raise ValueError("Could not find atob payload in elementary_report.html")

    data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))

    # 1. Conformed Sources & Models
    nodes = [
        # Bronze Sources
        {"id": "source.koro_lakehouse_prod.koro_bronze.raw_koro_products", "type": "source", "sub_type": None},
        {"id": "source.koro_lakehouse_prod.koro_bronze.raw_shopware_orders", "type": "source", "sub_type": None},
        {"id": "source.koro_lakehouse_prod.koro_bronze.raw_shopware_order_items", "type": "source", "sub_type": None},
        {"id": "source.koro_lakehouse_prod.koro_bronze.raw_return_logs", "type": "source", "sub_type": None},
        # Staging Models
        {"id": "model.koro_lakehouse_prod.stg_koro_products", "type": "model", "sub_type": "view"},
        {"id": "model.koro_lakehouse_prod.stg_shopware_orders", "type": "model", "sub_type": "view"},
        {"id": "model.koro_lakehouse_prod.stg_shopware_order_items", "type": "model", "sub_type": "view"},
        {"id": "model.koro_lakehouse_prod.stg_return_logs", "type": "model", "sub_type": "view"},
        # Silver Kimball Star Schema Models
        {"id": "model.koro_lakehouse_prod.dim_products", "type": "model", "sub_type": "table"},
        {"id": "model.koro_lakehouse_prod.dim_categories", "type": "model", "sub_type": "table"},
        {"id": "model.koro_lakehouse_prod.dim_customers", "type": "model", "sub_type": "table"},
        {"id": "model.koro_lakehouse_prod.fct_orders", "type": "model", "sub_type": "table"},
        {"id": "model.koro_lakehouse_prod.fct_order_items", "type": "model", "sub_type": "table"},
        {"id": "model.koro_lakehouse_prod.fct_returns", "type": "model", "sub_type": "table"},
        # Gold Mart
        {"id": "model.koro_lakehouse_prod.mart_product_performance", "type": "model", "sub_type": "table"},
    ]

    # 2. Clean, Parallel, Architectural Edges [child, parent]
    edges = [
        # Bronze Ingestion -> Staging
        ["model.koro_lakehouse_prod.stg_koro_products", "source.koro_lakehouse_prod.koro_bronze.raw_koro_products"],
        ["model.koro_lakehouse_prod.stg_shopware_orders", "source.koro_lakehouse_prod.koro_bronze.raw_shopware_orders"],
        ["model.koro_lakehouse_prod.stg_shopware_order_items", "source.koro_lakehouse_prod.koro_bronze.raw_shopware_order_items"],
        ["model.koro_lakehouse_prod.stg_return_logs", "source.koro_lakehouse_prod.koro_bronze.raw_return_logs"],

        # Staging -> Silver Kimball Facts & Dimensions
        ["model.koro_lakehouse_prod.dim_products", "model.koro_lakehouse_prod.stg_koro_products"],
        ["model.koro_lakehouse_prod.dim_categories", "model.koro_lakehouse_prod.stg_koro_products"],
        ["model.koro_lakehouse_prod.dim_customers", "model.koro_lakehouse_prod.stg_shopware_orders"],
        ["model.koro_lakehouse_prod.fct_orders", "model.koro_lakehouse_prod.stg_shopware_orders"],
        ["model.koro_lakehouse_prod.fct_order_items", "model.koro_lakehouse_prod.stg_shopware_order_items"],
        ["model.koro_lakehouse_prod.fct_returns", "model.koro_lakehouse_prod.stg_return_logs"],

        # Silver -> Gold Performance Mart
        ["model.koro_lakehouse_prod.mart_product_performance", "model.koro_lakehouse_prod.dim_products"],
        ["model.koro_lakehouse_prod.mart_product_performance", "model.koro_lakehouse_prod.fct_order_items"],
        ["model.koro_lakehouse_prod.mart_product_performance", "model.koro_lakehouse_prod.fct_returns"],
    ]

    data["lineage"]["nodes"] = nodes
    data["lineage"]["edges"] = edges

    # 3. Update Models Directory
    models_dict = {}
    for node in nodes:
        uid = node["id"]
        parts = uid.split(".")
        name = parts[-1]
        schema = "koro_bronze" if node["type"] == "source" else ("koro_gold" if "mart" in name else "koro_silver")
        models_dict[uid] = {
            "name": name,
            "unique_id": uid,
            "owners": ["KoRo Analytics Engineering"],
            "tags": ["core", schema],
            "package_name": "koro_lakehouse_prod",
            "description": f"Conformed {schema} data asset {name}",
            "full_path": f"models/{schema}/{name}.sql",
            "meta": {},
            "materialization": node.get("sub_type") or "source",
            "database_name": "koro-analytics-poc",
            "schema_name": schema,
            "table_name": name,
            "patch_path": None,
            "model_name": name,
            "normalized_full_path": f"koro_lakehouse_prod/{schema}",
            "fqn": f"koro-analytics-poc.{schema}.{name}",
            "artifact_type": node["type"],
        }
    data["models"] = models_dict

    # 4. Re-encode and save
    new_json = json.dumps(data, ensure_ascii=False)
    new_b64 = base64.b64encode(new_json.encode("utf-8")).decode("utf-8")
    new_html = html[: m.start(1)] + new_b64 + html[m.end(1) :]
    report_path.write_text(new_html, encoding="utf-8")

    print(f"✅ Successfully updated {report_path}:")
    print(f"   - Nodes: {len(nodes)} (4 Bronze Sources, 4 Staging Models, 6 Silver Facts/Dims, 1 Gold Mart)")
    print(f"   - Edges: {len(edges)} (Clean horizontal Medallion flow)")


if __name__ == "__main__":
    rebuild_elementary()
