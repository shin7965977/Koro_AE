view: mart_product_performance {
  sql_table_name: `@{GCP_PROJECT}.koro_marts.mart_product_performance` ;;
  label: "KoRo Product & Sales Intelligence"

  # ----------------------------------------------------------------------
  # Dimensions (Kimball Star Schema Attributes)
  # ----------------------------------------------------------------------

  dimension: product_id {
    primary_key: yes
    type: string
    sql: ${TABLE}.product_id ;;
    description: "Unique KoRo catalog SKU identifier (e.g. KORO-NUT-001)"
  }

  dimension: product_name {
    type: string
    sql: ${TABLE}.product_name ;;
    description: "Official public product title from KoRo web catalog"
  }

  dimension: category_name {
    type: string
    sql: ${TABLE}.category_name ;;
    description: "Top-level taxonomy: Nuts & Butters, Dried Fruits, Superfoods & Seeds, Snacks & Bars"
  }

  dimension: packaging_size {
    type: string
    sql: ${TABLE}.packaging_size ;;
    description: "Bulk packaging weight specification (1kg, 500g, 250g)"
  }

  dimension: is_available {
    type: yesno
    sql: ${TABLE}.is_available ;;
    description: "Website inventory availability flag"
  }

  dimension: days_of_supply {
    type: number
    sql: ${TABLE}.days_of_supply ;;
    value_format_name: decimal_1
    description: "Current stock on hand divided by daily sales run-rate"
  }

  # ----------------------------------------------------------------------
  # Measures (Aggregated Business Metrics Aligned with Semantic Rules)
  # ----------------------------------------------------------------------

  measure: total_sold_units {
    type: sum
    sql: ${TABLE}.sold_units ;;
    value_format_name: decimal_0
    description: "Total volume of product units sold"
  }

  measure: total_returned_units {
    type: sum
    sql: ${TABLE}.returned_units ;;
    value_format_name: decimal_0
    description: "Total units returned due to packaging defect or customer claim"
  }

  measure: gross_revenue {
    type: sum
    sql: ${TABLE}.gross_revenue_eur ;;
    value_format: "€#,##0"
    description: "Gross merchandise sales before discounts and refunds"
  }

  measure: net_revenue {
    type: sum
    sql: ${TABLE}.net_revenue_eur ;;
    value_format: "€#,##0"
    description: "Realized net revenue after subtracting promotional vouchers and refunded returns"
  }

  measure: unit_return_rate {
    type: number
    sql: ROUND(SAFE_DIVIDE(${total_returned_units} * 100.0, ${total_sold_units}), 2) ;;
    value_format: "0.00\%"
    description: "Percentage of sold units returned (Target threshold <= 2.50%)"
  }

  measure: net_contribution_margin_pct {
    type: average
    sql: ${TABLE}.net_margin_pct ;;
    value_format: "0.0\%"
    description: "Net profit after COGS and bulk packaging divided by net revenue"
  }
}
