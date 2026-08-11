import hashlib
import math

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split


_FEATURE_COLUMNS = [
    "Product_Code",
    "Category_Code",
    "Day_Code",
    "Is_Weekend",
    "Is_Promotion",
    "Month",
    "Year",
    "Stock_Level",
    "Unit_Weight_kg",
    "Unit_Volume_m3",
]

_model = None
_product_lookup = None
_category_lookup = None
_day_lookup = None
_feature_defaults = None
_model_signature = None


def _dataset_signature(df):
    """Fingerprint model inputs so a forecast can never reuse another dataset's model."""
    frame=df.reset_index(drop=True)
    values=pd.util.hash_pandas_object(frame,index=True).values.tobytes()
    columns='\x1f'.join(map(str,frame.columns)).encode('utf-8')
    return hashlib.sha256(columns+b'\x1e'+values).hexdigest()


def reset_model():
    """Clear process-wide model state after the active dataset is replaced/reset."""
    global _model, _product_lookup, _category_lookup, _day_lookup, _feature_defaults, _model_signature
    _model=None
    _product_lookup=None
    _category_lookup=None
    _day_lookup=None
    _feature_defaults=None
    _model_signature=None


def _prepare_training_frame(df):
    data = df.copy()
    data["Date"] = pd.to_datetime(data["Date"])

    for col in ["Product", "Category", "Day_of_Week"]:
        data[col] = data[col].astype(str)

    data["Product_Code"] = data["Product"].astype("category").cat.codes
    data["Category_Code"] = data["Category"].astype("category").cat.codes
    data["Day_Code"] = data["Day_of_Week"].astype("category").cat.codes

    product_lookup = dict(zip(data["Product"], data["Product_Code"]))
    category_lookup = dict(zip(data["Category"], data["Category_Code"]))
    day_lookup = dict(zip(data["Day_of_Week"], data["Day_Code"]))

    return data, product_lookup, category_lookup, day_lookup


def train_model(df):
    """Train the demand model used by the Streamlit forecasting page."""
    global _model, _product_lookup, _category_lookup, _day_lookup, _feature_defaults, _model_signature

    data, product_lookup, category_lookup, day_lookup = _prepare_training_frame(df)
    X = data[_FEATURE_COLUMNS]
    y = data["Quantity_Sold"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=120,
        random_state=42,
        min_samples_leaf=2,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    mae = round(float(mean_absolute_error(y_test, preds)), 2)
    r2 = float(r2_score(y_test, preds))
    accuracy = round(float(r2 * 100), 2)

    _model = model
    _product_lookup = product_lookup
    _category_lookup = category_lookup
    _day_lookup = day_lookup
    _feature_defaults = data.groupby("Product").agg(
        Category=("Category", "last"),
        Stock_Level=("Stock_Level", "mean"),
        Unit_Weight_kg=("Unit_Weight_kg", "first"),
        Unit_Volume_m3=("Unit_Volume_m3", "first"),
        Is_Promotion=("Is_Promotion", "mean"),
    )
    _model_signature = _dataset_signature(df)

    return model, accuracy, mae, X_test, y_test, preds


def forecast_next_7_days(df):
    """Forecast demand for every product for the next seven days."""
    global _model, _model_signature

    if _model is None or _model_signature != _dataset_signature(df):
        train_model(df)

    data = df.copy()
    data["Date"] = pd.to_datetime(data["Date"])
    last_date = data["Date"].max()
    products = sorted(data["Product"].dropna().unique())

    rows = []
    for offset in range(1, 8):
        forecast_date = last_date + pd.Timedelta(days=offset)
        day_name = forecast_date.day_name()
        for product in products:
            defaults = _feature_defaults.loc[product]
            category = defaults["Category"]
            feature_row = pd.DataFrame([
                {
                    "Product_Code": _product_lookup.get(product, 0),
                    "Category_Code": _category_lookup.get(category, 0),
                    "Day_Code": _day_lookup.get(day_name, 0),
                    "Is_Weekend": int(forecast_date.weekday() >= 5),
                    "Is_Promotion": int(round(defaults["Is_Promotion"])),
                    "Month": forecast_date.month,
                    "Year": forecast_date.year,
                    "Stock_Level": float(defaults["Stock_Level"]),
                    "Unit_Weight_kg": float(defaults["Unit_Weight_kg"]),
                    "Unit_Volume_m3": float(defaults["Unit_Volume_m3"]),
                }
            ])
            predicted_qty = max(0, int(round(_model.predict(feature_row[_FEATURE_COLUMNS])[0])))
            rows.append(
                {
                    "Date": forecast_date.strftime("%Y-%m-%d"),
                    "Product": product,
                    "Predicted_Qty": predicted_qty,
                }
            )

    return pd.DataFrame(rows)




def evaluate_model(df):
    """Train the model and return presentation-ready evaluation details."""
    model, accuracy, mae, X_test, y_test, preds = train_model(df)
    rmse = round(float(np.sqrt(np.mean((np.array(y_test) - np.array(preds)) ** 2))), 2)
    r2 = round(float(r2_score(y_test, preds)), 4)

    data = df.copy()
    data["Date"] = pd.to_datetime(data["Date"])
    predictions = pd.DataFrame({
        "Actual Sales": y_test.reset_index(drop=True).astype(float),
        "Predicted Sales": np.round(preds, 2),
    })
    predictions["Absolute Error"] = (predictions["Actual Sales"] - predictions["Predicted Sales"]).abs().round(2)

    importances = pd.DataFrame({
        "Feature": _FEATURE_COLUMNS,
        "Importance": np.round(model.feature_importances_ * 100, 2),
    }).sort_values("Importance", ascending=False).reset_index(drop=True)

    dataset_info = {
        "total_records": int(len(df)),
        "training_records": int(len(df) * 0.8),
        "testing_records": int(len(df) - int(len(df) * 0.8)),
        "products": int(df["Product"].nunique()) if "Product" in df.columns else 0,
        "categories": int(df["Category"].nunique()) if "Category" in df.columns else 0,
        "start_date": data["Date"].min().strftime("%Y-%m-%d"),
        "end_date": data["Date"].max().strftime("%Y-%m-%d"),
    }

    return {
        "algorithm": "Random Forest Regressor",
        "target_variable": "Quantity_Sold",
        "accuracy": accuracy,
        "mae": mae,
        "rmse": rmse,
        "r2_score": r2,
        "dataset_info": dataset_info,
        "predictions": predictions,
        "feature_importance": importances,
    }


def allocate_trucks(predicted_qty, unit_weight_kg):
    """Choose a truck class and count from total forecasted load."""
    total_weight = round(float(predicted_qty) * float(unit_weight_kg), 2)

    capacities = [
        ("1-Ton Van", 1000),
        ("3-Ton Truck", 3000),
        ("5-Ton Truck", 5000),
        ("10-Ton Lorry", 10000),
    ]

    for truck_type, capacity in capacities:
        trucks_needed = max(1, math.ceil(total_weight / capacity))
        if trucks_needed <= 3:
            return truck_type, trucks_needed, total_weight

    truck_type, capacity = capacities[-1]
    return truck_type, max(1, math.ceil(total_weight / capacity)), total_weight
