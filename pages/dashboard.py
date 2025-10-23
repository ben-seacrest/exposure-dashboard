# dashboard.py
import json
import pandas as pd
import requests
import streamlit as st
from requests.exceptions import ReadTimeout, ConnectionError

# -------------------------------#
# Centroid endpoints
# -------------------------------#
centroid = st.secrets["centroid"]
LOGIN_URL = centroid["login_url"]
POS_URL   = centroid["positions_url"]
USERNAME  = centroid["username"]
PASSWORD  = centroid["password"]
CLIENT_CODE = centroid.get("client_code", "")
ACCOUNTS = centroid.get("accounts", [])

# -------------------------------#
# Symbol and Asset DataFrames
# -------------------------------#
symbols_data = [
    ["AUDCAD", "AUD", "CAD"],
    ["AUDCHF", "AUD", "CHF"],
    ["AUDJPY", "AUD", "JPY"],
    ["AUDNZD", "AUD", "NZD"],
    ["AUDUSD", "AUD", "USD"],
    ["BCHUSD", "BCH", "USD"],
    ["BRENT", "BRENT", "GBP"],
    ["BTCUSD", "BTC", "USD"],
    ["CADCHF", "CAD", "CHF"],
    ["CADJPY", "CAD", "JPY"],
    ["CHFJPY", "CHF", "JPY"],
    ["Cotton", "Cotton", "USD"],
    ["DE40", "DE40", "EUR"],
    ["ETHUSD", "ETH", "USD"],
    ["EURAUD", "EUR", "AUD"],
    ["EURCAD", "EUR", "CAD"],
    ["EURCHF", "EUR", "CHF"],
    ["EURGBP", "EUR", "GBP"],
    ["EURJPY", "EUR", "JPY"],
    ["EURNZD", "EUR", "NZD"],
    ["EURUSD", "EUR", "USD"],
    ["Gasoil", "Gasoil", "USD"],
    ["GBPAUD", "GBP", "AUD"],
    ["GBPCAD", "GBP", "CAD"],
    ["GBPCHF", "GBP", "CHF"],
    ["GBPJPY", "GBP", "JPY"],
    ["GBPNZD", "GBP", "NZD"],
    ["GBPUSD", "GBP", "USD"],
    ["JP225", "JP225", "JPY"],
    ["LTCUSD", "LTC", "USD"],
    ["NZDCAD", "NZD", "CAD"],
    ["NZDCHF", "NZD", "CHF"],
    ["NZDJPY", "NZD", "JPY"],
    ["NZDUSD", "NZD", "USD"],
    ["UK100", "UK100", "GBP"],
    ["US100", "US100", "USD"],
    ["US30", "US30", "USD"],
    ["US500", "US500", "USD"],
    ["USDCAD", "USD", "CAD"],
    ["USDCHF", "USD", "CHF"],
    ["USDCNH", "USD", "CNH"],
    ["USDJPY", "USD", "JPY"],
    ["USDMXN", "USD", "MXN"],
    ["USDNOK", "USD", "NOK"],
    ["USDPLN", "USD", "PLN"],
    ["USDSEK", "USD", "SEK"],
    ["USDZAR", "USD", "ZAR"],
    ["USOIL", "USOIL", "USD"],
    ["XAGUSD", "XAG", "USD"],
    ["XAUUSD", "XAU", "USD"],
]
symbols_df = pd.DataFrame(symbols_data, columns=["Symbol", "Base", "Quote"])

buckets_data = [
    "AUD","BCH","BRENT","BTC","CAD","CHF","Cotton","DE40","ETH","EUR",
    "Gasoil","GBP","JP225","LTC","NZD","UK100","US100","US30","US500","USD",
    "USOIL","XAG","XAU","JPY","CNH","MXN","NOK","PLN","SEK","ZAR",
]
buckets_df = pd.DataFrame({"Asset": buckets_data})
buckets_df["Net Total"] = 0.0

# -------------------------------#
# Centroid Helper Functions
# -------------------------------#
def normalize_accounts(accounts):
    normalized, raw = [], []
    for a in accounts or []:
        a = str(a).strip()
        if not a:
            continue
        raw.append(a)
        if "||" in a:
            normalized.append(a)
        elif a.startswith("CLIENT "):
            normalized.append("CLIENT||" + a.split(" ", 1)[1])
        else:
            normalized.append(f"CLIENT||{a}")
    def _dedup(seq):
        seen, out = set(), []
        for x in seq:
            if x not in seen:
                out.append(x); seen.add(x)
        return out
    return _dedup(normalized), _dedup(raw)

def login():
    if not USERNAME or not PASSWORD:
        raise RuntimeError("Missing Streamlit secrets: centroid.username / centroid.password")
    r = requests.post(
        LOGIN_URL,
        json={"username": USERNAME, "password": PASSWORD},
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=15,
    )
    r.raise_for_status()
    j = r.json()
    token = j["token"]
    user = j.get("user", {})
    broker_user = user.get("username", USERNAME)
    client_code = user.get("client_code") or CLIENT_CODE
    if not client_code:
        raise RuntimeError("client_code missing; set [centroid].client_code in secrets.")
    return token, client_code, broker_user

def try_fetch(token, client_code, broker_user, body):
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "x-forward-client": client_code,
        "x-forward-user": broker_user,
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(POS_URL, headers=headers, json=body, timeout=25)
        if r.status_code != 200 or "application/json" not in (r.headers.get("Content-Type","")).lower():
            return []
        data = r.json()
        return data if isinstance(data, list) else []
    except (ReadTimeout, ConnectionError):
        st.warning("⚠️ Network/API timeout or unreachable Centroid bridge.")
        return []
    except Exception as e:
        st.warning(f"⚠️ Unexpected error: {e}")
        return []

def fetch_positions(accounts_input):
    token, client_code, broker_user = login()
    norm, raw = normalize_accounts(accounts_input)
    bodies = []
    if norm: bodies.append({"position_account": norm, "symbol": [], "taker": []})
    if raw:  bodies.append({"position_account": raw,  "symbol": [], "taker": []})
    bodies.append({"position_account": [], "symbol": [], "taker": []})
    for b in bodies:
        data = try_fetch(token, client_code, broker_user, b)
        if data:
            return data, client_code, broker_user, b
    return [], client_code, broker_user, bodies[-1]

def to_df(items):
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame(items)
    cols = [
        "account","symbol_val","net_volume","avg_price","pl","taker","last_time_value",
        "notional","base_exposure","quote_exposure","margin"
    ]
    df = df[[c for c in cols if c in df.columns]].copy()
    df.rename(columns={
        "symbol_val":"symbol",
        "net_volume":"net",
        "avg_price":"avg_px",
        "last_time_value":"last_time"
    }, inplace=True)
    for c in ["net","avg_px","pl","notional","base_exposure","quote_exposure","margin"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "symbol" in df.columns:
        df = df[df["symbol"].str.lower() != "coffee"]
    return df

def fmt_money(val: float) -> str:
    try: val = float(val)
    except (TypeError, ValueError): return "$0.00"
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 1_000_000_000: out = f"{val/1_000_000_000:.2f}b"
    elif val >= 1_000_000:   out = f"{val/1_000_000:.2f}m"
    elif val >= 1_000:       out = f"{val/1_000:.2f}k"
    else:                    out = f"{val:.2f}"
    return f"{sign}${out}"

# -------------------------------#
# Auto-refresh Exposure Panel
# -------------------------------#
@st.fragment(run_every=5)
def exposure_panel():
    accounts_input = ACCOUNTS or []
    st.caption(f"Accounts from → {accounts_input}")

    items, client_code, broker_user, used_body = fetch_positions(accounts_input)
    if not items:
        st.error("No positions returned.")
        return

    df = to_df(items)
    if df.empty:
        st.warning("Empty DataFrame after normalization.")
        return

    # --- KPI metrics ---
    k = st.columns(3)
    with k[0]:
        st.metric("Floating P/L", fmt_money(df["pl"].sum(skipna=True)), border=True)
    with k[1]:
        if "notional" in df.columns:
            st.metric("Notional Volume", fmt_money(df["notional"].sum(skipna=True)), border=True)
    with k[2]:
        if "margin" in df.columns:
            st.metric("Utilised Margin", fmt_money(df["margin"].sum(skipna=True)), border=True)

    st.divider()

    # --- Filters ---
    symbols = sorted(df["symbol"].dropna().astype(str).unique())
    takers  = sorted(df["taker"].dropna().astype(str).unique())
    col1, col2 = st.columns(2)
    with col1:
        symbol_sel = st.selectbox("Symbols", options=["(All)"] + symbols, index=0)
    with col2:
        taker_sel = st.selectbox("Platforms", options=["(All)"] + takers, index=0)

    # --- Filter view ---
    view = df.copy()
    if symbol_sel != "(All)":
        view = view[view["symbol"] == symbol_sel]
    if taker_sel != "(All)":
        view = view[view["taker"] == taker_sel]
    for c in ["net","avg_px","pl","notional","base_exposure","quote_exposure","margin"]:
        if c in view.columns:
            view[c] = pd.to_numeric(view[c], errors="coerce").round(2)
    view = view.sort_values(by="pl", key=lambda s: s.abs(), ascending=False)

    # --- Merge Base/Quote columns ---
    view = view.merge(symbols_df, how="left", left_on="symbol", right_on="Symbol").drop(columns=["Symbol"])

    # --- Exposure buckets calc ---
    base_sum  = view.groupby("Base", dropna=False)["base_exposure"].sum(numeric_only=True)
    quote_sum = view.groupby("Quote", dropna=False)["quote_exposure"].sum(numeric_only=True)
    buckets_df["Net Total"] = (
        buckets_df["Asset"].map(base_sum).fillna(0)
        + buckets_df["Asset"].map(quote_sum).fillna(0)
    )

    # --- Output ---
    st.write("### Net Exposure by Asset")
    st.dataframe(
        buckets_df.sort_values("Net Total", key=lambda s: s.abs(), ascending=False), 
        hide_index=True,
        column_config={
            "Net Total": st.column_config.NumberColumn(format="dollar"),
        }
    )

# -------------------------------#
# Page entrypoint
# -------------------------------#
def dashboard_page():
    first_name = st.session_state.get("first_name", "there")
    st.subheader(f"Welcome, {first_name}", anchor=False)
    exposure_panel()

if __name__ == "__main__":
    dashboard_page()
