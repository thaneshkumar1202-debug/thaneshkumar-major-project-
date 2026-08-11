from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def _normalise(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def load_sales_history(data_path: str | Path = "data/cleaned_data.csv") -> pd.DataFrame:
    path = Path(data_path)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def recommend_stock_orders(stock_rows: list[tuple], forecast_days: int = 7, safety_days: int = 3,
                           data_path: str | Path = "data/cleaned_data.csv") -> list[dict[str, Any]]:
    """Create transparent reorder suggestions from actual stock and recent demand.

    stock_rows must follow database.get_stock_items():
    id, item_name, category, quantity, unit, daily_usage, reorder_level,
    supplier, days_remaining, operational_status.
    """
    sales = load_sales_history(data_path)
    product_col = "Product" if "Product" in sales.columns else None
    qty_col = "Quantity_Sold" if "Quantity_Sold" in sales.columns else None
    if product_col and qty_col:
        sales["_product_key"] = sales[product_col].map(_normalise)
        if "Date" in sales.columns and sales["Date"].notna().any():
            latest = sales["Date"].max()
            recent = sales[sales["Date"] >= latest - pd.Timedelta(days=29)]
        else:
            recent = sales
    else:
        recent = pd.DataFrame()

    output: list[dict[str, Any]] = []
    for row in stock_rows:
        item_id, item, category, current, unit, actual_daily, reorder, supplier, days_left, *extra = row
        current = float(current or 0)
        actual_daily = float(actual_daily or 0)
        predicted_daily = actual_daily
        source = "Actual daily usage"
        if not recent.empty:
            matched = recent[recent["_product_key"] == _normalise(item)]
            if not matched.empty:
                predicted_daily = max(0.0, float(pd.to_numeric(matched[qty_col], errors="coerce").fillna(0).mean()))
                source = "Recent sales prediction"

        blended_daily = max(actual_daily, (actual_daily * 0.4) + (predicted_daily * 0.6))
        predicted_demand = round(blended_daily * forecast_days)
        safety_stock = round(blended_daily * safety_days)
        target_stock = max(float(reorder), predicted_demand + safety_stock)
        suggested = max(0, int(round(target_stock - current)))
        shortage_days = round(current / blended_daily, 1) if blended_daily > 0 else 999

        if suggested <= 0:
            urgency = "No Order Needed"
        elif shortage_days <= 2:
            urgency = "Critical"
        elif shortage_days <= forecast_days:
            urgency = "Order Now"
        else:
            urgency = "Order Soon"

        reason = (
            f"Current stock is {current:g} {unit}. Expected {forecast_days}-day demand is "
            f"{predicted_demand:g} {unit}, with {safety_stock:g} {unit} safety stock. "
            f"The recommendation uses {source.lower()} and the reorder level of {float(reorder):g} {unit}."
        )
        output.append({
            "item_id": int(item_id), "item": item, "category": category,
            "current_stock": int(current), "unit": unit,
            "actual_daily_usage": round(actual_daily, 2),
            "predicted_daily_usage": round(predicted_daily, 2),
            "forecast_days": forecast_days, "predicted_demand": int(predicted_demand),
            "safety_stock": int(safety_stock), "reorder_level": int(reorder),
            "suggested_order_qty": suggested, "supplier": supplier or "Not assigned",
            "days_remaining": shortage_days, "urgency": urgency, "reason": reason,
        })
    return output
