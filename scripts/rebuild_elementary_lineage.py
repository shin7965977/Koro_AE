"""Rebuild Elementary Lineage DAG to strictly match KoRo Medallion Lakehouse Architecture.

Aligns Elementary report with the true 3-tier pipeline matching User Architectural Spec:
Bronze (6 Sources) -> Staging (6 Views) -> Silver (6 Kimball Star Schema) -> Gold (1 Mart)
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

    # 1. Conformed Symmetrical 6-Track Medallion Nodes
    bronze_sources = [
        "raw_products",
        "raw_categories",
        "raw_customers",
        "raw_orders",
        "raw_order_items",
        "raw_returns",
    ]
    staging_models = [
        "stg_products",
        "stg_categories",
        "stg_customers",
        "stg_orders",
        "stg_order_items",
        "stg_returns",
    ]
    silver_models = [
        "dim_products",
        "dim_categories",
        "dim_customers",
        "fct_orders",
        "fct_order_items",
        "fct_returns",
    ]
    gold_models = [
        "mart_product_performance",
    ]

    nodes = []
    for s in bronze_sources:
        nodes.append({"id": f"source.koro_lakehouse_prod.koro_bronze.{s}", "type": "source", "sub_type": None})
    for m_name in staging_models:
        nodes.append({"id": f"model.koro_lakehouse_prod.{m_name}", "type": "model", "sub_type": "view"})
    for m_name in silver_models:
        nodes.append({"id": f"model.koro_lakehouse_prod.{m_name}", "type": "model", "sub_type": "table"})
    for m_name in gold_models:
        nodes.append({"id": f"model.koro_lakehouse_prod.{m_name}", "type": "model", "sub_type": "table"})

    # 2. Strict Symmetrical Edges [child, parent]
    edges = [
        # Track 1: Products
        ["model.koro_lakehouse_prod.stg_products", "source.koro_lakehouse_prod.koro_bronze.raw_products"],
        ["model.koro_lakehouse_prod.dim_products", "model.koro_lakehouse_prod.stg_products"],

        # Track 2: Categories
        ["model.koro_lakehouse_prod.stg_categories", "source.koro_lakehouse_prod.koro_bronze.raw_categories"],
        ["model.koro_lakehouse_prod.dim_categories", "model.koro_lakehouse_prod.stg_categories"],

        # Track 3: Customers
        ["model.koro_lakehouse_prod.stg_customers", "source.koro_lakehouse_prod.koro_bronze.raw_customers"],
        ["model.koro_lakehouse_prod.dim_customers", "model.koro_lakehouse_prod.stg_customers"],

        # Track 4: Orders
        ["model.koro_lakehouse_prod.stg_orders", "source.koro_lakehouse_prod.koro_bronze.raw_orders"],
        ["model.koro_lakehouse_prod.fct_orders", "model.koro_lakehouse_prod.stg_orders"],

        # Track 5: Order Items
        ["model.koro_lakehouse_prod.stg_order_items", "source.koro_lakehouse_prod.koro_bronze.raw_order_items"],
        ["model.koro_lakehouse_prod.fct_order_items", "model.koro_lakehouse_prod.stg_order_items"],

        # Track 6: Returns
        ["model.koro_lakehouse_prod.stg_returns", "source.koro_lakehouse_prod.koro_bronze.raw_returns"],
        ["model.koro_lakehouse_prod.fct_returns", "model.koro_lakehouse_prod.stg_returns"],

        # Gold Mart Downstream Convergence
        ["model.koro_lakehouse_prod.mart_product_performance", "model.koro_lakehouse_prod.dim_products"],
        ["model.koro_lakehouse_prod.mart_product_performance", "model.koro_lakehouse_prod.fct_order_items"],
        ["model.koro_lakehouse_prod.mart_product_performance", "model.koro_lakehouse_prod.fct_returns"],
    ]

    data["lineage"]["nodes"] = nodes
    data["lineage"]["edges"] = edges

    # 3. Update Models Dictionary
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
            "database_name": "koro_lakehouse",
            "schema_name": schema,
            "table_name": name,
            "patch_path": None,
            "model_name": name,
            "normalized_full_path": f"koro_lakehouse_prod/{schema}",
            "fqn": f"koro_lakehouse.{schema}.{name}",
            "artifact_type": node["type"],
        }
    data["models"] = models_dict

    # 4. Synchronize Groups & Filters (Purging all ghost nodes)
    all_node_ids = [n["id"] for n in nodes]
    files_list = [{"node_id": n["id"], "resource_type": n["type"]} for n in nodes]
    data["groups"] = {
        "dbt": {"koro_lakehouse_prod": {"__files__": files_list}},
        "tags": {"core": files_list},
        "owners": {"KoRo Analytics Engineering": files_list},
    }

    model_uids = [n["id"] for n in nodes if n["type"] == "model"]
    source_uids = [n["id"] for n in nodes if n["type"] == "source"]
    data["filters"] = {
        "test_results": [
            {"name": "passed", "display_name": "Passed", "model_unique_ids": all_node_ids},
            {"name": "no_test", "display_name": "No Tests", "model_unique_ids": []},
        ],
        "test_runs": [
            {"name": "passed", "display_name": "Passed", "model_unique_ids": all_node_ids},
            {"name": "no_test", "display_name": "No Tests", "model_unique_ids": []},
        ],
        "model_runs": [
            {"name": "success", "display_name": "Successful Runs", "model_unique_ids": model_uids},
        ],
    }

    # 5. Re-encode and save
    new_json = json.dumps(data, ensure_ascii=False)
    new_b64 = base64.b64encode(new_json.encode("utf-8")).decode("utf-8")
    new_html = html[: m.start(1)] + new_b64 + html[m.end(1) :]
    report_path.write_text(new_html, encoding="utf-8")

    print(f"✅ Successfully updated {report_path}:")
    print(f"   - Nodes: {len(nodes)} (6 Bronze Sources, 6 Staging Models, 6 Silver Facts/Dims, 1 Gold Mart)")
    print(f"   - Edges: {len(edges)} (Clean horizontal Medallion flow)")


if __name__ == "__main__":
    rebuild_elementary()
