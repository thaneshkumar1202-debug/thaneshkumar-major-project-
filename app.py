import base64, datetime, hashlib, io, os, itertools, math
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from database import *

ROUTE_DISTANCES_FROM_KL = {
    'Shah Alam': 25,
    'Seremban': 65,
    'Melaka City': 145,
    'Ipoh': 200,
    'Kuantan': 250,
    'Johor Bahru': 330,
    'George Town': 350,
    'Alor Setar': 430,
    'Kota Bharu': 450,
    'Kuala Terengganu': 450,
    'Kangar': 480,
    'Kuching (flight)': 970,
    'Kota Kinabalu (flight)': 1627,
}
import recommendation_engine
import forecasting_engine
import festival_engine
import data_cleaning_engine

DIESEL_PRICE=2.15

DELIVERY_COLS=['ID','Schedule No','Internal PO','Customer','Contact Person','Customer Phone','Delivery Address','Truck No','Truck Type','Delivery Date','Estimated Arrival','Item','Quantity','Actual Quantity','Instructions','Driver','Driver Phone','Distance KM','Avg Speed (km/h)','Tank Capacity (L)','Fuel L/km','Tank Range (km)','Toll RM','Fuel Litres','Fuel Cost RM','Load KG','Utilization %','Status','Arrival Time','Completed Time','Verified By','Verification Status','Verification Note','Driver Notes','Created At','Truck ID','Load Volume m³','Assigned At']

st.set_page_config(page_title='Smart Demand Forecasting and Truck Allocation System',page_icon='🚛',layout='wide',initial_sidebar_state='expanded')
st.session_state.setdefault('dark_mode', False)
dark_mode = st.session_state.dark_mode
if dark_mode:
    page_bg = 'linear-gradient(135deg,#0b1224,#111827,#0f172a)'
    sidebar_bg = 'linear-gradient(160deg,#0f172a,#111827,#0b1224,#111827)'
    sidebar_text = '#e2e8f0'
    text_color = '#e2e8f0'
    secondary_text = '#94a3b8'
    card_bg = 'linear-gradient(145deg,#111827,#0f172a)'
    panel_bg = '#111827'
    panel_border = 'rgba(148,163,184,0.18)'
    panel_shadow = 'rgba(0,0,0,.25)'
    input_bg = 'rgba(255,255,255,0.08)'
    input_border = 'rgba(148,163,184,0.22)'
    table_header_bg = 'linear-gradient(90deg,#0f172a,#111827)'
    table_row_bg = 'rgba(148,163,184,.03)'
    table_text = '#cbd5e1'
    table_hover = 'rgba(37,99,235,.08)'
    notif_bg = 'linear-gradient(145deg,#111827,#0f172a)'
    notif_text = '#e2e8f0'
    access_text = '#e0f2fe'
    logo_border = 'rgba(148,163,184,0.2)'
    button_shadow = 'rgba(37,99,235,.35)'
    nav_text = '#e2e8f0'
    nav_text_shadow = '0 0 0 0'
    sidebar_button_bg = 'rgba(255,255,255,0.08)'
    sidebar_button_border = '1px solid rgba(148,163,184,0.22)'
    sidebar_button_hover = 'rgba(59,130,246,0.12)'
else:
    page_bg = 'linear-gradient(135deg,#eff6ff,#f8fafc,#ffffff)'
    sidebar_bg = 'linear-gradient(160deg,#e2e8ff,#dbeafe,#bfdbfe,#dbeafe)'
    sidebar_text = '#0f172a'
    text_color = '#0f172a'
    secondary_text = '#475569'
    card_bg = 'linear-gradient(145deg,#ffffff,#f8fafc)'
    panel_bg = '#ffffff'
    panel_border = 'rgba(148,163,184,0.15)'
    panel_shadow = 'rgba(15,23,42,.08)'
    input_bg = 'rgba(15,23,42,0.04)'
    input_border = 'rgba(148,163,184,0.18)'
    table_header_bg = 'linear-gradient(90deg,#e2e8ff,#dbeafe)'
    table_row_bg = '#f8fafc'
    table_text = '#0f172a'
    table_hover = 'rgba(37,99,235,.12)'
    notif_bg = 'linear-gradient(145deg,#ffffff,#f8fafc)'
    notif_text = '#0f172a'
    access_text = '#0f172a'
    logo_border = 'rgba(15,23,42,0.12)'
    button_shadow = 'rgba(37,99,235,.22)'
    nav_text = '#ffffff'
    nav_text_shadow = '0 0 2px rgba(0,0,0,0.8), 0 0 4px rgba(0,0,0,0.5)'
    sidebar_button_bg = 'linear-gradient(90deg,#2563eb,#3b82f6,#2563eb)'
    sidebar_button_border = '1px solid rgba(59,130,246,0.55)'
    sidebar_button_hover = 'linear-gradient(90deg,#1d4ed8,#2563eb)'
app_before = 'radial-gradient(circle,#2563eb,#0f172a 55%,transparent 75%)' if dark_mode else 'radial-gradient(circle,#60a5fa,#eff6ff 55%,transparent 75%)'
app_after = 'radial-gradient(circle,#0f172a,#111827 55%,transparent 75%)' if dark_mode else 'radial-gradient(circle,#dbeafe,#ffffff 55%,transparent 75%)'
css = f'''<style>
@keyframes bgFlow{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
@keyframes gradientText{{to{{background-position:300% center}}}}
@keyframes fadeInUp{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes fadeInRow{{from{{opacity:0;transform:translateX(-8px)}}to{{opacity:1;transform:translateX(0)}}}}
@keyframes pulseGlow{{0%,100%{{transform:scale(1);filter:brightness(1)}}50%{{transform:scale(1.07);filter:brightness(1.25)}}}}
@keyframes pulseBorder{{0%,100%{{border-left-color:#2563eb}}50%{{border-left-color:#22d3ee}}}}
@keyframes floatBlob{{0%,100%{{transform:translate(0,0) scale(1)}}33%{{transform:translate(30px,-20px) scale(1.08)}}66%{{transform:translate(-20px,25px) scale(.95)}}}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
*{{font-family:Inter,Arial,sans-serif}}#MainMenu,footer,header{{visibility:hidden}}
.stApp{{background:{page_bg};background-size:250% 250%;animation:bgFlow 28s ease infinite;color:{text_color}}}
.stApp::before,.stApp::after{{content:'';position:fixed;width:620px;height:620px;border-radius:50%;filter:blur(70px);opacity:.45;z-index:-1;pointer-events:none;animation:floatBlob 22s ease-in-out infinite}}
.stApp::before{{top:-160px;left:-140px;background:{app_before}}}
.stApp::after{{bottom:-180px;right:-140px;background:{app_after};animation-duration:28s}}
.block-container::before{{content:'';position:fixed;bottom:-140px;left:38%;width:560px;height:560px;border-radius:50%;filter:blur(80px);opacity:.28;z-index:-1;pointer-events:none;background:radial-gradient(circle,{panel_bg},{page_bg} 60%,transparent 75%);animation:floatBlob 30s ease-in-out infinite reverse}}
.block-container{{max-width:1600px;padding-top:1rem}}
[data-testid="stSidebar"]{{background:{sidebar_bg};background-size:300% 300%;animation:bgFlow 24s ease infinite;color:{sidebar_text}}}
[data-testid="stSidebar"] *{{color:{sidebar_text}!important}}
[data-testid="stSidebar"] button{{background:{sidebar_button_bg} !important;color:{nav_text} !important;border:{sidebar_button_border};border-radius:14px;padding:.8rem .9rem;margin-bottom:.65rem;transition:all .25s ease;box-shadow:0 10px 30px rgba(0,0,0,.14);font-weight:800;text-shadow:{nav_text_shadow} !important;}}
[data-testid="stSidebar"] button, [data-testid="stSidebar"] button *{{color:{nav_text} !important;text-shadow:{nav_text_shadow} !important;}}
[data-testid="stSidebar"] button:hover{{background:{sidebar_button_hover} !important;border-color:rgba(59,130,246,0.55);transform:translateY(-1px)}}
[data-testid="stSidebar"] button:focus-visible{{outline:2px solid rgba(37,99,235,.8);box-shadow:0 0 0 4px rgba(37,99,235,.15)}}
.stRadio{{display:flex;justify-content:flex-end;}}
.stRadio>div{{display:flex;align-items:center;gap:.35rem;background:rgba(255,255,255,.12);border:1px solid rgba(148,163,184,.3);border-radius:999px;padding:.35rem;}}
.stRadio input[type=radio]{{display:none;}}
.stRadio label{{display:flex;align-items:center;justify-content:center;min-width:80px;padding:.55rem 1rem;border-radius:999px;color:rgba(255,255,255,.85);font-weight:800;cursor:pointer;transition:all .22s ease;text-transform:none;}}
.stRadio label:nth-of-type(1), .stRadio label:nth-of-type(2){{background:rgba(255,255,255,.08);color:{secondary_text};}}
.stRadio input[type=radio]:checked+label{{background:linear-gradient(90deg,#60a5fa,#4f46e5);color:#fff;text-shadow:0 0 2px rgba(0,0,0,.7);box-shadow:0 12px 24px rgba(37,99,235,.18);}}
.stRadio label:hover{{background:rgba(255,255,255,.18);}}
[data-testid="stSidebar"] img.sidebar-logo{{width:300px;max-width:100%;border-radius:18px;border:1px solid {logo_border};box-shadow:0 24px 50px rgba(0,0,0,.18);margin-bottom:1rem;transition:transform .35s ease,filter .35s ease;}}
[data-testid="stSidebar"] img.sidebar-logo:hover{{transform:translateY(-4px) scale(1.04);filter:drop-shadow(0 24px 45px rgba(37,99,235,.3));}}
.brand-text{{font-size:1.7rem;font-weight:900;background:linear-gradient(90deg,#60a5fa,#4f46e5,#22d3ee);background-size:300% auto;-webkit-background-clip:text;background-clip:text;color:transparent;animation:gradientText 5s linear infinite}}
.title{{font-size:2rem;font-weight:900;display:inline-block;background:linear-gradient(90deg,{text_color},{secondary_text},#60a5fa);background-size:300% auto;-webkit-background-clip:text;background-clip:text;color:transparent;animation:gradientText 7s linear infinite}}
.subtitle{{color:{secondary_text};margin-bottom:1rem}}
.section{{font-size:1.05rem;font-weight:900;display:inline-block;position:relative;margin:1rem 0 .8rem;padding-bottom:6px;color:{text_color}}}
.section::after{{content:'';position:absolute;left:0;bottom:0;height:3px;width:100%;border-radius:3px;background:linear-gradient(90deg,#60a5fa,#3b82f6,#38bdf8);background-size:300% auto;animation:gradientText 4s linear infinite}}
.kpi{{position:relative;overflow:hidden;background:{card_bg};border:1px solid {panel_border};border-radius:22px;padding:1.05rem 1.1rem;box-shadow:0 12px 30px {panel_shadow};transition:transform .25s ease,box-shadow .25s ease;animation:fadeInUp .5s ease both;min-height:128px}}
.kpi::before{{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#22d3ee,#2563eb,#4f46e5);background-size:300% auto;animation:gradientText 4s linear infinite}}
.kpi:hover{{transform:translateY(-7px) scale(1.02);box-shadow:0 18px 36px rgba(0,0,0,.34)}}
.kpi .icon{{width:38px;height:38px;display:flex;align-items:center;justify-content:center;border-radius:12px;background:{panel_bg};font-size:1.15rem;margin-bottom:.55rem;box-shadow:inset 0 0 0 1px rgba(148,163,184,.2)}}
.kpi .value{{font-size:1.65rem;font-weight:900;color:{text_color};transition:color .2s ease}}
.kpi:hover .value{{color:#60a5fa}}
.kpi .label{{font-size:.72rem;color:{secondary_text};text-transform:uppercase;font-weight:800;margin-top:.4rem}}
.note{{background:{card_bg};border-left:4px solid #2563eb;padding:.8rem 1rem;border-radius:12px;animation:fadeInUp .4s ease both;color:{text_color}}}
.pod{{background:{card_bg};color:{text_color};padding:28px;border:1px solid {panel_border};font-family:Arial}}
.pod h2{{text-align:center;margin:0}}.pod-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.pod-box{{border:1px solid rgba(148,163,184,0.12);padding:10px}}.sig{{height:100px;border:1px solid rgba(148,163,184,0.12);margin-top:8px}}
.stButton>button,[data-testid="stFormSubmitButton"]>button{{background:linear-gradient(90deg,#2563eb,#4f46e5,#22d3ee);background-size:250% auto;background-position:0 0;color:white;border:0;border-radius:12px;font-weight:800;box-shadow:0 4px 18px {button_shadow};transition:transform .18s ease,box-shadow .18s ease,background-position .6s ease}}
.stButton>button:hover,[data-testid="stFormSubmitButton"]>button:hover{{background-position:100% 0;transform:translateY(-2px) scale(1.03);box-shadow:0 10px 28px rgba(37,99,235,.45)}}
.stButton>button:active,[data-testid="stFormSubmitButton"]>button:active{{transform:translateY(0) scale(.97)}}
div[data-testid="stMetric"]{{background:{card_bg};border-radius:14px;padding:.7rem .9rem;box-shadow:0 6px 18px {panel_shadow};transition:transform .2s ease,box-shadow .2s ease;animation:fadeInUp .45s ease both}}
div[data-testid="stMetric"]:hover{{transform:translateY(-5px);box-shadow:0 14px 28px {panel_shadow}}}
[data-testid="stProgress"]>div>div>div{{background:linear-gradient(90deg,#2563eb,#4f46e5,#22d3ee)!important;background-size:300% auto;animation:gradientText 3s linear infinite}}
.tbl-wrap{{overflow-x:auto;border-radius:14px;border:1px solid {panel_border};margin-bottom:1.1rem;box-shadow:0 8px 22px {panel_shadow};animation:fadeInUp .45s ease both}}
.vtable{{width:100%;border-collapse:collapse;font-size:.88rem;background:{panel_bg}}}
.vtable thead th{{background:{table_header_bg};background-size:200% auto;animation:gradientText 8s linear infinite;color:{text_color};padding:11px 14px;text-align:left;font-weight:800;font-size:.74rem;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}}
.vtable tbody tr{{animation:fadeInRow .35s ease both;transition:transform .15s ease}}
.vtable tbody td{{padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.08);color:{table_text};white-space:nowrap}}
.vtable tbody tr:nth-child(even){{background:{table_row_bg}}}
.vtable tbody tr:hover{{background:{table_hover};transform:scale(1.008)}}
.badge{{padding:3px 11px;border-radius:999px;font-weight:800;font-size:.74rem;white-space:nowrap;display:inline-block;border:1px solid;transition:transform .15s ease}}
.badge:hover{{transform:scale(1.08)}}
.badge-pulse{{animation:pulseGlow 1.7s ease-in-out infinite}}
.login-title{{font-size:2.5rem;font-weight:900;text-align:center;margin:.7rem 0 .25rem;line-height:1.15;background:linear-gradient(90deg,#60a5fa,#4f46e5,#22d3ee);background-size:300% auto;-webkit-background-clip:text;background-clip:text;color:transparent;animation:gradientText 5s linear infinite}}
.login-sub{{font-size:1.05rem;color:{secondary_text}!important;text-align:center;margin-bottom:1.3rem;font-weight:600}}
.notif-card{{background:{notif_bg};border-left:5px solid #2563eb;border-radius:12px;padding:.85rem 1.05rem;margin-bottom:.65rem;box-shadow:0 4px 14px {panel_shadow};transition:transform .2s ease,box-shadow .2s ease;animation:fadeInUp .4s ease both}}
.notif-card:hover{{transform:translateX(5px);box-shadow:0 10px 22px {panel_shadow}}}
.notif-unread{{border-left-color:#2563eb;background:rgba(37,99,235,.1);animation:fadeInUp .4s ease both,pulseBorder 2.2s ease-in-out infinite}}
.notif-title{{font-weight:800;color:{notif_text}}}
.notif-time{{font-size:.74rem;color:{secondary_text}}}
.truck-card{{background:{card_bg};border:1px solid rgba(148,163,184,0.14);border-radius:20px;padding:12px;box-shadow:0 10px 28px {panel_shadow};margin-bottom:12px}}
.truck-card .plate{{font-size:1.12rem;font-weight:900;color:{text_color};margin-top:4px}}.truck-card .meta{{color:{secondary_text};font-size:.86rem;line-height:1.55}}.truck-card .cap{{font-weight:800;color:#60a5fa}}
.truck-photo-wrapper{{background:#ffffff;border-radius:18px;padding:12px;display:flex;justify-content:center;align-items:center;box-shadow:0 12px 32px rgba(15,23,42,.08);margin-bottom:1rem;}}
.truck-photo{{width:100%;height:auto;max-height:220px;object-fit:contain;border-radius:14px;}}
.access-banner{{background:linear-gradient(90deg,{panel_bg},{card_bg});border:1px solid rgba(37,99,235,.3);border-left:5px solid #2563eb;padding:.85rem 1rem;border-radius:14px;margin:.2rem 0 1rem;color:{access_text};font-weight:650}}
    @media print {{
      [data-testid="stSidebar"], #MainMenu, footer, button, .stButton, [data-testid="stFormSubmitButton"], .css-1sqrs0k, .stRadio, .stSelectbox, .stTextInput, .stTextArea, nav, .stAlert, .stText, .stMarkdown, .stMetric, .stButton>button {{display:none !important;}}
      .block-container {{padding:0 !important;max-width:none !important;}}
      .pod {{box-shadow:none !important;border:none !important;background:#fff !important;}}
      .pod-grid {{grid-template-columns:1fr !important;gap:0 !important;}}
      .pod-box {{border:none !important;padding:0 !important;margin-bottom:16px !important;}}
      .sig {{border:1px solid #000 !important;}}
      body {{background:#fff !important;color:#000 !important;}}
    }}</style>'''
st.markdown(css,unsafe_allow_html=True)

STATUS_COLORS={
    'Available':'#16a34a','Stock Ready':'#16a34a','Ready':'#16a34a','Delivered':'#16a34a','Verified':'#16a34a','Completed':'#16a34a','No Order Needed':'#16a34a','Active':'#16a34a',
    'Assigned':'#d97706','Loading':'#d97706','On Route':'#d97706','Pending':'#d97706','Order Soon':'#d97706','Waiting Verification':'#d97706','Standby':'#d97706',
    'Critical':'#dc2626','Rejected':'#dc2626','Late':'#dc2626','Order Now':'#dc2626',
    'Allocated':'#2563eb','Arrived':'#2563eb',
    'Maintenance':'#6b7280',
}

ADMIN_ROLES={'Super Admin'}
def is_admin(): return st.session_state.get('user_role') in ADMIN_ROLES
def can_manage_sales_data(): return st.session_state.get('user_role') in {'Purchasing Staff','Super Admin'}
def role_is(*roles): return st.session_state.get('user_role') in roles or is_admin()
def active_dataset_path():
    p=Path('data/cleaned_data.csv')
    return p if p.exists() and p.stat().st_size>0 else None
def dataset_ready(): return active_dataset_path() is not None

def active_dataset_signature():
    """Return a content fingerprint so cached model results follow the active file."""
    path=active_dataset_path()
    if path is None: return None
    digest=hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()

def clear_model_cache():
    try: _get_model_evaluation_for_signature.clear()
    except Exception: pass
    try: forecasting_engine.reset_model()
    except Exception: pass

def reset_viva_demo():
    """Start a clean viva demonstration while keeping fixed master data such as trucks."""
    reset_demo_operational_data()
    for path in [Path('data/cleaned_data.csv'), Path('data/cleaned_data_backup.csv'), Path('models/random_forest_model.pkl')]:
        try:
            if path.exists(): path.unlink()
        except OSError:
            pass
    clear_model_cache()


def render_dataset_required_banner():
    st.error('🚫 Sales dataset required: forecasting, festival planning and smart truck allocation cannot run until Purchasing uploads, cleans, validates and activates a dataset.')
    st.info('Truck and driver master details remain available because they are fixed fleet records. Use Sales Data Management to inject a dataset for this viva session.')
KPI_ICONS={'Available Trucks':'✅','Assigned Trucks':'🚚','Trucks in Maintenance':'🛠️','Pending Deliveries':'⏱️','Total Insourced Deliveries':'📦','Total Fuel Usage':'⛽','Total Toll Cost':'🛣️','Diesel Price':'💳','Products in Dataset':'📦','Sales Qty in Dataset':'📈','Current Stock Level':'🏷️','Pending Requests':'🧾'}
def kpi(v,l): return f'<div class="kpi"><div class="icon">{KPI_ICONS.get(l,"◆")}</div><div class="value">{v}</div><div class="label">{l}</div></div>'
def header(t,s):
    c1,c2=st.columns([9,3])
    with c1:
        st.markdown(f'<div class="title">{t}</div><div class="subtitle">{s}</div>',unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div style="text-align:right;color:{secondary_text};font-weight:700;margin-bottom:.25rem">Theme</div>',unsafe_allow_html=True)
        theme_choice = st.radio('', ['Light', 'Dark'], index=1 if st.session_state.dark_mode else 0, horizontal=True, key='theme_toggle', label_visibility='collapsed')
        st.session_state.dark_mode = (theme_choice == 'Dark')

URGENT_STATUSES={'Critical','Order Now','Late','Rejected'}
def badge(v):
    s=str(v) if v not in (None,'') else '—'
    c=STATUS_COLORS.get(s.strip())
    if c:
        cls='badge badge-pulse' if s.strip() in URGENT_STATUSES else 'badge'
        return f'<span class="{cls}" style="background:{c}1a;color:{c};border-color:{c}55">{s}</span>'
    return s

def render_table(df,status_cols=None):
    if df.empty: st.info('No records yet.'); return
    status_cols = status_cols if status_cols is not None else [c for c in df.columns if 'status' in c.lower() or c.lower()=='urgency']
    disp=df.copy()
    for c in status_cols:
        if c in disp.columns: disp[c]=disp[c].apply(badge)
    head=''.join(f'<th>{c}</th>' for c in disp.columns)
    body=''
    for _,row in disp.iterrows():
        body+='<tr>'+''.join(f'<td>{row[c] if pd.notna(row[c]) else "—"}</td>' for c in disp.columns)+'</tr>'
    st.markdown(f'<div class="tbl-wrap"><table class="vtable"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',unsafe_allow_html=True)

def table(rows,cols,display_drop=None,status_cols=None):
    df=pd.DataFrame(rows,columns=cols)
    view=df.drop(columns=display_drop) if display_drop and not df.empty else df
    render_table(view,status_cols)
    return df

def logo_b64():
    p=Path('images/vilvam_logo.png')
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ''

@st.cache_resource(show_spinner=False)
def _get_model_evaluation_for_signature(dataset_signature):
    path=active_dataset_path()
    if path is None: raise FileNotFoundError('Purchasing has not uploaded and activated a sales dataset yet.')
    if active_dataset_signature()!=dataset_signature:
        raise RuntimeError('The active sales dataset changed while the forecast model was loading. Please retry.')
    data=pd.read_csv(path)
    result=forecasting_engine.evaluate_model(data)
    rename={'Product_Code':'Product','Category_Code':'Category','Day_Code':'Day of Week','Is_Weekend':'Weekend','Is_Promotion':'Promotion','Stock_Level':'Stock Level','Month':'Month','Year':'Year','Unit_Weight_kg':'Unit Weight','Unit_Volume_m3':'Unit Volume'}
    imp=result['feature_importance'].copy(); imp['Feature']=imp['Feature'].map(rename).fillna(imp['Feature']); imp=imp.sort_values('Importance',ascending=True)
    result['feature_importance']=imp
    return result,data

def get_model_evaluation():
    signature=active_dataset_signature()
    if signature is None:
        raise FileNotFoundError('Purchasing has not uploaded and activated a sales dataset yet.')
    return _get_model_evaluation_for_signature(signature)

def run_notification_scan():
    refresh_system_notifications(include_stock=dataset_ready())
    if not dataset_ready():
        return
    try:
        for r in recommendation_engine.recommend_stock_orders(get_stock_items()):
            if r['urgency'] in ('Critical','Order Now') and r['suggested_order_qty']>0:
                notify('Purchasing Staff',f"Forecast demand risk: {r['item']}",f"Suggested order {r['suggested_order_qty']} {r['unit']} ({r['urgency']}). {r['reason']}")
    except Exception:
        pass

def login():
    login_bg=Path('images/unloading-cargo-truck-warehouse-building-39493908.webp')
    bg_data='' 
    if login_bg.exists():
        bg_data=base64.b64encode(login_bg.read_bytes()).decode()
        bg_data=f'data:image/webp;base64,{bg_data}'
    st.markdown(f'''<style>
    .stApp{{background:linear-gradient(rgba(255,255,255,.78),rgba(255,255,255,.78)),url("{bg_data}") center/cover no-repeat!important;animation:none!important}}
    .login-sub{{color:#94a3b8!important}}.login-title{{background:linear-gradient(90deg,#60a5fa,#4f46e5,#22d3ee);background-size:250% auto;-webkit-background-clip:text;background-clip:text;color:transparent}}
    div[data-testid="stTextInput"] label{{color:#0f172a!important}}
    </style>''',unsafe_allow_html=True)
    _,m,_=st.columns([1,1.1,1])
    with m:
        logo=Path('images/vilvam_logo.png')
        if logo.exists(): st.image(str(logo),use_container_width=True)
        st.markdown('<div class="login-title">Smart Demand Forecasting and<br>Truck Allocation System</div><div class="login-sub">Sign in to continue</div>',unsafe_allow_html=True)
        with st.form('login'):
            e=st.text_input('Email'); p=st.text_input('Password',type='password')
            if st.form_submit_button('Login',use_container_width=True):
                u=verify_user(e,p)
                if u:
                    # Shared operational state must survive different browser/user sessions.
                    # Only the explicit Super Admin reset is allowed to clear active data.
                    st.session_state.update(logged_in=True,user_name=u[0],user_role=u[1],page='Dashboard',missing_dataset_notified=False)
                    st.rerun()
                st.error('Invalid email or password.')
        st.info('Purchasing: purchase@vilvam.com / purchase123\n\nLogistics: logistics@vilvam.com / logistics123\n\nAdmin (technical backup): admin@vilvam.com / admin123')

def sidebar():
    with st.sidebar:
        unread=get_unread_notification_count(st.session_state.user_role)
        logo=Path('images/vilvam_logo-navigation bar-preview.png')
        if logo.exists(): st.image(str(logo), width=320, caption='', clamp=False)
        st.markdown(f'<div style="color:{sidebar_text};font-weight:900;margin-top:.35rem;margin-bottom:.35rem;font-size:1.05rem">{st.session_state.user_name}</div><div style="color:{secondary_text};font-size:.85rem;margin-bottom:1.2rem">{st.session_state.user_role}</div>',unsafe_allow_html=True)
        pages=[('Dashboard','📊'),('Notifications','🔔'),('Sales Dataset','👁️')]
        if role_is('Purchasing Staff'): pages += [('Stock Management','📦'),('Customer Management','🏢'),('Purchase Requests','🧾'),('Smart Reorder Recommendation','🎯')]
        if can_manage_sales_data(): pages += [('Sales Data Management','⬆️')]
        if role_is('Logistics Staff'): pages += [('Forecasting','📈'),('Festival Planning','🎉'),('Smart Truck Allocation','🧠'),('Truck Management','🚛'),('Delivery Schedule','📅'),('Printable POD','🖨️'),('Delivery Verification','✅'),('Reports','📑'),('Request Approval','👍'),('Stock View','👁️')]
        if is_admin(): pages += [('Admin','👥')]
        for p,i in pages:
            label=f'{i} {p}'
            if p=='Notifications' and unread: label+=f' ({unread})'
            if st.button(label,key='nav'+p,use_container_width=True): st.session_state.page=p; st.rerun()
        if is_admin() and st.button('🔄 Reset Viva Demo',use_container_width=True):
            reset_viva_demo()
            st.session_state.page='Dashboard'
            st.session_state.missing_dataset_notified=False
            st.success('Temporary sales, forecasting and delivery data were cleared. Fixed truck master details were kept.')
            st.rerun()
        if st.button('Logout',use_container_width=True): st.session_state.update(logged_in=False,user_name='',user_role='',page='Dashboard',missing_dataset_notified=False); st.rerun()

def semi_gauge(value,title,detail):
    bar_color='#dc2626' if value<40 else '#f59e0b' if value<70 else '#16a34a'
    fig=go.Figure(go.Indicator(mode='gauge+number',value=value,number={'suffix':'%','font':{'color':bar_color}},title={'text':f'<b>{title}</b><br><span style="font-size:12px">{detail}</span>'},gauge={'shape':'angular','axis':{'range':[0,100]},'bar':{'color':bar_color},'bgcolor':'white','borderwidth':0,'steps':[{'range':[0,40],'color':'#fee2e2'},{'range':[40,70],'color':'#fef3c7'},{'range':[70,100],'color':'#dcfce7'}],'threshold':{'line':{'color':bar_color,'width':3},'thickness':.85,'value':value}})); fig.update_layout(height=260,margin=dict(l=20,r=20,t=55,b=5),transition={'duration':600,'easing':'cubic-in-out'}); st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})

SPARK_PALETTE=['#f97316','#8b5cf6','#06b6d4','#ec4899','#16a34a']
def hex_to_rgba(h,a=.2):
    h=h.lstrip('#'); r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    return f'rgba({r},{g},{b},{a})'
def sparkline(df,x,y,title,suffix='',color=None):
    c=color or SPARK_PALETTE[abs(hash(title))%len(SPARK_PALETTE)]
    fig=go.Figure(go.Scatter(x=df[x],y=df[y],mode='lines+markers',fill='tozeroy',line={'color':c,'width':3,'shape':'spline'},marker={'color':c,'size':7,'line':{'color':'white','width':1}},fillcolor=hex_to_rgba(c,.2),hovertemplate=f'%{{x}}<br>%{{y}}{suffix}<extra></extra>'))
    fig.update_layout(title=title,height=210,margin=dict(l=25,r=15,t=50,b=25),showlegend=False,xaxis=dict(showgrid=False),yaxis=dict(showgrid=False),transition={'duration':500,'easing':'cubic-in-out'},plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})

@st.fragment(run_every='1s')
def demo_delivery_timer_fragment(delivery_id):
    """Live 60-second viva stopwatch; zero automatically moves the route to Delivered."""
    timer=get_demo_delivery_timer(delivery_id)
    if not timer or timer.get('demo_due_at') is None or timer.get('status')!='On Route':
        return
    now=datetime.datetime.now().timestamp()
    remaining=max(0.0,float(timer['demo_due_at'])-now)
    started=float(timer.get('demo_started_at') or now)
    duration=max(1.0,float(timer['demo_due_at'])-started)
    elapsed=min(duration,max(0.0,duration-remaining))
    pct=elapsed/duration*100
    fig=go.Figure(go.Pie(
        values=[max(pct,0.001),max(100-pct,0.001)],
        hole=.72,sort=False,direction='clockwise',rotation=0,
        marker=dict(colors=['#2563eb','#e2e8f0'],line=dict(color='#0f172a',width=3)),
        textinfo='none',hoverinfo='skip'
    ))
    fig.add_annotation(text=f'<b>{math.ceil(remaining)}s</b><br><span style="font-size:12px">ON ROUTE</span>',x=.5,y=.5,showarrow=False,font=dict(size=24,color='#0f172a'))
    fig.update_layout(title=f"⏱️ 1-Minute Demo Trip — {timer['schedule_no']}",height=330,margin=dict(l=30,r=30,t=60,b=20),showlegend=False,paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False},key=f'demo_timer_{delivery_id}')
    st.progress(min(1.0,elapsed/duration)); st.caption(f"Truck is On Route • {math.ceil(remaining)} second(s) remaining • At 0 seconds the delivery automatically changes to Delivered.")
    if remaining<=0 and complete_demo_delivery_if_due(delivery_id):
        st.session_state.delivery_arrived_popup=timer['schedule_no']
        st.rerun(scope='app')

@st.dialog('🚚 Delivery Arrived')
def delivery_arrived_dialog(schedule_no):
    st.markdown("<div style='text-align:center;font-size:30px;font-weight:800;color:#16a34a;margin:8px 0 12px'>Goods delivered on time!</div>",unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center;font-size:16px'><b>{schedule_no}</b><br><br>The trip has finished successfully.</div>",unsafe_allow_html=True)
    st.info('Status: Delivered / Waiting Verification. The delivery is hidden from the active schedule and is now ready for management verification.')
    if st.button('Continue to Verification',use_container_width=True,type='primary'):
        st.session_state.page='Delivery Verification'
        st.rerun()

@st.dialog('✅ Delivery Complete')
def delivery_complete_dialog(schedule_no,customer):
    st.markdown("<div style='text-align:center;font-size:28px;font-weight:800;color:#16a34a;margin:8px 0 12px'>Goods delivered on time!</div>",unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center;font-size:16px'><b>{schedule_no}</b><br>{customer}<br><br>The delivery is verified and complete. The truck is now Available.</div>",unsafe_allow_html=True)
    st.caption('This completed record is removed from the active Delivery Schedule list and remains available in Reports/history.')
    if st.button('Done',use_container_width=True,type='primary'):
        st.rerun()

def dashboard():
    header('Dashboard',f'Operational overview for {st.session_state.user_role}.')
    if role_is('Purchasing Staff') and not role_is('Logistics Staff'):
        if not dataset_ready():
            st.markdown('<div class="access-banner">⚠️ Waiting for Purchasing sales dataset. Dashboard KPIs are not calculated until a valid dataset is uploaded, processed and activated.</div>',unsafe_allow_html=True)
            st.info('No live sales/stock KPI values are shown here yet. This prevents old or demo stock records from appearing as current Purchasing results.')
            if can_manage_sales_data() and st.button('Open Sales Data Management',use_container_width=True):
                st.session_state.page='Sales Data Management'; st.rerun()
            return
        try:
            active=pd.read_csv(active_dataset_path())
            ds_summary,stock_snapshot=data_cleaning_engine.build_sales_dashboard_summary(active)
        except Exception as exc:
            st.error(f'Unable to build the Purchasing dashboard from the active dataset: {exc}')
            return
        pending=get_dashboard_summary()['pending_requests']
        cols=st.columns(4)
        vals=[ds_summary['products'],f"{ds_summary['total_sales_qty']:,.0f}",f"{ds_summary['current_stock_level']:,.0f}",pending]
        labs=['Products in Dataset','Sales Qty in Dataset','Current Stock Level','Pending Requests']
        for c,v,l in zip(cols,vals,labs): c.markdown(kpi(v,l),unsafe_allow_html=True)
        st.caption(f"Active Purchasing dataset • {ds_summary['rows']:,} records • latest sales date {ds_summary['latest_sales_date']}")
        display_cols=['Date','Product','Category','Quantity_Sold','Stock_Level','Unit_Weight_kg','Unit_Volume_m3']
        display_cols=[c for c in display_cols if c in stock_snapshot.columns]
        view=stock_snapshot[display_cols].rename(columns={'Quantity_Sold':'Latest Sales Qty','Stock_Level':'Current Stock Level','Unit_Weight_kg':'Unit Weight (kg)','Unit_Volume_m3':'Unit Volume (m³)'})
        st.markdown('<div class="section">Latest Product Stock from Active Dataset</div>',unsafe_allow_html=True)
        st.dataframe(view,use_container_width=True,hide_index=True)
        return

    s=get_dashboard_summary()
    if st.session_state.user_role=='Logistics Staff' and not dataset_ready():
        st.markdown('<div class="access-banner">⚠️ Forecasting is waiting for Purchasing. No active sales dataset has been uploaded yet. Truck, driver, fuel and fleet-status information remains available below.</div>',unsafe_allow_html=True)
    vals=[s['available_trucks'],s['assigned_trucks'],s['on_route_trucks'],s['maintenance_trucks'],s['pending_deliveries'],s['total_insourced_deliveries'],f"{s['fuel_litres']:.2f} L",f"RM {s['toll_cost']:.2f}",f'RM {DIESEL_PRICE:.2f}/L']
    labs=['Available Trucks','Assigned / Active Trucks','On Route Trucks','Trucks in Maintenance','Pending Deliveries','Total Insourced Deliveries','Active Fuel Usage','Active Toll Cost','Diesel Price']
    for row in [range(0,3),range(3,6),range(6,9)]:
        cols=st.columns(3)
        for c,i in zip(cols,row): c.markdown(kpi(vals[i],labs[i]),unsafe_allow_html=True)
    all_vals=[f"{s['fuel_litres_all_time']:.2f} L",f"RM {s['fuel_cost_all_time']:.2f}",f"RM {s['toll_cost_all_time']:.2f}",s['total_insourced_deliveries']]
    all_labs=['All-time Fuel Usage','All-time Fuel Cost','All-time Toll Cost','Total Deliveries']
    st.markdown('<div class="section">Lifetime Delivery KPIs</div>',unsafe_allow_html=True)
    cols=st.columns(4)
    for c,v,l in zip(cols,all_vals,all_labs): c.markdown(kpi(v,l),unsafe_allow_html=True)
    st.markdown('<div class="section">Fleet Availability</div>',unsafe_allow_html=True)
    c1,c2=st.columns(2); total=max(1,s['available_trucks']+s['assigned_trucks']+s['maintenance_trucks'])
    with c1: semi_gauge(s['available_trucks']/total*100,'Fleet Availability',f"{s['available_trucks']} of {total} trucks ready")
    with c2:
        d=pd.DataFrame({'Status':['Available','Assigned','Maintenance'],'Trucks':[s['available_trucks'],s['assigned_trucks'],s['maintenance_trucks']]}); fig=px.pie(d,names='Status',values='Trucks',hole=.62,title='Truck Status'); fig.update_layout(height=270,margin=dict(l=10,r=10,t=55,b=10)); st.plotly_chart(fig,use_container_width=True)
        if st.button('Open Truck Management',use_container_width=True): st.session_state.page='Truck Management'; st.rerun()
    metrics=pd.DataFrame(get_monthly_delivery_metrics(),columns=['Month','Deliveries','Fuel','Toll'])
    if not metrics.empty:
        a,b,c=st.columns(3)
        with a: sparkline(metrics,'Month','Deliveries','Monthly Delivery Trend')
        with b: sparkline(metrics,'Month','Fuel','Fuel Usage Trend',' L')
        with c: sparkline(metrics,'Month','Toll','Toll Cost Trend',' RM')
    st.markdown('<div class="section">Driver Information</div>',unsafe_allow_html=True)
    drivers=get_driver_information()
    if drivers:
        table(drivers,['Driver','Phone','Truck','Delivery Status','Latest Delivery'],None,['Delivery Status'])
    else:
        st.info('No driver assignment records yet. Truck information is still available in Truck Management.')
    st.markdown('<div class="section">Forecast & Delivery Insights</div>',unsafe_allow_html=True)
    if not dataset_ready():
        st.info('Forecast KPIs are locked until the Purchasing Department uploads and activates the sales dataset.')
        return
    try:
        result,active_data=get_model_evaluation()
        st.markdown('<div class="section">Current Active Sales Dataset</div>',unsafe_allow_html=True)
        ds1,ds2,ds3,ds4=st.columns(4)
        ds1.metric('Dataset Rows',f'{len(active_data):,}')
        ds2.metric('Products',f"{active_data['Product'].nunique():,}")
        ds3.metric('Total Sales Qty',f"{active_data['Quantity_Sold'].sum():,.0f}")
        ds4.metric('Latest Sales Date',str(active_data['Date'].max()))
        d1,d2,d3=st.columns(3)
        with d1:
            pred=result['predictions'].reset_index(drop=True).head(40)
            fig=go.Figure(); fig.add_trace(go.Scatter(y=pred['Actual Sales'],name='Actual',mode='lines',hovertemplate='Actual: %{y}<extra></extra>')); fig.add_trace(go.Scatter(y=pred['Predicted Sales'],name='Predicted',mode='lines',line={'dash':'dot'},hovertemplate='Predicted: %{y}<extra></extra>')); fig.update_layout(title='Actual vs Predicted Sales',height=260,margin=dict(l=20,r=10,t=45,b=20)); st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
        with d2:
            imp=result['feature_importance'].tail(6); fig=px.bar(imp,x='Importance',y='Feature',orientation='h',title='Feature Importance',hover_data={'Importance':':.1f'}); fig.update_layout(height=260,margin=dict(l=10,r=10,t=45,b=20)); st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
        with d3:
            drows=get_delivery_schedules()
            if drows:
                ddf=pd.DataFrame(drows,columns=DELIVERY_COLS); dstat=ddf.Status.value_counts().rename_axis('Status').reset_index(name='Count'); fig=px.pie(dstat,names='Status',values='Count',hole=.55,title='Delivery Status'); fig.update_layout(height=260,margin=dict(l=10,r=10,t=45,b=20)); st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
            else: st.info('No deliveries yet.')
    except Exception as e:
        st.caption(f'Forecast insights unavailable: {e}')
    nav=st.columns(3)
    if nav[0].button('Available Trucks → Truck Management',use_container_width=True): st.session_state.page='Truck Management'; st.rerun()
    if nav[1].button('Pending Deliveries → Delivery Schedule',use_container_width=True): st.session_state.page='Delivery Schedule'; st.rerun()
    if nav[2].button('Pending Requests → Request Approval',use_container_width=True): st.session_state.page='Request Approval'; st.rerun()

def stock(readonly=False):
    header('Stock View' if readonly else 'Stock Management','Stock status follows Critical → Stock Ready → Standby → Allocated → Delivered.')
    rows=get_stock_items(); df=table(rows,['ID','Item','Category','Quantity','Unit','Daily Usage','Reorder Level','Supplier','Days Remaining','Stock Status'],['ID'],['Stock Status'])
    if readonly:return
    opts={f'{r[1]} ({r[3]} {r[4]})':r[0] for r in rows}; c1,c2=st.columns(2); item=c1.selectbox('Stock Item',list(opts)); q=c2.number_input('New Quantity',min_value=0,step=1)
    if st.button('Update Stock'): update_stock_quantity(opts[item],q); st.success('Updated.'); st.rerun()
    low=get_low_stock_items() or rows
    with st.form('req'):
        ro={f'{r[1]} — {r[8]} days remaining':r[0] for r in low}; sel=st.selectbox('Low-stock item',list(ro)); qty=st.number_input('Requested quantity',1,10000,100,10); weight=st.number_input('Estimated load kg',1.0,50000.0,100.0,10.0); reason=st.text_area('Reason')
        if st.form_submit_button('Create Purchase Request'): st.success(f'{create_purchase_request(ro[sel],qty,weight,reason,st.session_state.user_name)} created.')

def reorder_recommendation():
    header('Smart Reorder Recommendation','Compares current stock, actual usage, predicted demand and safety stock to suggest what to order next.')
    recs=recommendation_engine.recommend_stock_orders(get_stock_items())
    if not recs: st.info('No stock items to evaluate.'); return
    order={'Critical':0,'Order Now':1,'Order Soon':2,'No Order Needed':3}
    recs=sorted(recs,key=lambda r:order.get(r['urgency'],9))
    df=pd.DataFrame(recs)
    view=df.rename(columns={'item':'Item','category':'Category','current_stock':'Current Stock','unit':'Unit','actual_daily_usage':'Actual Daily Usage','predicted_daily_usage':'Predicted Daily Usage','predicted_demand':'Predicted Demand','safety_stock':'Safety Stock','reorder_level':'Reorder Level','days_remaining':'Days Remaining','suggested_order_qty':'Suggested Qty','urgency':'Urgency','supplier':'Supplier','reason':'Reason'})
    view=view[['Item','Category','Current Stock','Unit','Actual Daily Usage','Predicted Daily Usage','Predicted Demand','Safety Stock','Reorder Level','Days Remaining','Suggested Qty','Urgency','Supplier','Reason']]
    render_table(view,status_cols=['Urgency'])
    st.markdown('<div class="section">Create Purchase Request from Recommendation</div>',unsafe_allow_html=True)
    actionable=[r for r in recs if r['suggested_order_qty']>0]
    if not actionable: st.success('No reorder needed right now.'); return
    opts={f"{r['item']} — suggest {r['suggested_order_qty']} {r['unit']} ({r['urgency']})":r for r in actionable}
    sel=st.selectbox('Item',list(opts)); rec=opts[sel]; st.caption(rec['reason'])
    c1,c2=st.columns(2); qty=c1.number_input('Requested Quantity',1,100000,int(rec['suggested_order_qty'])); weight=c2.number_input('Estimated Load KG',1.0,50000.0,float(max(1,rec['suggested_order_qty'])))
    if st.button('Create Purchase Request from Recommendation'):
        no=create_purchase_request(rec['item_id'],qty,weight,f"Auto-suggested ({rec['urgency']}): {rec['reason']}",st.session_state.user_name)
        st.success(f'{no} created.'); st.rerun()

def notifications_page():
    header('Notifications','Low stock, approvals, delivery and forecast alerts for your role.')
    rows=get_notifications(st.session_state.user_role)
    if not rows: st.success('No notifications.'); return
    if st.button('Mark all as read'): mark_all_notifications_read(st.session_state.user_role); st.rerun()
    for i,role,title,message,is_read,created in rows:
        cls='notif-card' if is_read else 'notif-card notif-unread'
        st.markdown(f'<div class="{cls}"><div class="notif-title">{title}</div><div class="notif-time">{created}</div><div>{message}</div></div>',unsafe_allow_html=True)
        if not is_read:
            if st.button('Mark read',key=f'read{i}'): mark_notification_read(i); st.rerun()

def customers():
    header('Customer Management','Purchasing maintains customer details used automatically by Logistics.')
    rows=get_customers(); table(rows,['ID','Code','Customer','Contact Person','Phone','Email','Address','Distance KM','Status'],['ID'],['Status'])
    with st.form('customer',clear_on_submit=True):
        a,b=st.columns(2); code=a.text_input('Customer Code'); name=b.text_input('Customer Name'); c,d=st.columns(2); contact=c.text_input('Contact Person'); phone=d.text_input('Phone'); email=st.text_input('Email'); address=st.text_area('Delivery Address'); distance=st.number_input('Default Round-trip Distance (KM)',0.0,2000.0,30.0)
        if st.form_submit_button('Save Customer'):
            if not code or not name: st.error('Customer Code and Customer Name are required.')
            else:
                try: create_customer(code,name,contact,phone,email,address,distance,st.session_state.user_name); st.success('Customer saved.'); st.rerun()
                except Exception as e:
                    st.error(f'That Customer Code "{code}" is already in use — please use a unique code.' if 'UNIQUE' in str(e) else str(e))

    st.markdown('<div class="section">📨 Quick Customer Sales Request</div>',unsafe_allow_html=True)
    st.caption('Record what the customer wants once. Logistics will receive the same customer, product, quantity, weight and volume automatically in Delivery Schedule.')
    if not dataset_ready():
        st.warning('Activate the Purchasing sales dataset first so products, unit weight and unit volume can be selected from the approved dataset.')
    else:
        try:
            active=pd.read_csv(active_dataset_path())
            product_meta=active.sort_values('Date').groupby('Product',as_index=False).tail(1).copy()
            if 'Unit_Weight_kg' not in product_meta: product_meta['Unit_Weight_kg']=1.0
            if 'Unit_Volume_m3' not in product_meta: product_meta['Unit_Volume_m3']=0.01
            product_meta['Unit_Weight_kg']=pd.to_numeric(product_meta['Unit_Weight_kg'],errors='coerce').fillna(1.0).clip(lower=.001)
            product_meta['Unit_Volume_m3']=pd.to_numeric(product_meta['Unit_Volume_m3'],errors='coerce').fillna(.01).clip(lower=.001)
            product_map={str(r.Product):r for _,r in product_meta.sort_values('Product').iterrows()}
            customer_map={f'{r[2]} — {r[1]}':r for r in rows if r[8]=='Active'}
            if not customer_map or not product_map:
                st.info('An active customer and at least one dataset product are required.')
            else:
                with st.container(border=True):
                    rc1,rc2=st.columns(2)
                    request_customer=rc1.selectbox('Customer requesting the goods',list(customer_map),key='sales_req_customer')
                    request_product=rc2.selectbox('Product required',list(product_map),key='sales_req_product')
                    request_qty=st.number_input('Requested Quantity',1.0,1000000.0,100.0,key='sales_req_qty')
                    meta=product_map[request_product]; uw=float(meta['Unit_Weight_kg']); uv=float(meta['Unit_Volume_m3'])
                    rm1,rm2=st.columns(2); rm1.metric('Dataset Unit Weight',f'{uw:g} kg'); rm2.metric('Dataset Unit Volume',f'{uv:g} m³')
                    company=customer_map[request_customer][2]
                    dummy_message=f'Customer {company} requested {request_qty:,.0f} unit(s) of {request_product}. Please arrange a suitable available truck for delivery.'
                    st.info(f'💬 Customer message: "{dummy_message}"')
                    if st.button('📨 Save Request & Send to Logistics',type='primary',use_container_width=True):
                        try:
                            no,_=create_customer_sales_request(customer_map[request_customer][0],request_product,request_qty,uw,uv,st.session_state.user_name,dummy_message)
                            st.success(f'✅ {no} sent to Logistics. Delivery Schedule can now auto-fill this order.')
                            st.rerun()
                        except ValueError as exc: st.error(str(exc))
        except Exception as exc:
            st.error(f'Unable to load products from the active dataset: {exc}')
    sales_requests=get_customer_sales_requests()
    if sales_requests:
        request_view=pd.DataFrame(sales_requests)[['request_no','company_name','item_name','requested_qty','unit_weight_kg','unit_volume_m3','status','created_at']]
        request_view.columns=['Request No','Customer','Product','Quantity','Unit Weight kg','Unit Volume m³','Status','Created At']
        st.markdown('<div class="section">Customer Sales Request History</div>',unsafe_allow_html=True)
        st.dataframe(request_view,use_container_width=True,hide_index=True)

def requests():
    header('Purchase Requests','Purchasing tracks approvals and completes approved orders.')
    rows=get_purchase_requests(); df=table(rows,['ID','Request No','Item','Category','Current Stock','Unit','Requested Qty','Weight KG','Reason','Status','Created By','Reviewed By','Created At','Reviewed At','Completed At','Item ID','Stock Status'],['ID','Item ID'],['Status','Stock Status'])
    if not df.empty:
        a=df[df.Status=='Approved']
        if not a.empty:
            opts={f"{r['Request No']} — {r['Item']}":int(r.ID) for _,r in a.iterrows()}; sel=st.selectbox('Approved Order',list(opts))
            if st.button('Complete Purchase and Move Stock to Standby'): complete_purchase_request(opts[sel]); st.success('Stock added and moved to Standby.'); st.rerun()

def approve():
    header('Request Approval','Approval immediately changes Critical stock to Stock Ready.')
    rows=get_purchase_requests(); df=pd.DataFrame(rows,columns=['ID','Request No','Item','Category','Current Stock','Unit','Requested Qty','Weight KG','Reason','Status','Created By','Reviewed By','Created At','Reviewed At','Completed At','Item ID','Stock Status'])
    for _,r in df[df.Status=='Pending'].iterrows():
        with st.container(border=True):
            st.write(f"**{r['Request No']} — {r['Item']}** | {r['Requested Qty']} {r['Unit']} | {r['Weight KG']} kg")
            c1,c2=st.columns(2)
            if c1.button('Approve',key='a'+str(r.ID)): update_purchase_request_status(r.ID,'Approved',st.session_state.user_name); st.success('Approved; stock is Stock Ready.'); st.rerun()
            if c2.button('Reject',key='r'+str(r.ID)): update_purchase_request_status(r.ID,'Rejected',st.session_state.user_name); st.rerun()

def _read_uploaded_dataset(uploaded):
    """Read a CSV or Excel upload without changing the source file."""
    if uploaded.name.lower().endswith('.csv'):
        return pd.read_csv(uploaded)
    return pd.read_excel(uploaded)


def _evaluation_line_chart(result, title):
    pred=result['predictions'].reset_index(drop=True).copy()
    pred=pred.head(min(120,len(pred)))
    fig=go.Figure()
    fig.add_trace(go.Scatter(
        x=pred.index+1,y=pred['Actual Sales'],name='Actual Sales',mode='lines+markers',
        hovertemplate='Sample %{x}<br>Actual: %{y:.2f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=pred.index+1,y=pred['Predicted Sales'],name='Predicted Sales',mode='lines+markers',
        line={'dash':'dot'},hovertemplate='Sample %{x}<br>Predicted: %{y:.2f}<extra></extra>'
    ))
    fig.update_layout(
        title=title,xaxis_title='Testing sample number',yaxis_title='Quantity sold',
        hovermode='x unified',height=430,legend_title_text='Series'
    )
    return fig




def render_dataset_rejection(title, reasons, detected_columns=None):
    """Display a clear blocking validation message with specific reasons."""
    st.error(f"❌ {title}")
    st.markdown("**Forecasting cannot continue with this dataset.**")
    st.markdown("**Reason(s):**")
    for reason in reasons:
        st.markdown(f"- {reason}")
    if detected_columns is not None:
        with st.expander("Uploaded columns detected"):
            st.write(list(detected_columns))
    st.info("The Purchasing Department must upload a valid historical sales dataset containing Date, Product and Quantity Sold. Unit Weight and Unit Volume are recommended for accurate truck allocation. Admin can upload only as a technical backup when Purchasing has an issue. The current active dataset has not been changed.")

def validate_active_forecasting_dataset(data):
    """Protect the Forecasting page from an invalid or unrelated active dataset."""
    try:
        mapping=data_cleaning_engine.detect_column_mapping(data.columns)
        cleaned,_=data_cleaning_engine.clean_sales_data(data,mapping)
        relevance=data_cleaning_engine.assess_dataset_relevance(cleaned)
        if not relevance['is_relevant']:
            return False, relevance.get('reasons', ['The active dataset is not relevant to food-demand forecasting.'])
        if len(cleaned) < 50:
            return False, [f"Only {len(cleaned)} valid rows are available; at least 50 are required for forecasting."]
        if cleaned['Quantity_Sold'].nunique() < 2:
            return False, ["Quantity Sold has no meaningful variation, so the model cannot learn demand patterns."]
        return True, []
    except Exception as exc:
        return False, [str(exc)]

def sales_dataset_view():
    """Read-only dataset access for Logistics and authorised staff."""
    header('Sales Dataset','Shared sales data supplied by Purchasing. Logistics access is read-only.')
    path=active_dataset_path()
    if path is None:
        st.warning('No sales dataset is available yet. The Purchasing Department must upload and activate it before forecasting can start. Admin is available only as a technical backup.')
        return
    try:
        data=pd.read_csv(path)
    except Exception as exc:
        st.error(f'Unable to read the active sales dataset: {exc}')
        return
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Rows',f'{len(data):,}'); c2.metric('Products',data['Product'].nunique() if 'Product' in data else '—')
    c3.metric('Total Sales Qty',f"{data['Quantity_Sold'].sum():,.0f}" if 'Quantity_Sold' in data else '—')
    c4.metric('Access','Read-only' if st.session_state.user_role=='Logistics Staff' else 'Authorised')
    st.caption('This page has no upload, edit, delete, or activation controls for Logistics users.')
    st.dataframe(data,use_container_width=True,hide_index=True,height=520)

def _current_model_result():
    try:
        result,data=get_model_evaluation()
        return result,data
    except Exception:
        return None,None


def data_cleaning_page():
    if not can_manage_sales_data():
        st.error('Access denied. Sales dataset upload is for the Purchasing Department. Admin may use it only for technical support; Logistics is read-only.')
        return
    header('Sales Data Management','Purchasing Department: upload, clean, validate and activate the sales dataset used by Forecasting and Truck Allocation.')
    if st.session_state.user_role=='Super Admin':
        st.warning('🛠️ Admin technical access: use dataset upload only when the Purchasing Department is unable to complete the upload due to a technical issue.')
    else:
        st.success('🔐 Dataset owner: Purchasing Department. Logistics has read-only access. Admin is technical backup only.')
    st.info('A new dataset is accepted only when it contains relevant food-demand information and passes model-quality checks. The existing active dataset remains unchanged when validation fails.')

    tab1,tab2=st.tabs(['🧹 Clean and Validate One Dataset','📊 Compare Different Datasets'])

    with tab1:
        uploaded=st.file_uploader('Upload raw sales dataset',type=['csv','xlsx'],key='single_clean_upload')
        if uploaded is None:
            st.markdown('<div class="section">Required information</div>',unsafe_allow_html=True)
            st.write('Minimum required fields: Date, Product, and Quantity Sold. Category, Stock Level, Unit Weight, Unit Volume (m³/CBM), and Promotion are recommended. Weight and volume are used for truck allocation. Common alternative column names are detected automatically.')
        else:
            try:
                raw=_read_uploaded_dataset(uploaded)
            except Exception as e:
                st.error(f'Unable to read the uploaded file: {e}')
                raw=None

            if raw is not None:
                st.markdown('<div class="section">Raw dataset preview</div>',unsafe_allow_html=True)
                st.dataframe(raw.head(20),use_container_width=True)
                detected=data_cleaning_engine.detect_column_mapping(raw.columns)
                st.caption('Automatically detected mapping: '+(', '.join(f'{k} ← {v}' for k,v in detected.items()) if detected else 'No matching columns detected'))

                try:
                    cleaned,report=data_cleaning_engine.clean_sales_data(raw,detected)
                    relevance=data_cleaning_engine.assess_dataset_relevance(cleaned)
                except Exception as e:
                    render_dataset_rejection(
                        'Dataset Validation Failed',
                        [str(e)],
                        raw.columns,
                    )
                    cleaned=None

                if cleaned is not None:
                    st.markdown('<div class="section">Cleaning summary</div>',unsafe_allow_html=True)
                    cols=st.columns(5)
                    metrics=[(report['input_rows'],'Input Rows'),(report['output_rows'],'Clean Rows'),(report['duplicates_removed'],'Duplicates Removed'),(report['invalid_core_rows_removed'],'Invalid Rows Removed'),(report['target_outliers_clipped'],'Outliers Adjusted')]
                    for c,(v,l) in zip(cols,metrics): c.metric(l,v)

                    detail=pd.DataFrame({
                        'Check':['Missing stock values filled','Invalid weights replaced','Invalid volumes replaced','Products','Categories','Date range'],
                        'Result':[report['missing_stock_filled'],report['invalid_weights_replaced'],report['invalid_volumes_replaced'],report['products'],report['categories'],f"{report['date_start']} to {report['date_end']}"]
                    })
                    st.dataframe(detail,use_container_width=True,hide_index=True)
                    for warning in report['warnings']: st.warning(warning)

                    st.markdown('<div class="section">Dataset relevance validation</div>',unsafe_allow_html=True)
                    r1,r2,r3=st.columns(3)
                    r1.metric('Relevance Status',relevance['status'])
                    r2.metric('Relevance Score',f"{relevance['score']}/100")
                    r3.metric('Food-related Records',f"{relevance.get('food_match_percent',0)}%")
                    if relevance['is_relevant']:
                        st.success('✅ Relevant food-demand dataset detected. Model evaluation is allowed.')
                        for reason in relevance['reasons']:
                            st.caption('• '+reason)
                    else:
                        render_dataset_rejection(
                            'Irrelevant Dataset Detected',
                            relevance['reasons'],
                            raw.columns,
                        )
                        st.warning('Forecasting, model training and dataset activation are blocked for this file.')

                    st.markdown('<div class="section">Cleaned dataset preview</div>',unsafe_allow_html=True)
                    st.dataframe(cleaned.head(50),use_container_width=True)
                    csv_bytes=cleaned.to_csv(index=False).encode('utf-8')
                    st.download_button('Download Cleaned CSV',csv_bytes,file_name='cleaned_data.csv',mime='text/csv',use_container_width=True)

                    if relevance['is_relevant']:
                        try:
                            candidate_result=forecasting_engine.evaluate_model(cleaned)
                            active_result,_=_current_model_result()
                            active_r2=active_result['r2_score'] if active_result else None
                            st.markdown('<div class="section">Candidate model evaluation</div>',unsafe_allow_html=True)
                            e1,e2,e3,e4=st.columns(4)
                            e1.metric('R²',f"{candidate_result['r2_score']:.4f}")
                            e2.metric('MAE',f"{candidate_result['mae']:.2f}")
                            e3.metric('RMSE',f"{candidate_result['rmse']:.2f}")
                            e4.metric('Testing Records',candidate_result['dataset_info']['testing_records'])
                            st.plotly_chart(_evaluation_line_chart(candidate_result,'Candidate Dataset: Actual Sales vs Predicted Sales'),use_container_width=True)

                            quality_ok=candidate_result['r2_score'] >= 0.50
                            drop_ok=active_r2 is None or candidate_result['r2_score'] >= active_r2-0.15
                            if not quality_ok:
                                st.error('Model quality check failed: R² is below 0.50. The active dataset will not be replaced.')
                            elif not drop_ok:
                                st.error(f"Model protection check failed: candidate R² is more than 0.15 below the active model R² ({active_r2:.4f}). The active dataset will not be replaced.")
                            else:
                                st.success('The dataset passed relevance, cleaning, and model-quality checks.')

                            if st.button('Activate This Dataset for Forecasting',use_container_width=True,disabled=not(quality_ok and drop_ok),key='activate_candidate'):
                                Path('data').mkdir(exist_ok=True)
                                active=Path('data/cleaned_data.csv')
                                backup=Path('data/cleaned_data_backup.csv')
                                if active.exists():
                                    if backup.exists(): backup.unlink()
                                    active.replace(backup)
                                cleaned.to_csv(active,index=False)
                                clear_model_cache()
                                notify('Logistics Staff','Sales dataset ready',f'{uploaded.name} was validated and activated by Purchasing. Forecasting and smart truck allocation are now available.')
                                st.success(f"Dataset activated successfully. R²: {candidate_result['r2_score']:.4f} | MAE: {candidate_result['mae']:.2f} | RMSE: {candidate_result['rmse']:.2f}")
                                st.rerun()
                        except Exception as e:
                            st.error(f'Model evaluation failed. The dataset was not activated: {e}')

    with tab2:
        st.write('Upload two or more datasets to compare their forecasting performance after cleaning. Irrelevant files are rejected and are not evaluated or injected.')
        comparison_files=st.file_uploader(
            'Upload datasets for comparison',type=['csv','xlsx'],accept_multiple_files=True,key='comparison_uploads'
        )
        include_active=st.checkbox('Include the current active dataset as a baseline',value=dataset_ready())

        if st.button('Run Dataset Comparison',use_container_width=True,disabled=not comparison_files and not include_active):
            comparison_results=[]
            chart_results={}

            if include_active:
                active_result,active_data=_current_model_result()
                if active_result is not None:
                    comparison_results.append({
                        'Dataset':'Current Active Dataset','Status':'Accepted / Active',
                        'Rows':len(active_data),'Products':active_data['Product'].nunique(),
                        'R²':active_result['r2_score'],'MAE':active_result['mae'],'RMSE':active_result['rmse']
                    })
                    chart_results['Current Active Dataset']=active_result

            for file in comparison_files or []:
                try:
                    raw=_read_uploaded_dataset(file)
                    mapping=data_cleaning_engine.detect_column_mapping(raw.columns)
                    cleaned,report=data_cleaning_engine.clean_sales_data(raw,mapping)
                    relevance=data_cleaning_engine.assess_dataset_relevance(cleaned)
                    if not relevance['is_relevant']:
                        comparison_results.append({
                            'Dataset':file.name,'Status':'Rejected – Irrelevant Dataset',
                            'Rows':len(cleaned),'Products':cleaned['Product'].nunique(),
                            'R²':None,'MAE':None,'RMSE':None
                        })
                        continue
                    result=forecasting_engine.evaluate_model(cleaned)
                    status='Accepted' if result['r2_score'] >= 0.50 else 'Relevant but Low Accuracy'
                    comparison_results.append({
                        'Dataset':file.name,'Status':status,'Rows':len(cleaned),
                        'Products':cleaned['Product'].nunique(),'R²':result['r2_score'],
                        'MAE':result['mae'],'RMSE':result['rmse']
                    })
                    chart_results[file.name]=result
                except Exception as e:
                    comparison_results.append({
                        'Dataset':file.name,'Status':f'Rejected – {str(e)[:80]}',
                        'Rows':None,'Products':None,'R²':None,'MAE':None,'RMSE':None
                    })

            st.session_state['dataset_comparison_table']=pd.DataFrame(comparison_results)
            st.session_state['dataset_comparison_charts']=chart_results

        comp_df=st.session_state.get('dataset_comparison_table')
        chart_results=st.session_state.get('dataset_comparison_charts',{})
        if comp_df is not None and not comp_df.empty:
            st.markdown('<div class="section">Model performance comparison</div>',unsafe_allow_html=True)
            format_df=comp_df.copy()
            for col in ['R²','MAE','RMSE']:
                format_df[col]=format_df[col].apply(lambda v:'—' if pd.isna(v) else f'{v:.4f}' if col=='R²' else f'{v:.2f}')
            st.dataframe(format_df,use_container_width=True,hide_index=True)
            st.caption('Higher R² is better. Lower MAE and RMSE are better. Rejected datasets are never written to the active forecasting file.')

            if chart_results:
                selected=st.selectbox('Select an accepted dataset for the Actual vs Predicted line chart',list(chart_results.keys()))
                st.plotly_chart(_evaluation_line_chart(chart_results[selected],f'{selected}: Actual Sales vs Predicted Sales'),use_container_width=True)


def forecasting():
    header('Forecasting','Actual sales vs predicted sales, powered by the trained Random Forest model.')
    active_path=active_dataset_path()
    if active_path is None:
        st.warning('⚠️ Forecasting cannot proceed because Purchasing has not uploaded and activated the sales dataset yet.')
        return
    try:
        active_data=pd.read_csv(active_path)
    except Exception as exc:
        render_dataset_rejection('Forecasting Blocked', [f'Unable to read the active dataset: {exc}'])
        return
    valid,reasons=validate_active_forecasting_dataset(active_data)
    if not valid:
        render_dataset_rejection('Forecasting Blocked – Invalid Active Dataset', reasons, active_data.columns)
        st.warning('Ask the Purchasing Department to upload and activate a valid dataset before returning to Forecasting.')
        return
    try:
        result,data=get_model_evaluation()
    except Exception as exc:
        render_dataset_rejection('Forecasting Blocked – Model Evaluation Failed', [str(exc)], active_data.columns)
        return
    a,b,c,d=st.columns(4)
    a.metric('Model Accuracy (R²)',f"{result['accuracy']}%"); b.metric('MAE',result['mae']); c.metric('RMSE',result['rmse']); d.metric('Training Records',f"{result['dataset_info']['training_records']:,}")
    pred=result['predictions'].reset_index(drop=True).head(60)
    fig=go.Figure(); fig.add_trace(go.Scatter(y=pred['Actual Sales'],name='Actual Sales',mode='lines',hovertemplate='Actual: %{y}<extra></extra>')); fig.add_trace(go.Scatter(y=pred['Predicted Sales'],name='Predicted Sales',mode='lines',line={'dash':'dot'},hovertemplate='Predicted: %{y}<extra></extra>')); fig.update_layout(title='Actual Sales vs Predicted Sales (test sample)',xaxis_title='Test sample #',yaxis_title='Quantity'); st.plotly_chart(fig,use_container_width=True)
    imp=result['feature_importance']
    fig2=px.bar(imp,x='Importance',y='Feature',orientation='h',title='Forecast Feature Importance (Random Forest)',hover_data={'Importance':':.1f'}); fig2.update_layout(xaxis_title='Relative influence (%)',yaxis_title='Input feature'); st.plotly_chart(fig2,use_container_width=True)
    top=imp.sort_values('Importance',ascending=False).iloc[0]
    st.info(f"**{top['Feature']}** has the strongest influence on the forecast ({top['Importance']}% relative importance). A longer bar means the model relies more heavily on that input.")

    next7=forecasting_engine.forecast_next_7_days(data)
    st.markdown('<div class="section">Next 7 Days Demand Forecast</div>',unsafe_allow_html=True)
    st.dataframe(next7,use_container_width=True,hide_index=True)

def smart_allocation():
    header('Smart Truck Allocation','Forecast-driven allocation using sales quantity, unit weight, unit volume and live truck availability.')
    if not dataset_ready():
        st.warning('⚠️ Truck allocation forecasting is locked until the Purchasing Department uploads and activates the sales dataset.')
        st.info('You can still open Truck Management to view truck status and fleet details.')
        return
    try:
        _,data=get_model_evaluation()
        forecast=forecasting_engine.forecast_next_7_days(data)
    except Exception as exc:
        st.error(f'Unable to calculate the forecast-based allocation: {exc}')
        return

    specs=data.copy()
    if 'Unit_Volume_m3' not in specs: specs['Unit_Volume_m3']=0.01
    specs=specs.groupby('Product',as_index=False).agg(Unit_Weight_kg=('Unit_Weight_kg','median'),Unit_Volume_m3=('Unit_Volume_m3','median'))
    plan=forecast.merge(specs,on='Product',how='left')
    plan['Forecast Weight KG']=(plan['Predicted_Qty']*plan['Unit_Weight_kg']).round(2)
    plan['Forecast Volume (cubic meter)']=(plan['Predicted_Qty']*plan['Unit_Volume_m3']).round(3)
    plan.rename(columns={'Unit_Weight_kg':'Unit Weight','Unit_Volume_m3':'Unit Volume'}, inplace=True)

    dates=list(plan['Date'].drop_duplicates())
    selected_date=st.selectbox('Forecast delivery date',dates)
    day=plan[plan['Date']==selected_date].copy()
    products=['All products',*sorted(day['Product'].unique())]
    selected_product=st.selectbox('Product scope',products)
    if selected_product!='All products': day=day[day['Product']==selected_product]

    total_qty=float(day['Predicted_Qty'].sum()); load=float(day['Forecast Weight KG'].sum()); volume=float(day['Forecast Volume (cubic meter)'].sum())
    available_count=sum(1 for r in get_all_trucks() if r[9]=='Available')
    a,b,c,d=st.columns(4)
    a.metric('Forecast Sales Qty',f'{total_qty:,.0f}'); b.metric('Forecast Weight',f'{load:,.1f} kg'); c.metric('Forecast Volume',f'{volume:,.2f} m³'); d.metric('Available Trucks',available_count)
    st.dataframe(day[['Product','Predicted_Qty','Unit Weight','Unit Volume','Forecast Weight KG','Forecast Volume (cubic meter)']],use_container_width=True,hide_index=True)

    rec=recommend_available_fleet(load,volume)
    if rec['available']:
        st.success(f"✅ {len(rec['trucks'])} available company truck(s) can handle this forecast load.")
        selected=pd.DataFrame(rec['trucks'],columns=['ID','Plate No','Truck Type','Capacity KG','Capacity cubic meter','Brand','Model','Year','Fuel/100KM','Status','Current Location'])
        st.dataframe(selected[['Plate No','Truck Type','Brand','Model','Capacity KG','Capacity cubic meter','Status','Current Location']],use_container_width=True,hide_index=True)
        u1,u2=st.columns(2); u1.metric('Weight Utilization',f"{rec['weight_utilization_pct']}%"); u2.metric('Volume Utilization',f"{rec['volume_utilization_pct']}%")
        st.progress(min(max(rec['weight_utilization_pct'],rec['volume_utilization_pct'])/100,1.0)); st.caption(rec['reason'])
    else:
        st.error('No combination of currently available company trucks has enough weight and/or volume capacity for this forecast load.')
        c1,c2,c3=st.columns(3); c1.warning('Contact Subcontractor'); c2.info('Wait for a truck to return from delivery.'); c3.info('Check trucks returning from repair.')
        notify('Purchasing Staff','No truck capacity for forecast',f'Forecast load {load:,.0f} kg / {volume:,.2f} m³ exceeds current available fleet capacity.')

def festival_planning():
    header('Festival Demand and Truck Preparation','Forecast upcoming festival surges, prepare inventory and reserve the right trucks for the load.')
    if not dataset_ready():
        st.warning('Festival planning requires an active sales dataset from Purchasing. The forecast and truck preparation worksheet are not available until the dataset is activated.')
        return
    try:
        _, data = get_model_evaluation()
        forecast = forecasting_engine.forecast_next_7_days(data)
    except Exception as exc:
        st.error(f'Unable to compute the festival forecast: {exc}')
        return

    festivals = [f for f in festival_engine.get_festival_names() if f != 'Normal Period']
    selected_festival = st.selectbox('Select festival to plan for', festivals)
    festival_pct = festival_engine.get_festival_percentage(selected_festival)
    uplift_factor = 1.0 + festival_pct
    st.markdown(f"<div class='section'>Expected uplift for {selected_festival}</div>", unsafe_allow_html=True)
    st.markdown(f"**Projected demand increase:** {festival_pct*100:.0f}%<br>**Adjustment multiplier:** {uplift_factor:.2f}")

    summary_cols = ['Date', 'Total Demand Before', 'Total Demand After', 'Total Weight KG', 'Total Volume m³']
    specs = data[['Product','Unit_Weight_kg','Unit_Volume_m3']].drop_duplicates(subset=['Product']).set_index('Product')
    forecast = forecast.merge(specs, on='Product', how='left')
    forecast['Adjusted_Qty'] = (forecast['Predicted_Qty'] * uplift_factor).round().astype(int)
    forecast['Demand_Increase'] = forecast['Adjusted_Qty'] - forecast['Predicted_Qty']
    forecast['Adjusted_Weight_KG'] = (forecast['Adjusted_Qty'] * forecast['Unit_Weight_kg']).round(2)
    forecast['Adjusted_Volume_m3'] = (forecast['Adjusted_Qty'] * forecast['Unit_Volume_m3']).round(3)

    totals = forecast.groupby('Date', as_index=False).agg(
        Total_Demand_Before=('Predicted_Qty','sum'),
        Total_Demand_After=('Adjusted_Qty','sum'),
        Total_Weight_KG=('Adjusted_Weight_KG','sum'),
        Total_Volume_m3=('Adjusted_Volume_m3','sum'),
    )
    totals['Demand Uplift'] = ((totals['Total_Demand_After'] / totals['Total_Demand_Before']) - 1).fillna(0).apply(lambda v: f"{v*100:.0f}%")

    st.markdown('<div class="section">Festival Forecast Summary</div>', unsafe_allow_html=True)
    st.dataframe(totals.rename(columns={
        'Total_Demand_Before':'Total Demand Before',
        'Total_Demand_After':'Total Demand After',
        'Total_Weight_KG':'Total Weight KG',
        'Total_Volume_m3':'Total Volume m³'
    }), use_container_width=True, hide_index=True)

    if not totals.empty:
        selected_date = st.selectbox('Select planning date', totals['Date'])
        day_plan = forecast[forecast['Date'] == selected_date].copy()
        day_plan = day_plan.sort_values(['Demand_Increase','Adjusted_Qty'], ascending=False)
        st.markdown('<div class="section">Top Products for Festival Delivery</div>', unsafe_allow_html=True)
        st.dataframe(day_plan[['Product','Predicted_Qty','Adjusted_Qty','Demand_Increase','Unit_Weight_kg','Unit_Volume_m3']].rename(columns={
            'Predicted_Qty':'Forecast Qty',
            'Adjusted_Qty':'Festival Qty',
            'Demand_Increase':'Qty Increase',
            'Unit_Weight_kg':'Unit Weight',
            'Unit_Volume_m3':'Unit Volume'
        }), use_container_width=True, hide_index=True)

        total_weight = float(day_plan['Adjusted_Weight_KG'].sum())
        total_volume = float(day_plan['Adjusted_Volume_m3'].sum())
        st.markdown('<div class="section">Truck Readiness</div>', unsafe_allow_html=True)
        st.write(f'**Estimated festival load:** {total_weight:,.0f} kg and {total_volume:,.2f} m³ for {selected_date}.')

        truck_rec = recommend_available_fleet(total_weight, total_volume)
        if truck_rec['available']:
            st.success('✅ Current available company fleet can handle this festival preparation load.')
            st.dataframe(pd.DataFrame(truck_rec['trucks'], columns=['ID','Plate No','Truck Type','Capacity KG','Capacity cubic meter','Brand','Model','Year','Fuel/100KM','Status','Current Location'])[ ['Plate No','Truck Type','Capacity KG','Capacity cubic meter','Brand','Model','Year','Status','Current Location'] ], use_container_width=True, hide_index=True)
            st.markdown(f"**Weight utilization:** {truck_rec['weight_utilization_pct']}%<br>**Volume utilization:** {truck_rec['volume_utilization_pct']}%", unsafe_allow_html=True)
            if max(truck_rec['weight_utilization_pct'], truck_rec['volume_utilization_pct']) > 90:
                st.warning('The selected fleet is nearing full capacity. Review the schedule and consider reserving backup trucks or splitting the load across earlier deliveries.')
        else:
            st.error('⚠️ Current available company fleet cannot support this festival load. Additional truck allocation is required.')
            st.write(truck_rec['reason'])
            st.info('Recommended action: reserve subcontractor trucks or trailer capacity, or rework the delivery plan to reduce peak load.')

    upcoming = festival_engine.get_upcoming_festivals(90)
    if upcoming:
        st.markdown('<div class="section">Upcoming Festival Calendar</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(upcoming), use_container_width=True, hide_index=True)


def truck_image_for(row):
    """Return the supplied photo that matches this fleet vehicle."""
    truck_type = str(row[2]).lower()
    brand = str(row[5]).lower()
    model = str(row[6]).lower()
    if '10-ton' in truck_type or '10 ton' in truck_type or 'heavy duty' in truck_type:
        return Path('images/truck_scania.jpg')
    if '5-ton' in truck_type or '5 ton' in truck_type or 'hino 700' in model:
        return Path('images/truck_hino_700.webp')
    if '2-ton' in truck_type or '2 ton' in truck_type or 'hino 300' in model or 'hino' in brand:
        return Path('images/truck_hino_light.jpg')
    if '1-ton' in truck_type or '1 ton' in truck_type or 'van' in truck_type:
        return Path('images/truck_toyota_hiace.jpg')
    return Path('images/hino300.jpg')

def get_dummy_drivers():
    return [
        ('Amin', '012-3456789'),
        ('Siti', '013-8765432'),
        ('Rahman', '014-9876543'),
        ('Rina', '015-4567890'),
        ('Azlan', '016-2345678'),
        ('Mira', '017-3456789'),
        ('Zul', '018-7654321'),
        ('Nadia', '019-1234567'),
        ('Farah', '010-9988776'),
        ('Hassan', '011-8877665'),
        ('Dina', '012-9988776'),
        ('Kamal', '013-7766554'),
        ('Lina', '014-6655443'),
        ('Aida', '015-5544332'),
        ('Badrul', '016-4433221'),
        ('Sabrina', '017-3322110'),
        ('Imran', '018-2211009'),
        ('Nora', '019-1100998'),
        ('Alya', '010-2233445'),
        ('Fahmi', '011-3344556'),
        ('Hana', '012-4455667'),
        ('Irfan', '013-5566778'),
        ('Jasmine', '014-6677889'),
        ('Khalid', '015-7788990'),
        ('Liyana', '016-8899001'),
        ('Mansor', '017-9900112'),
        ('Nabil', '018-1011121'),
        ('Omar', '019-1213141'),
        ('Putri', '010-1415161'),
        ('Rizal', '011-1617181'),
    ]

def get_truck_driver_map():
    schedules = get_delivery_schedules()
    mapping = {}
    for s in sorted(schedules, key=lambda r: r[0], reverse=True):
        truck_id = s[35] if len(s) > 35 else None
        if truck_id and truck_id not in mapping:
            driver_name = s[15] or '-'
            driver_phone = s[16] or '-'
            mapping[truck_id] = (driver_name, driver_phone)
    dummy_drivers = get_dummy_drivers()
    for idx, truck in enumerate(get_all_trucks()):
        if truck[0] not in mapping:
            mapping[truck[0]] = dummy_drivers[idx % len(dummy_drivers)]
    return mapping

def get_driver_information():
    """Return the latest known truck/status for each named driver."""
    conn=get_connection()
    rows=conn.execute('''SELECT ds.driver_name,ds.driver_phone,t.plate_no,ds.status,MAX(ds.delivery_date)
                         FROM delivery_schedules ds JOIN trucks t ON ds.truck_id=t.id
                         WHERE TRIM(COALESCE(ds.driver_name,''))!=''
                         GROUP BY ds.driver_name,ds.driver_phone,t.plate_no,ds.status
                         ORDER BY MAX(ds.delivery_date) DESC''').fetchall()
    conn.close()
    if rows:
        return [tuple(r) for r in rows]

    dummy_drivers = get_dummy_drivers()
    trucks = get_all_trucks()
    output = []
    for idx, truck in enumerate(trucks):
        driver_name, driver_phone = dummy_drivers[idx % len(dummy_drivers)]
        output.append((driver_name, driver_phone, truck[1], truck[9], '-'))
    return output

def trucks():
    header('Truck Management','Truck status updates the Logistics Dashboard immediately.')
    rows=get_all_trucks()
    driver_map=get_truck_driver_map()
    assignment_map=get_truck_assignment_map()
    display_rows=[]
    for idx,r in enumerate(rows, start=1):
        driver, phone = driver_map.get(r[0],('-', '-'))
        assignment=assignment_map.get(r[0])
        assigned_order=assignment['schedule_no'] if assignment else '-'
        assigned_at=assignment['assigned_at'] if assignment else '-'
        display_rows.append((idx, r[1], r[2], r[3], r[4], r[5], r[6], r[7], driver, phone, r[9], r[10],assigned_order,assigned_at))

    st.markdown('<div class="section">Fleet Summary</div>',unsafe_allow_html=True)
    total_trucks=len(rows)
    count_by_type={r[2]:0 for r in rows}
    for r in rows: count_by_type[r[2]] += 1
    c0,c1,c2,c3,c4 = st.columns(5)
    c0.metric('Total Trucks',f'{total_trucks}')
    c1.metric('3-Ton Lorry',f'{count_by_type.get("3-Ton Lorry",0)}')
    c2.metric('5-Ton Lorry',f'{count_by_type.get("5-Ton Lorry",0)}')
    c3.metric('10-Ton Lorry',f'{count_by_type.get("10-Ton Lorry",0)}')
    c4.metric('Tanker Truck',f'{count_by_type.get("Tanker Truck",0)}')

    st.markdown('<div class="section">Fleet Table</div>',unsafe_allow_html=True)
    statuses = ['All', *sorted({r[9] for r in rows})]
    selection = st.selectbox('Filter by Status', statuses, index=0)
    filtered = [row for row in display_rows if selection == 'All' or row[10] == selection]
    if selection != 'All':
        st.markdown(f'<div class="note">Showing trucks with status: <strong>{selection}</strong></div>', unsafe_allow_html=True)
    table(filtered,['No.','Plate No','Truck Type','Capacity (KG)','Capacity (m³)','Brand','Model','Year','Driver Name','Contact No.','Status','Current Location','Assigned Order','Assigned At'],['No.'],['Status'])

    st.markdown('<div class="section">Status Legend</div>',unsafe_allow_html=True)
    legend_cols = st.columns(4)
    legend_cols[0].markdown('<span class="badge" style="background:#dc26261a;color:#dc2626;border-color:#dc262655">Available</span>',unsafe_allow_html=True)
    legend_cols[1].markdown('<span class="badge" style="background:#d977061a;color:#d97706;border-color:#d9770655">Assigned</span>',unsafe_allow_html=True)
    legend_cols[2].markdown('<span class="badge" style="background:#6b72801a;color:#6b7280;border-color:#6b728055">Maintenance</span>',unsafe_allow_html=True)
    legend_cols[3].markdown('<span class="badge" style="background:#16a34a1a;color:#16a34a;border-color:#16a34a55">Verified/Completed</span>',unsafe_allow_html=True)
    st.caption(f'Last updated: {datetime.datetime.now():%d %B %Y %I:%M %p}')

    st.markdown('<div class="section">Fleet Cards</div>',unsafe_allow_html=True)
    for start in range(0,len(rows),4):
        cols=st.columns(4)
        for col,r in zip(cols,rows[start:start+4]):
            with col:
                with st.container(border=True):
                    truck_photo=truck_image_for(r)
                    if truck_photo.exists():
                        image_b64 = base64.b64encode(truck_photo.read_bytes()).decode()
                        suffix = truck_photo.suffix.lstrip('.').lower()
                        st.markdown(
                            f'<div class="truck-photo-wrapper"><img class="truck-photo" src="data:image/{suffix};base64,{image_b64}" alt="{r[1]}"></div>',
                            unsafe_allow_html=True
                        )
                    st.markdown(f"**{r[1]}**  \n{r[5]} {r[6]} · {r[7]}  \n{r[2]}  \n**Capacity:** {r[3]:,.0f} kg · {r[4]:,.1f} m³")
                    st.markdown(badge(r[9]),unsafe_allow_html=True)
                    st.caption(f'{r[10]} · {r[8]:g} L/100km')
                    assignment=assignment_map.get(r[0])
                    if assignment:
                        st.caption(f"📋 {assignment['schedule_no']} · Assigned {assignment['assigned_at']}")
    st.caption('Each fleet card uses the matching vehicle photo supplied for that truck.')

    opts={f'{r[1]} — {r[2]} ({r[9]})':r[0] for r in rows}
    c1,c2,c3=st.columns(3)
    sel=c1.selectbox('Truck',list(opts))
    status=c2.selectbox('Status',['Available','Assigned','Loading','On Route','Arrived','Delivered','Maintenance'])
    loc=c3.text_input('Location','Warehouse - KL')
    if st.button('Save Truck Status'):
        try:
            update_truck_status(opts[sel],status,loc)
            st.success('Truck and linked delivery status updated.')
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

def delivery():
    header('Delivery Schedule','Create Internal PO, assign a customer and truck, and calculate fuel/toll automatically.')
    arrived_popup=st.session_state.pop('delivery_arrived_popup',None)
    if arrived_popup:
        delivery_arrived_dialog(arrived_popup)
    st.markdown('<div class="section">Viva Demo Sales Orders</div>',unsafe_allow_html=True)
    if dataset_ready():
        st.caption('Generate 30 days of demo sales orders from the active dataset. Historical orders are completed, while the latest order is left Waiting Verification so you can demonstrate the full verification workflow.')
        if st.button('🧪 Generate 30-Day Demo Sales Orders',use_container_width=True):
            try:
                active=pd.read_csv(active_dataset_path())
                product_rows=active[['Product','Unit_Weight_kg']].dropna().drop_duplicates('Product').to_dict('records')
                count=generate_demo_sales_orders(product_rows,30)
                st.success(f'{count} demo sales orders generated. The latest delivery is Waiting Verification for your viva demonstration.')
                st.rerun()
            except Exception as exc:
                st.error(f'Unable to generate demo sales orders: {exc}')
    else:
        st.warning('Inject and activate a valid sales dataset before generating dummy sales orders. The orders must use products from the active dataset.')
    cust=get_customers(); co={f'{r[2]} — {r[1]}':r for r in cust}; available=[r for r in get_all_trucks() if r[9]=='Available']
    pending_sales=get_customer_sales_requests('Pending')
    request_options={f"📨 {r['request_no']} — {r['company_name']} — {r['item_name']} × {r['requested_qty']:g}":r for r in pending_sales}
    request_options['Manual Delivery Entry']=None
    if pending_sales:
        st.caption(f'📨 {len(pending_sales)} Purchasing customer request(s) waiting. The newest request is selected automatically for fast entry.')
    selected_request_label=st.selectbox('Purchasing Customer Request',list(request_options),help='Choose a request created by Purchasing to auto-fill the order. Use Manual Delivery Entry only when there is no Purchasing request.')
    sales_request=request_options[selected_request_label]
    if sales_request:
        st.success(f"✅ Received from Purchasing: {sales_request['request_no']} · Created {sales_request['created_at']}")
        st.info(f"💬 {sales_request['message']}")
    with st.container(border=True):
        request_key=str(sales_request['id']) if sales_request else 'manual'
        if sales_request:
            customer=next(k for k,v in co.items() if int(v[0])==int(sales_request['customer_id']))
            customer=st.selectbox('Customer from Purchasing',list(co),index=list(co).index(customer),disabled=True,key=f'delivery_customer_{request_key}')
            item=st.text_input('Item',value=sales_request['item_name'],disabled=True,key=f'delivery_item_{request_key}')
        else:
            customer=st.selectbox('Customer from Purchasing',list(co),key='delivery_customer_manual'); item=st.text_input('Item',key='delivery_item_manual')
        q1,q2,q3=st.columns(3)
        if sales_request:
            qty=q1.number_input('Quantity',1.0,1000000.0,float(sales_request['requested_qty']),disabled=True,key=f'delivery_qty_{request_key}')
            unit_weight=q2.number_input('Unit Weight (kg)',0.001,10000.0,float(sales_request['unit_weight_kg']),disabled=True,key=f'delivery_weight_{request_key}',help='Automatically received from Purchasing.')
            unit_volume=q3.number_input('Unit Volume (m³)',0.001,1000.0,float(sales_request['unit_volume_m3']),disabled=True,key=f'delivery_volume_{request_key}',format='%.3f',help='Automatically received from Purchasing.')
        else:
            qty=q1.number_input('Quantity',1.0,100000.0,100.0,key='delivery_qty_manual')
            unit_weight=q2.number_input('Unit Weight (kg)',0.001,10000.0,1.0,0.1,key='delivery_weight_manual',help='Weight of one unit/item.')
            unit_volume=q3.number_input('Unit Volume (m³)',0.001,1000.0,0.01,0.01,key='delivery_volume_manual',format='%.3f',help='Volume occupied by one unit/item.')
        load=float(qty)*float(unit_weight); load_m3=float(qty)*float(unit_volume)
        m1,m2=st.columns(2); m1.metric('Calculated Total Weight',f'{load:,.1f} kg'); m2.metric('Calculated Total Volume',f'{load_m3:,.2f} m³')
        rec=recommend_truck(load,load_m3)
        fitting=[r for r in available if float(r[3])>=load and float(r[4])>=load_m3]
        to={f'{r[1]} — {r[2]} ({r[3]:,.0f} kg / {r[4]:,.1f} m³)':r for r in fitting}
        if rec['available'] and rec['truck_id'] in [r[0] for r in fitting]:
            recommended_key=next(k for k,v in to.items() if v[0]==rec['truck_id'])
            default=list(to).index(recommended_key)
            truck=st.selectbox('Recommended Available Truck',list(to),index=default)
            st.success(f"✅ Suitable truck found: {rec['plate_no']} — {rec['truck_type']} · Weight use {rec['utilization_pct']}% · Volume use {rec['volume_utilization_pct']}%")
        else:
            truck=None
            st.warning('⚠️ No currently Available truck can carry BOTH this weight and volume. Use Smart Truck Allocation for multiple trucks, wait for a truck to become Available, or contact a subcontractor.')
        c3,c4=st.columns(2); driver=c3.text_input('Driver Name'); phone=c4.text_input('Driver Phone')
        c5,c6=st.columns(2); date=c5.date_input('Delivery Date',datetime.date.today()); eta=c6.text_input('Estimated Arrival Time',placeholder='e.g. 2:30 PM')
        with st.expander('Truck delivery details', expanded=False):
            c7,c8=st.columns(2)
            avg_speed=c7.number_input('Expected Average Speed (km/h)',40.0,120.0,80.0,1.0,help='Higher average speeds above 80 km/h increase fuel burn significantly.')
            tank_capacity=c8.number_input('Approx Tank Capacity (L)',100.0,600.0,250.0,10.0,help='Optional tank capacity for range estimation.')
            route_choices=['Customer default distance']+list(ROUTE_DISTANCES_FROM_KL.keys())+['Custom distance']
            selected_route=st.selectbox('Route from KL',route_choices)
            if selected_route in ROUTE_DISTANCES_FROM_KL:
                one_way_distance=float(ROUTE_DISTANCES_FROM_KL[selected_route])
                distance_default=one_way_distance*2.0
                st.caption(f'Using {selected_route} one-way distance: {one_way_distance} km; default round-trip: {distance_default} km')
            elif selected_route=='Customer default distance':
                one_way_distance=float(co[customer][7])
                distance_default=one_way_distance*2.0
                st.caption(f'Using customer default one-way distance: {one_way_distance} km; default round-trip: {distance_default} km')
            else:
                distance_default=0.0
            distance=st.number_input('Round-trip Distance KM',0.0,3000.0,distance_default)
            toll=st.number_input('Toll decided by Manager (RM)',0.0,10000.0,0.0,help='This saved route value is added to the Dashboard Active Toll Cost when the truck moves On Route.')
            instructions=st.text_area('Loading Instructions')
        if st.button('Generate Internal PO and Assign Truck',disabled=not bool(to),type='primary',use_container_width=True):
            try:
                no,po=create_delivery_schedule(co[customer][0],to[truck][0],date,item,qty,instructions,driver,phone,distance,toll,load,eta,avg_speed,tank_capacity,load_m3=load_m3,customer_request_id=sales_request['id'] if sales_request else None)
                st.success(f'✅ {no} created with {po}. Truck {to[truck][1]} changed from Available to Assigned and the assignment time was recorded.')
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    rows=get_delivery_schedules(); df=pd.DataFrame(rows,columns=DELIVERY_COLS)
    active_df=df[~df.Status.isin(['Delivered','Completed'])] if not df.empty else df
    if active_df.empty:
        st.info('No active deliveries. Delivered items move to Delivery Verification; completed items remain in Reports/history.')
    else:
        render_table(active_df.drop(columns=['ID','Truck ID']),['Status','Verification Status'])
    if not df.empty:
        open_df=active_df
        if not open_df.empty:
            opts={f"{r['Schedule No']} — {r['Customer']}":int(r.ID) for _,r in open_df.iterrows()}; sel=st.selectbox('Update Delivery Status',list(opts)); status=st.selectbox('New Status',['Assigned','Loading','On Route','Arrived','Delivered']); dnote=st.text_input('Driver Notes (used when marking Delivered)')
            if st.button('Update Delivery Status'):
                update_delivery_status(opts[sel],status,dnote if status=='Delivered' and dnote else None)
                if status=='Delivered':
                    delivered_row=df[df.ID==opts[sel]].iloc[0]
                    st.session_state.delivery_arrived_popup=delivered_row['Schedule No']
                st.success('Status updated.'); st.rerun()
        st.markdown('<div class="section">⏱️ 1-Minute Viva Delivery Timer</div>',unsafe_allow_html=True)
        st.caption('Demo feature: starts the selected delivery On Route for 60 seconds. When the clock reaches zero, the linked delivery and truck automatically change to Delivered / Waiting Verification.')
        eligible=df[df.Status.isin(['Assigned','Loading','On Route','Arrived'])]
        if eligible.empty:
            st.info('Create/assign a delivery to use the 1-minute viva timer.')
        else:
            timer_opts={f"{r['Schedule No']} — {r['Truck No']} — {r['Customer']}":int(r.ID) for _,r in eligible.iterrows()}
            timer_sel=st.selectbox('Demo delivery',list(timer_opts),key='demo_timer_delivery')
            timer_id=timer_opts[timer_sel]; timer_state=get_demo_delivery_timer(timer_id)
            timer_running=bool(timer_state and timer_state.get('status')=='On Route' and timer_state.get('demo_due_at') is not None)
            if st.button('▶ Start 1-Minute Demo Trip',disabled=timer_running,use_container_width=True):
                try:
                    start_demo_delivery_timer(timer_id,60)
                    st.success('Demo timer started. Truck status changed to On Route.')
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            if timer_running:
                demo_delivery_timer_fragment(timer_id)

def pod():
    header('Printable Insourced POD','Professional A4 proof of delivery with signature boxes.')
    rows=get_delivery_schedules(); df=pd.DataFrame(rows,columns=DELIVERY_COLS)
    if df.empty: st.info('No delivery record.'); return
    opts={f"{r['Schedule No']} — {r['Customer']}":i for i,r in df.iterrows()}; sel=st.selectbox('Select POD',list(opts)); r=df.loc[opts[sel]]
    logo64=logo_b64(); logo_html=f'<img src="data:image/png;base64,{logo64}" style="height:56px;display:block;margin:0 auto 6px">' if logo64 else ''
    st.markdown(f'''<div id="printpod" class="pod">{logo_html}<h2>VILVAM TRADING</h2><p style="text-align:center"><b>INSOURCED PROOF OF DELIVERY</b></p><div class="pod-grid"><div class="pod-box"><b>Customer</b><br>{r['Customer']}<br>{r['Delivery Address']}<br>Contact: {r['Contact Person']} / {r['Customer Phone']}</div><div class="pod-box"><b>Delivery</b><br>Schedule: {r['Schedule No']}<br>Internal PO: {r['Internal PO']}<br>Date: {r['Delivery Date']}<br>Estimated Arrival: {r['Estimated Arrival'] or '—'}<br>Status: {r['Status']}</div><div class="pod-box"><b>Truck & Driver</b><br>Truck: {r['Truck No']} ({r['Truck Type']})<br>Driver: {r['Driver']}<br>Phone: {r['Driver Phone']}</div><div class="pod-box"><b>Item Details</b><br>Item: {r['Item']}<br>Quantity: {r['Quantity']}<br>Actual Quantity: {r['Actual Quantity'] or '—'}<br>Instructions: {r['Instructions']}</div></div><div class="pod-box" style="margin-top:14px"><b>Delivery Verification</b><br>Arrival Time: {r['Arrival Time'] or '—'}<br>Completed Time: {r['Completed Time'] or '—'}<br>Verified By: {r['Verified By'] or '—'}<br>Verification Status: {r['Verification Status']}<br>Driver Notes: {r['Driver Notes'] or '—'}</div><div class="pod-grid" style="margin-top:14px"><div><b>Customer Signature</b><div class="sig"></div></div><div><b>Driver Signature</b><div class="sig"></div></div></div></div>''',unsafe_allow_html=True)
    st.components.v1.html('''<button onclick="window.parent.print()" style="padding:12px 24px;background:#f97316;color:white;border:0;border-radius:8px;font-weight:bold">🖨 Print POD</button>''',height=60)

def verification():
    header('Delivery Verification','Management verifies delivered stock before the truck returns to Available.')
    rows=get_delivery_schedules(); df=pd.DataFrame(rows,columns=DELIVERY_COLS); waiting=df[df['Verification Status']=='Waiting Verification']
    if waiting.empty: st.success('No delivery waiting for verification.'); return
    v1,v2=st.columns([1,3]); v1.metric('Waiting Verification',len(waiting)); v2.info('Workflow: Delivered → Management Verification → Completed → Truck Available')
    preview_cols=['Schedule No','Customer','Truck No','Item','Quantity','Completed Time','Driver Notes']
    st.dataframe(waiting[preview_cols],use_container_width=True,hide_index=True)
    opts={f"{r['Schedule No']} — {r['Customer']} — {r['Truck No']}":int(r.ID) for _,r in waiting.iterrows()}; sel=st.selectbox('Delivery',list(opts)); row=df[df.ID==opts[sel]].iloc[0]
    actual_qty=st.number_input('Actual Quantity Delivered',0.0,1000000.0,float(row['Quantity'] or 0)); note=st.text_area('Management Verification Note')
    if st.button('Verify Delivery and Release Truck'):
        try:
            verify_delivery(opts[sel],note,st.session_state.user_name,actual_qty)
            delivery_complete_dialog(row['Schedule No'],row['Customer'])
        except ValueError as exc:
            st.error(str(exc))

def build_pdf_report(summary,df,forecast_acc):
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    pdf=FPDF(); pdf.add_page(); pdf.set_font('Helvetica','B',16); pdf.cell(0,10,'VILVAM Logistics Report',ln=True)
    pdf.set_font('Helvetica','',11)
    lines=[f"Total Deliveries: {summary['total_deliveries']}",f"Completed: {summary['completed_deliveries']}",f"Pending: {summary['pending_deliveries']}",
           f"Distance Travelled: {summary['distance_km']} km",f"Average Truck Utilization: {summary['avg_utilization']}%",f"Delivery Performance: {summary['delivery_performance']}%",
           f"Forecast Accuracy: {forecast_acc if forecast_acc is not None else 'N/A'}%",f"Fuel Used: {df['Fuel Litres'].sum():.2f} L",
           f"Fuel Cost: RM {df['Fuel Cost RM'].sum():.2f}",f"Toll Cost: RM {df['Toll RM'].sum():.2f}"]
    for l in lines: pdf.cell(0,8,l,ln=True)
    return bytes(pdf.output())

def reports():
    header('Reports','Delivery, fuel, toll, utilization, performance and forecast accuracy analytics.')
    st.markdown('<div class="section">Demo Order Generator</div>',unsafe_allow_html=True)
    if dataset_ready():
        if st.button('🧪 Generate / Refresh 30-Day Dummy Sales Orders',use_container_width=True):
            try:
                active=pd.read_csv(active_dataset_path())
                product_rows=active[['Product','Unit_Weight_kg']].dropna().drop_duplicates('Product').to_dict('records')
                count=generate_demo_sales_orders(product_rows,30)
                st.success(f'{count} demo sales orders generated. The latest delivery is Waiting Verification so Delivery Verification can be demonstrated.')
                st.rerun()
            except Exception as exc:
                st.error(f'Unable to generate demo orders: {exc}')
    else:
        st.warning('Dummy sales orders cannot be generated without an injected and activated sales dataset.')
    rows=get_delivery_schedules(); df=pd.DataFrame(rows,columns=DELIVERY_COLS)
    summary=get_report_summary()
    try: result,_=get_model_evaluation(); forecast_acc=result['accuracy']
    except Exception: forecast_acc=None
    a,b,c,d,e=st.columns(5)
    a.metric('Total Deliveries',summary['total_deliveries']); b.metric('Completed',summary['completed_deliveries']); c.metric('Pending',summary['pending_deliveries']); d.metric('Distance Travelled',f"{summary['distance_km']:,.0f} km"); e.metric('Avg Truck Utilization',f"{summary['avg_utilization']}%")
    f,g,h,i=st.columns(4)
    f.metric('Delivery Performance',f"{summary['delivery_performance']}%"); g.metric('Forecast Accuracy',f"{forecast_acc}%" if forecast_acc is not None else 'N/A')
    period=get_fuel_cost_period_summary()
    st.markdown('<div class="section">Fuel Cost by Period</div>',unsafe_allow_html=True)
    pc1,pc2,pc3=st.columns(3)
    pc1.metric('Today',f"RM {period['day'][2]:.2f}",f"{period['day'][0]} order(s) • {period['day'][1]:.2f} L")
    pc2.metric('Last 7 Days',f"RM {period['week'][2]:.2f}",f"{period['week'][0]} order(s) • {period['week'][1]:.2f} L")
    pc3.metric('Current Month',f"RM {period['month'][2]:.2f}",f"{period['month'][0]} order(s) • {period['month'][1]:.2f} L")
    if period['daily']:
        fuel_daily=pd.DataFrame(period['daily'],columns=['Date','Sales Orders','Fuel Litres','Fuel Cost RM'])
        st.plotly_chart(px.line(fuel_daily,x='Date',y='Fuel Cost RM',markers=True,title='Daily Fuel Cost Trend'),use_container_width=True)
        st.dataframe(fuel_daily,use_container_width=True,hide_index=True)
    if df.empty: st.info('No delivery report data yet. Generate dummy sales orders after activating a dataset.'); return
    h.metric('Fuel Used',f"{df['Fuel Litres'].sum():.2f} L"); i.metric('Fuel Cost',f"RM {df['Fuel Cost RM'].sum():.2f}")
    st.metric('Toll Cost',f"RM {df['Toll RM'].sum():.2f}")
    status=df.Status.value_counts().rename_axis('Status').reset_index(name='Deliveries'); st.plotly_chart(px.pie(status,names='Status',values='Deliveries',hole=.5,title='Delivery Status'),use_container_width=True)
    st.markdown('<div class="section">Export</div>',unsafe_allow_html=True)
    e1,e2,e3=st.columns(3)
    e1.download_button('Download CSV',df.to_csv(index=False).encode(),file_name='vilvam_delivery_report.csv',mime='text/csv',use_container_width=True)
    xbuf=io.BytesIO()
    with pd.ExcelWriter(xbuf,engine='openpyxl') as writer: df.to_excel(writer,index=False,sheet_name='Delivery Report')
    e2.download_button('Download Excel',xbuf.getvalue(),file_name='vilvam_delivery_report.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True)
    pdf_bytes=build_pdf_report(summary,df,forecast_acc)
    if pdf_bytes: e3.download_button('Download PDF',pdf_bytes,file_name='vilvam_delivery_report.pdf',mime='application/pdf',use_container_width=True)
    else: e3.caption('PDF export needs `pip install fpdf2`.')

def admin(): header('Admin','Users and roles.'); table(get_all_users(),['ID','Name','Email','Role'],None,['Role'])

def main():
    init_db()
    for k,v in [('logged_in',False),('user_name',''),('user_role',''),('page','Dashboard'),('missing_dataset_notified',False)]: st.session_state.setdefault(k,v)
    if not st.session_state.logged_in: login(); return
    run_notification_scan()
    if st.session_state.user_role=='Logistics Staff' and not dataset_ready() and not st.session_state.missing_dataset_notified:
        st.toast('Forecasting cannot proceed yet — Purchasing has not uploaded the sales dataset.',icon='⚠️')
        st.session_state.missing_dataset_notified=True
    sidebar(); p=st.session_state.page
    if not dataset_ready() and p not in ('Sales Data Management','Sales Dataset','Truck Management','Dashboard','Notifications','Admin'):
        render_dataset_required_banner()
    pages={'Dashboard':dashboard,'Sales Data Management':data_cleaning_page,'Sales Dataset':sales_dataset_view,'Stock Management':lambda:stock(False),'Stock View':lambda:stock(True),'Customer Management':customers,'Purchase Requests':requests,'Smart Reorder Recommendation':reorder_recommendation,'Notifications':notifications_page,'Request Approval':approve,'Forecasting':forecasting,'Festival Planning':festival_planning,'Smart Truck Allocation':smart_allocation,'Truck Management':trucks,'Delivery Schedule':delivery,'Printable POD':pod,'Delivery Verification':verification,'Reports':reports,'Admin':admin}
    if p in pages: pages[p]()
    else: st.error('Access denied.')
if __name__=='__main__': main()
