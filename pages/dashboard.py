# dashboard.py
import json
import pandas as pd
import requests
import streamlit as st
from requests.exceptions import ReadTimeout, ConnectionError

centroid = st.secrets["centroid"]
LOGIN_URL = centroid["login_url"]
POS_URL   = centroid["positions_url"]
USERNAME  = centroid["username"]
PASSWORD  = centroid["password"]
CLIENT_CODE = centroid.get("client_code", "")
ACCOUNTS = centroid.get("accounts", [])

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
    "AUD",
    "BCH",
    "BRENT",
    "BTC",
    "CAD",
    "CHF",
    "Cotton",
    "DE40",
    "ETH",
    "EUR",
    "Gasoil",
    "GBP",
    "JP225",
    "LTC",
    "NZD",
    "UK100",
    "US100",
    "US30",
    "US500",
    "USD",
    "USOIL",
    "XAG",
    "XAU",
    "JPY",
    "CNH",
    "MXN",
    "NOK",
    "PLN",
    "SEK",
    "ZAR",
]

buckets_df = pd.DataFrame(buckets_data, columns=["Asset", "Net Total"])

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

    # de-dup while preserving order
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
    user  = j.get("user", {})
    broker_user = user.get("username", USERNAME)
    # Prefer API-returned client_code; fall back to secrets
    client_code = user.get("client_code") or CLIENT_CODE
    if not client_code:
        raise RuntimeError("client_code missing; set [centroid].client_code in secrets or use a user that returns it")
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
        if r.status_code != 200:
            return []
        if "application/json" not in (r.headers.get("Content-Type", "")).lower():
            return []
        data = r.json()
        return data if isinstance(data, list) else []
    except ReadTimeout:
        st.warning("Centroid API read timeout.")
        return []
    except ConnectionError:
        st.warning("Network/connection error reaching Centroid API.")
        return []
    except Exception as e:
        st.warning(f"Unexpected API error: {e}")
        return []

def fetch_positions(accounts_input):
    token, client_code, broker_user = login()
    norm, raw = normalize_accounts(accounts_input)

    bodies = []
    if norm: bodies.append({"position_account": norm, "symbol": [], "taker": []})
    if raw:  bodies.append({"position_account": raw,  "symbol": [], "taker": []})
    bodies.append({"position_account": [], "symbol": [], "taker": []})  # last resort: all visible

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
        "account", "symbol_val", "net_volume", "avg_price", "pl",
        "taker", "last_time_value", "notional",
        "base_exposure", "quote_exposure", "margin"
    ]
    df = df[[c for c in cols if c in df.columns]].copy()

    df.rename(columns={
        "symbol_val": "symbol",
        "net_volume": "net",
        "avg_price":  "avg_px",
        "last_time_value": "last_time"
    }, inplace=True)

    # Enforce numeric types (kept raw for sortable DataFrame)
    for c in ["net", "avg_px", "pl", "notional", "base_exposure", "quote_exposure", "margin"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Remove Coffee if present
    if "symbol" in df.columns:
        df = df[df["symbol"].str.lower() != "coffee"]

    return df

def fmt_money(val: float) -> str:
    try:
        val = float(val)
    except (TypeError, ValueError):
        return "$0.00"
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 1_000_000_000:
        out = f"{val/1_000_000_000:.2f}b"
    elif val >= 1_000_000:
        out = f"{val/1_000_000:.2f}m"
    elif val >= 1_000:
        out = f"{val/1_000:.2f}k"
    else:
        out = f"{val:.2f}"
    return f"{sign}${out}"

@st.fragment(run_every=1)
def exposure_panel():
    accounts_input = ACCOUNTS or []
    st.caption(f"Accounts from → {accounts_input}")

    items, client_code, broker_user, used_body = fetch_positions(accounts_input)

    if not items:
        st.error("No positions returned. Tip: set [centroid].accounts to ['CLIENT tem_b'] or leave it empty to fetch all visible.")
        return

    df = to_df(items)
    if df.empty:
        st.warning("Empty DataFrame after normalization.")
        return

    k = st.columns(3)
    with k[0]:
        st.metric(
            label="Floating P/L", 
            value=fmt_money(df["pl"].sum(skipna=True)),
            border=True
        )
    with k[1]:
        if "notional" in df.columns and df["notional"].notna().any():
            st.metric(
                label="Notional Volume", 
                value=fmt_money(df["notional"].sum(skipna=True)),
                border=True
            )
        else:
            est = (df["net"].abs() * df["avg_px"]).sum(skipna=True) if {"net","avg_px"}.issubset(df.columns) else 0.0
            st.metric(
                label="Notional Volume (est.)", 
                value=fmt_money(est),
                border=True
            )
    with k[2]:
        if "margin" in df.columns and df["margin"].notna().any():
            st.metric(
                label="Utilised Margin", 
                value=fmt_money(df["margin"].sum(skipna=True)),
                border=True
            )

    
    symbols = sorted(df["symbol"].dropna().astype(str).unique())
    takers  = sorted(df["taker"].dropna().astype(str).unique())

    col1, col2 = st.columns(2, vertical_alignment="top")
    with col1:
        symbol_sel = st.selectbox("Symbols", options=["(All)"] + symbols, index=0)
    with col2:
        taker_sel = st.selectbox("Platforms", options=["(All)"] + takers, index=0)
    
    view = df.copy()
    if symbol_sel != "(All)":
        view = view[view["symbol"] == symbol_sel]
    if taker_sel != "(All)":
        view = view[view["taker"] == taker_sel]

    for c in ["net", "avg_px", "pl", "notional", "base_exposure", "quote_exposure", "margin"]:
        if c in view.columns:
            view[c] = pd.to_numeric(view[c], errors="coerce").round(2)

    view = view.sort_values(by="pl", key=lambda s: s.abs(), ascending=False)

    tab1, tab2 = st.tabs(["Data Table", "Charts"])

    with tab1:
        if view.empty:
            st.info("No positions for the selected symbol / platform.")
        else:
            view_display = view[["symbol", "net", "avg_px", "pl", "taker", "notional", "margin"]]

            # Merge view with symbols_df to append Base and Quote
            view = view.merge(
                symbols_df,
                how="left",
                left_on="symbol",
                right_on="Symbol"
            )
            
            # Drop the duplicate 'Symbol' column from symbols_df after merge
            view.drop(columns=["Symbol"], inplace=True)
            
            st.dataframe(
                view,
                hide_index=True,
                #column_config={
                #    "symbol": st.column_config.TextColumn("Symbol"),
                #    "net": st.column_config.NumberColumn("Lots", format="accounting"),
                #    "avg_px": st.column_config.NumberColumn("Avg. Price", format="dollar"),
                #    "pl": st.column_config.NumberColumn("P/L", format="dollar"),
                #    "taker": st.column_config.TextColumn("Taker"),
                #    "notional": st.column_config.NumberColumn("Notional", format="dollar"),
                #    "margin": st.column_config.NumberColumn("Margin", format="dollar"),
                #},
            )

            # Sums per asset
            base_sum  = view.groupby("Base", dropna=False)["base_exposure"].sum(numeric_only=True)
            quote_sum = view.groupby("Quote", dropna=False)["quote_exposure"].sum(numeric_only=True)
            
            # Map to buckets and add
            buckets_df["Net Total"] = (
                buckets_df["Symbol"].map(base_sum).fillna(0)
                + buckets_df["Symbol"].map(quote_sum).fillna(0)
            )

            st.dataframe(buckets_df)
                        
        




    
    
    if {"symbol", "pl", "net"}.issubset(view.columns) and not view.empty:
        pl_by_symbol = (
            view.groupby("symbol", dropna=False)["pl"]
            .sum(numeric_only=True)
            .reset_index()
            .sort_values("pl", ascending=True)
        )
        net_by_symbol = (
            view.groupby("symbol", dropna=False)["net"]
            .sum(numeric_only=True)
            .reset_index()
            .sort_values("net", ascending=True)
        )

        with tab2:
            
            coll, colr = st.columns(2, vertical_alignment="top")
            
            options = ["P/L", "Volume"]
            with colr:
                flex = st.container(
                    horizontal=True, 
                    horizontal_alignment="right", 
                    border=False, 
                    vertical_alignment="bottom",
                    height=100,
                )
                data_selection = flex.segmented_control(
                    "Data Selction", 
                    options, 
                    selection_mode="single",
                    default="P/L",
                    label_visibility="hidden",
                )

            with coll:
                flex = st.container(
                    horizontal=True, 
                    horizontal_alignment="left", 
                    border=False, 
                    vertical_alignment="bottom",
                    height=100,
                )
                flex.write(f"**{data_selection} by Symbol**")

            if data_selection == "P/L":
                st.bar_chart(pl_by_symbol, y="pl", x="symbol", horizontal=True)
            else:
                st.bar_chart(net_by_symbol, y="net", x="symbol", horizontal=True)

def dashboard_page():
    first_name = st.session_state.get("first_name", "there")
    st.subheader(f"Welcome, {first_name}", anchor=False)
    exposure_panel()  # render the auto-refreshing exposure panel

if __name__ == "__main__":
    dashboard_page()
