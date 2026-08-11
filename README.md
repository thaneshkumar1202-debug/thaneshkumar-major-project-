# Smart Demand Forecasting and Truck Allocation System

## Run
```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Demo accounts
- Purchasing: purchase@vilvam.com / purchase123
- Logistics: logistics@vilvam.com / logistics123
- Admin (technical backup): admin@vilvam.com / admin123

The database is created and upgraded automatically on first run.

## Dataset rejection protection
- The Purchasing Department is the owner and normal uploader of sales datasets.
- Admin has the same upload control only as a technical backup when Purchasing cannot upload because of a system/technical issue.
- Logistics can open the active Sales Dataset in read-only mode and cannot upload, edit, delete, or activate it.
- A fresh copy of the application starts without an active forecasting dataset. Sample files are kept under `test_datasets/` for testing.
- The active dataset and operational records are shared across browser sessions. Logging in never clears another department's data; only the explicit Super Admin reset does that.
- Uploaded datasets are validated before model evaluation or activation.
- Missing required columns, unrelated non-food products, insufficient rows, invalid targets, or poor model performance block activation.
- The interface displays a clear Forecasting Blocked / Dataset Validation Failed message with the specific reasons.
- The active forecasting dataset remains unchanged after rejection.
- The Forecasting page validates the active dataset again before displaying results.

## Purchasing dashboard data rule
- Before Purchasing activates a valid sales dataset, the Purchasing Dashboard shows a `Waiting for Sales Dataset` message and no sales/stock KPI values or demo stock table.
- After activation, the Purchasing Dashboard reads the active cleaned dataset directly.
- Its product count, total sales quantity, current stock level and latest product-stock table therefore change with the newly activated dataset instead of using seeded SQLite demo stock as live KPI data.

## Logistics workflow before Purchasing uploads data
- Logistics receives a pop-up/warning that forecasting cannot proceed.
- Truck details, driver information, truck status, fuel KPIs, fleet charts, and other logistics records remain available.
- Forecasting and Smart Truck Allocation stay locked until Purchasing activates a valid dataset (or Admin activates it during technical support).

## Forecast-based truck allocation
- Demand quantity is forecast for the next 7 days.
- Forecast load uses product quantity × unit weight and quantity × unit volume.
- The recommendation checks only trucks whose live status is `Available`.
- Fleet selection must satisfy both weight (kg) and volume (m³) capacity.
- Forecast/model cache entries are keyed to the active dataset content so replacing the dataset forces the dashboard and forecasting pages onto the new data.

## Delivery, truck status, fuel and toll KPIs
- Purchasing Customer Management includes a Quick Customer Sales Request: Purchasing selects an active customer, an item from the activated sales dataset and quantity; the system generates a simple customer-request message and notifies Logistics.
- Delivery Schedule receives pending Purchasing requests directly. Selecting the request auto-fills customer, product, quantity, dataset unit weight and dataset unit volume, preventing Logistics from retyping the sales requirement.
- Route fuel and toll KPIs come from `delivery_schedules`, the same records that drive truck delivery status.
- Delivery Scheduling calculates order weight (`Quantity × Unit Weight`) and volume (`Quantity × Unit Volume`) and recommends only a currently `Available` truck whose kg AND m³ capacities both fit the order.
- Assigning the order immediately changes the linked truck `Available → Assigned`, records the Delivery Schedule and exact assignment time, and removes that truck from new recommendations until the delivery is verified/completed.
- Create/assign the Delivery Schedule first; this stores distance, fuel litres, fuel cost and the manager-entered toll value.
- Changing a Delivery Schedule to `On Route`, `Arrived` or `Delivered` also updates the linked truck status automatically.
- Truck Management cannot place a truck into a delivery workflow status when no active Delivery Schedule exists, preventing an `On Route` truck with zero route KPI data.

## Viva-ready delivery verification
- Delivery Schedule includes a `Start 1-Minute Demo Trip` control. It puts the linked truck `On Route`, displays a live 60-second stopwatch, and automatically changes the delivery to `Delivered / Waiting Verification` when the timer reaches zero.
- The one-minute timer does not bypass management verification: `Completed / Verified` and truck `Available` happen only after Delivery Verification is approved.
- At delivery, a `Goods delivered on time!` dialog is shown and the record leaves the active Delivery Schedule queue. It remains in Delivery Verification as `Waiting Verification`; after approval it is kept as completed history in Reports.
- The 30-day demo generator creates historical completed orders but intentionally leaves the latest delivery as `Delivered / Waiting Verification`.
- Delivery Verification lists the waiting record, records actual delivered quantity, management user and note, then marks it `Completed / Verified` and releases the truck to `Available`.
- Verification is guarded so an already verified or non-delivered record cannot be verified again.
- Large/impossible forecast loads are checked without exhaustive truck-combination searching, preventing Smart Truck Allocation from hanging on a large fleet.

## Fleet images
- Toyota Hiace uses the supplied Toyota Hiace photo.
- Hino 300 Light Duty uses the supplied Hino 1/2-ton photo.
- Hino 700 uses the supplied Hino 700 photo.
- Scania Heavy Duty uses the supplied Scania photo.
