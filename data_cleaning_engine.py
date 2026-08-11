"""Reusable data cleaning utilities for sales-demand datasets.

The cleaner accepts CSV/Excel data with common alternative column names,
standardises the schema used by the forecasting engine, derives date features,
and returns a detailed quality report.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd

CANONICAL_COLUMNS = [
    "Date",
    "Product",
    "Category",
    "Day_of_Week",
    "Is_Weekend",
    "Is_Promotion",
    "Month",
    "Year",
    "Quantity_Sold",
    "Stock_Level",
    "Unit_Weight_kg",
    "Unit_Volume_m3",
]

REQUIRED_SOURCE_COLUMNS = [
    "Date",
    "Product",
    "Quantity_Sold",
]

ALIASES: Dict[str, Iterable[str]] = {
    "Date": ["date", "salesdate", "transactiondate", "orderdate", "datetime"],
    "Product": ["product", "productname", "item", "itemname", "sku", "description"],
    "Category": ["category", "productcategory", "itemcategory", "group"],
    "Day_of_Week": ["dayofweek", "weekday", "day"],
    "Is_Weekend": ["isweekend", "weekend", "weekendflag"],
    "Is_Promotion": ["ispromotion", "promotion", "promo", "promotionstatus", "onpromotion"],
    "Month": ["month", "salesmonth"],
    "Year": ["year", "salesyear"],
    "Quantity_Sold": ["quantitysold", "qtysold", "salesquantity", "quantity", "qty", "demand", "unitsold", "unitssold"],
    "Stock_Level": ["stocklevel", "stock", "inventory", "inventorylevel", "currentstock"],
    "Unit_Weight_kg": ["unitweightkg", "unitweight", "weightkg", "productweightkg", "weight"],
    "Unit_Volume_m3": ["unitvolumem3", "unitvolume", "volumem3", "productvolumem3", "volume", "cbm"],
}


def _norm(name: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).strip().lower())


def detect_column_mapping(columns: Iterable[object]) -> Dict[str, str]:
    """Map uploaded column names to the canonical forecasting schema."""
    normalised = {_norm(c): str(c) for c in columns}
    mapping: Dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        candidates = [_norm(canonical), *[_norm(a) for a in aliases]]
        for candidate in candidates:
            if candidate in normalised:
                mapping[canonical] = normalised[candidate]
                break
    return mapping


def _to_binary(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)
    numeric = pd.to_numeric(series, errors="coerce")
    text = series.astype(str).str.strip().str.lower()
    translated = text.map({
        "yes": 1, "y": 1, "true": 1, "t": 1, "1": 1, "promotion": 1,
        "no": 0, "n": 0, "false": 0, "f": 0, "0": 0, "none": 0,
    })
    return numeric.fillna(translated).fillna(0).clip(0, 1).round().astype(int)


def _safe_mode(series: pd.Series, fallback: str) -> str:
    values = series.dropna().astype(str).str.strip()
    values = values[values.ne("")]
    return values.mode().iloc[0] if not values.mode().empty else fallback


def clean_sales_data(raw_df: pd.DataFrame, mapping: Dict[str, str] | None = None) -> Tuple[pd.DataFrame, dict]:
    """Clean and standardise an uploaded sales dataset.

    Accuracy cannot be guaranteed for arbitrary datasets. This function protects
    model quality by validating required fields, removing invalid target rows,
    standardising formats, deriving date features, and reporting all changes.
    """
    if raw_df is None or raw_df.empty:
        raise ValueError("The uploaded dataset is empty.")

    original = raw_df.copy()
    original.columns = [str(c).strip() for c in original.columns]
    mapping = mapping or detect_column_mapping(original.columns)

    missing_required = [c for c in REQUIRED_SOURCE_COLUMNS if c not in mapping]
    if missing_required:
        raise ValueError(
            "Required columns could not be identified: " + ", ".join(missing_required)
            + ". Please rename or map the uploaded columns."
        )

    data = pd.DataFrame(index=original.index)
    for canonical, source in mapping.items():
        if source in original.columns:
            data[canonical] = original[source]

    start_rows = len(data)
    duplicate_count = int(data.duplicated().sum())
    data = data.drop_duplicates().copy()

    # Standardise text fields.
    data["Product"] = data["Product"].astype("string").str.strip()
    data.loc[data["Product"].isin(["", "nan", "None"]), "Product"] = pd.NA

    if "Category" not in data:
        data["Category"] = "General"
    data["Category"] = data["Category"].astype("string").str.strip()
    data["Category"] = data["Category"].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    data["Category"] = data["Category"].fillna(_safe_mode(data["Category"], "General"))

    # Parse dates; invalid dates cannot contribute reliable time features.
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce", dayfirst=False)

    # Target must be numeric and non-negative.
    data["Quantity_Sold"] = pd.to_numeric(data["Quantity_Sold"], errors="coerce")
    invalid_target_mask = data["Quantity_Sold"].isna() | (data["Quantity_Sold"] < 0)

    invalid_core_mask = data["Date"].isna() | data["Product"].isna() | invalid_target_mask
    invalid_core_rows = int(invalid_core_mask.sum())
    data = data.loc[~invalid_core_mask].copy()

    if data.empty:
        raise ValueError("No valid rows remain after checking Date, Product, and Quantity_Sold.")

    # Optional numerical fields receive robust defaults.
    if "Stock_Level" not in data:
        data["Stock_Level"] = data["Quantity_Sold"]
    data["Stock_Level"] = pd.to_numeric(data["Stock_Level"], errors="coerce")
    stock_median = float(data["Stock_Level"].median()) if data["Stock_Level"].notna().any() else 0.0
    missing_stock = int(data["Stock_Level"].isna().sum())
    data["Stock_Level"] = data["Stock_Level"].fillna(stock_median).clip(lower=0)

    if "Unit_Weight_kg" not in data:
        data["Unit_Weight_kg"] = 1.0
    data["Unit_Weight_kg"] = pd.to_numeric(data["Unit_Weight_kg"], errors="coerce")
    positive_weights = data.loc[data["Unit_Weight_kg"] > 0, "Unit_Weight_kg"]
    weight_median = float(positive_weights.median()) if not positive_weights.empty else 1.0
    invalid_weight_mask = data["Unit_Weight_kg"].isna() | (data["Unit_Weight_kg"] <= 0)
    invalid_weights = int(invalid_weight_mask.sum())
    data.loc[invalid_weight_mask, "Unit_Weight_kg"] = weight_median

    # Volume is used by the truck-allocation step. Keep older datasets usable,
    # but clearly report when a conservative default had to be supplied.
    if "Unit_Volume_m3" not in data:
        data["Unit_Volume_m3"] = 0.01
        missing_volume = int(len(data))
    else:
        data["Unit_Volume_m3"] = pd.to_numeric(data["Unit_Volume_m3"], errors="coerce")
        positive_volumes = data.loc[data["Unit_Volume_m3"] > 0, "Unit_Volume_m3"]
        volume_median = float(positive_volumes.median()) if not positive_volumes.empty else 0.01
        invalid_volume_mask = data["Unit_Volume_m3"].isna() | (data["Unit_Volume_m3"] <= 0)
        missing_volume = int(invalid_volume_mask.sum())
        data.loc[invalid_volume_mask, "Unit_Volume_m3"] = volume_median

    if "Is_Promotion" not in data:
        data["Is_Promotion"] = 0
    data["Is_Promotion"] = _to_binary(data["Is_Promotion"])

    # Always derive date features from Date to avoid inconsistent uploaded values.
    data["Day_of_Week"] = data["Date"].dt.day_name()
    data["Is_Weekend"] = (data["Date"].dt.weekday >= 5).astype(int)
    data["Month"] = data["Date"].dt.month.astype(int)
    data["Year"] = data["Date"].dt.year.astype(int)

    # Reduce extreme target noise using IQR clipping, while retaining every valid row.
    q1 = float(data["Quantity_Sold"].quantile(0.25))
    q3 = float(data["Quantity_Sold"].quantile(0.75))
    iqr = q3 - q1
    lower = max(0.0, q1 - 1.5 * iqr)
    upper = q3 + 1.5 * iqr
    outlier_mask = (data["Quantity_Sold"] < lower) | (data["Quantity_Sold"] > upper)
    clipped_outliers = int(outlier_mask.sum())
    if iqr > 0:
        data["Quantity_Sold"] = data["Quantity_Sold"].clip(lower=lower, upper=upper)

    # Quantities are operational counts; preserve integer meaning.
    data["Quantity_Sold"] = data["Quantity_Sold"].round().astype(int)
    data["Stock_Level"] = data["Stock_Level"].round(2)
    data["Unit_Weight_kg"] = data["Unit_Weight_kg"].round(4)
    data["Unit_Volume_m3"] = data["Unit_Volume_m3"].round(6)
    data["Date"] = data["Date"].dt.strftime("%Y-%m-%d")

    data = data[CANONICAL_COLUMNS].sort_values("Date").reset_index(drop=True)

    warnings = []
    if len(data) < 50:
        warnings.append("Fewer than 50 valid rows remain; model evaluation may be unstable.")
    if data["Quantity_Sold"].nunique() < 2:
        warnings.append("Quantity_Sold has no meaningful variation; the model cannot learn demand patterns.")
    if data["Product"].nunique() < 2:
        warnings.append("Only one product is present; predictions will not generalise across products.")
    if missing_volume:
        warnings.append(
            f"{missing_volume} row(s) had no valid Unit Volume; a safe default/median was used. "
            "Provide Unit Volume (m³/CBM) for more accurate truck allocation."
        )

    report = {
        "input_rows": int(start_rows),
        "output_rows": int(len(data)),
        "input_columns": int(len(original.columns)),
        "output_columns": int(len(data.columns)),
        "duplicates_removed": duplicate_count,
        "invalid_core_rows_removed": invalid_core_rows,
        "missing_stock_filled": missing_stock,
        "invalid_weights_replaced": invalid_weights,
        "invalid_volumes_replaced": missing_volume,
        "target_outliers_clipped": clipped_outliers,
        "products": int(data["Product"].nunique()),
        "categories": int(data["Category"].nunique()),
        "date_start": str(data["Date"].min()),
        "date_end": str(data["Date"].max()),
        "mapping": mapping,
        "warnings": warnings,
    }
    return data, report


def build_sales_dashboard_summary(cleaned_df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Build Purchasing dashboard values only from the active cleaned sales dataset."""
    if cleaned_df is None or cleaned_df.empty:
        raise ValueError("The active sales dataset is empty.")

    required = {"Date", "Product", "Quantity_Sold", "Stock_Level"}
    missing = sorted(required.difference(cleaned_df.columns))
    if missing:
        raise ValueError("Active dataset is missing dashboard field(s): " + ", ".join(missing))

    data = cleaned_df.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Quantity_Sold"] = pd.to_numeric(data["Quantity_Sold"], errors="coerce").fillna(0)
    data["Stock_Level"] = pd.to_numeric(data["Stock_Level"], errors="coerce").fillna(0)
    data = data.dropna(subset=["Date", "Product"])
    if data.empty:
        raise ValueError("The active sales dataset has no valid dated product records.")

    # Current stock is the latest recorded stock level for each product, never a
    # seeded/demo stock_items row from SQLite.
    latest = (
        data.sort_values("Date")
        .groupby("Product", as_index=False, sort=True)
        .tail(1)
        .sort_values("Product")
        .reset_index(drop=True)
    )

    summary = {
        "products": int(data["Product"].nunique()),
        "total_sales_qty": float(data["Quantity_Sold"].sum()),
        "current_stock_level": float(latest["Stock_Level"].sum()),
        "latest_sales_date": data["Date"].max().strftime("%Y-%m-%d"),
        "rows": int(len(data)),
    }
    latest["Date"] = latest["Date"].dt.strftime("%Y-%m-%d")
    return summary, latest

FOOD_KEYWORDS = {
    "food", "foods", "beverage", "beverages", "drink", "drinks", "bakery",
    "snack", "snacks", "frozen", "dairy", "meat", "chicken", "poultry",
    "fish", "seafood", "rice", "noodle", "noodles", "bread", "cake",
    "biscuit", "biscuits", "cookie", "cookies", "juice", "water", "coffee",
    "tea", "milk", "sauce", "condiment", "cereal", "grain", "vegetable",
    "vegetables", "fruit", "fruits", "grocery", "flour", "sugar", "oil",
    "egg", "eggs", "cheese", "yogurt", "chocolate", "chips", "fries",
    "nugget", "nuggets", "dumpling", "dumplings", "peanut", "peanuts",
    "cracker", "crackers", "croissant", "muffin", "pandan", "soy", "orange",
    "wafer", "canned", "spice", "spices", "dessert", "confectionery"
}

NON_FOOD_KEYWORDS = {
    "electronics", "electronic", "computer", "laptop", "mobile", "phone",
    "smartphone", "tablet", "television", "clothing", "fashion", "shirt",
    "shoe", "shoes", "automotive", "vehicle", "furniture", "medicine",
    "pharmaceutical", "machinery", "machine", "construction", "chemical",
    "cosmetic", "cosmetics", "book", "books", "stationery", "appliance"
}


def assess_dataset_relevance(cleaned_df: pd.DataFrame) -> dict:
    """Check whether a cleaned dataset is relevant to food-demand forecasting.

    The check intentionally combines schema, category/product wording, target
    quality, date coverage and sample size. It prevents an unrelated dataset
    with matching column names from replacing the active forecasting data.
    """
    if cleaned_df is None or cleaned_df.empty:
        return {"is_relevant": False, "score": 0, "status": "Rejected", "reasons": ["The dataset contains no valid rows."]}

    required = {"Date", "Product", "Quantity_Sold", "Category"}
    missing = sorted(required.difference(cleaned_df.columns))
    if missing:
        return {
            "is_relevant": False,
            "score": 0,
            "status": "Rejected",
            "reasons": ["Missing required cleaned fields: " + ", ".join(missing)],
        }

    text = (
        cleaned_df["Product"].fillna("").astype(str) + " "
        + cleaned_df["Category"].fillna("").astype(str)
    ).str.lower()

    def contains_any(value: str, vocabulary: set[str]) -> bool:
        tokens = set(re.findall(r"[a-z]+", value))
        return bool(tokens.intersection(vocabulary))

    food_matches = text.map(lambda v: contains_any(v, FOOD_KEYWORDS))
    non_food_matches = text.map(lambda v: contains_any(v, NON_FOOD_KEYWORDS))
    food_ratio = float(food_matches.mean())
    non_food_ratio = float(non_food_matches.mean())

    score = 0
    reasons = []

    if food_ratio >= 0.60:
        score += 45
    elif food_ratio >= 0.30:
        score += 30
    elif food_ratio >= 0.15:
        score += 15
        reasons.append("Only a small proportion of products or categories could be confirmed as food-related.")
    else:
        reasons.append("Product and category values do not appear to describe food or beverage sales.")

    if non_food_ratio >= 0.30:
        score -= 50
        reasons.append("A large proportion of records contain clearly non-food categories or products.")
    elif non_food_ratio > 0:
        score -= 15
        reasons.append("Some records contain non-food categories or products.")

    row_count = len(cleaned_df)
    if row_count >= 200:
        score += 15
    elif row_count >= 50:
        score += 8
    else:
        reasons.append("Too few valid records are available for reliable model evaluation.")

    if cleaned_df["Quantity_Sold"].nunique() >= 10:
        score += 15
    elif cleaned_df["Quantity_Sold"].nunique() >= 2:
        score += 5
    else:
        reasons.append("Quantity_Sold has insufficient variation for demand forecasting.")

    dates = pd.to_datetime(cleaned_df["Date"], errors="coerce")
    date_span_days = int((dates.max() - dates.min()).days) if dates.notna().any() else 0
    if date_span_days >= 180:
        score += 15
    elif date_span_days >= 30:
        score += 8
    else:
        reasons.append("The date range is too short to represent useful demand patterns.")

    if cleaned_df["Product"].nunique() >= 2:
        score += 10
    else:
        reasons.append("The dataset contains only one product.")

    is_relevant = score >= 55 and non_food_ratio < 0.30 and food_ratio >= 0.15
    status = "Relevant" if is_relevant else "Irrelevant / Rejected"
    if is_relevant and not reasons:
        reasons.append("The schema, food-related content, target variation and date coverage are suitable for evaluation.")

    return {
        "is_relevant": bool(is_relevant),
        "score": int(max(0, min(100, score))),
        "status": status,
        "food_match_percent": round(food_ratio * 100, 1),
        "non_food_match_percent": round(non_food_ratio * 100, 1),
        "date_span_days": date_span_days,
        "reasons": reasons,
    }
