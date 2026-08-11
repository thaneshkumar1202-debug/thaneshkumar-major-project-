import pandas as pd
from datetime import datetime

FESTIVALS = [
    {"name":"Chinese New Year",    "dates":["2024-02-10","2024-02-11","2025-01-29","2025-01-30","2026-02-17","2026-02-18"], "boost":2.5,"icon":"🧧"},
    {"name":"Hari Raya Aidilfitri","dates":["2024-04-10","2024-04-11","2025-03-31","2025-04-01","2026-03-20","2026-03-21"], "boost":3.0,"icon":"🌙"},
    {"name":"Hari Raya Aidiladha", "dates":["2024-06-17","2024-06-18","2025-06-07","2025-06-08","2026-05-27","2026-05-28"], "boost":2.0,"icon":"🐑"},
    {"name":"Deepavali",           "dates":["2024-10-31","2024-11-01","2025-10-20","2025-10-21","2026-11-08","2026-11-09"], "boost":2.2,"icon":"🪔"},
    {"name":"Christmas",           "dates":["2024-12-25","2024-12-26","2025-12-25","2025-12-26","2026-12-25","2026-12-26"], "boost":1.8,"icon":"🎄"},
    {"name":"New Year",            "dates":["2024-01-01","2025-01-01","2026-01-01"],                                        "boost":1.6,"icon":"🎆"},
    {"name":"Merdeka Day",         "dates":["2024-08-31","2025-08-31","2026-08-31"],                                        "boost":1.5,"icon":"🇲🇾"},
    {"name":"Malaysia Day",        "dates":["2024-09-16","2025-09-16","2026-09-16"],                                        "boost":1.5,"icon":"🇲🇾"},
]

FESTIVAL_INCREASES = {
    "Normal Period": 0.00,
    "Hari Raya Aidilfitri": 0.80,
    "Deepavali": 0.70,
    "Chinese New Year": 0.98,
    "Christmas": 0.45,
    "New Year": 0.35,
}

FESTIVAL_MAP = {}
for f in FESTIVALS:
    for d in f["dates"]:
        FESTIVAL_MAP[d] = {"name":f["name"],"boost":f["boost"],"icon":f["icon"]}

def get_festival_percentage(name):
    return float(FESTIVAL_INCREASES.get(name, 0.0))

def get_festival_names():
    return list(FESTIVAL_INCREASES.keys())

def get_festival_boost(date_str):
    if date_str in FESTIVAL_MAP:
        f = FESTIVAL_MAP[date_str]
        return f["name"], f["boost"], f["icon"]
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    for days_before in range(1, 8):
        check = (dt - pd.Timedelta(days=days_before)).strftime("%Y-%m-%d")
        if check in FESTIVAL_MAP:
            f = FESTIVAL_MAP[check]
            surge = 1 + (f["boost"]-1)*(1-days_before/8)
            return f"{f['name']} (Pre-festival)", round(surge,2), f["icon"]
    return None, 1.0, None

def get_upcoming_festivals(days=30):
    today = datetime.today()
    upcoming = []
    for date_str, info in FESTIVAL_MAP.items():
        festival_date = datetime.strptime(date_str, "%Y-%m-%d")
        diff = (festival_date - today).days
        if 0 <= diff <= days:
            upcoming.append({"Festival":f"{info['icon']} {info['name']}","Date":date_str,"Days Away":diff,"Demand Boost":f"{info['boost']}x"})
    return sorted(upcoming, key=lambda x: x["Days Away"])

def apply_festival_boost_to_forecast(forecast_df):
    forecast_df = forecast_df.copy()
    names, boosts, icons = [], [], []
    for _, row in forecast_df.iterrows():
        n, b, i = get_festival_boost(str(row['Date'])[:10])
        names.append(n if n else "-"); boosts.append(b); icons.append(i if i else "")
    forecast_df['Festival'] = names; forecast_df['Boost'] = boosts
    forecast_df['Adjusted_Qty'] = (forecast_df['Predicted_Qty'] * forecast_df['Boost']).astype(int)
    return forecast_df
