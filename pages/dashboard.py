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

if "kpi_prev" not in st.session_state:
    st.session_state.kpi_prev = {
        "pl": None,     
        "notional": None,  
        "margin": None,  
    }

# -------------------------------#
# Helpers
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


# -------------------------------#
# Auto-refresh panel as a fragment
# -------------------------------#
@st.fragment(run_every=5)  # seconds; adjust cadence as needed
def exposure_panel():
    accounts_input = ACCOUNTS or []
    st.caption(f"Accounts from secrets → {accounts_input}")

    with st.spinner("Fetching…"):
        items, client_code, broker_user, used_body = fetch_positions(accounts_input)

    if not items:
        st.error("No positions returned. Tip: set [centroid].accounts to ['CLIENT tem_b'] or leave it empty to fetch all visible.")
        return

    df = to_df(items)
    if df.empty:
        st.warning("Empty DataFrame after normalization.")
        return

    # ----- KPIs with deltas -----
    # Current values
    curr_pl = float(df["pl"].sum(skipna=True))
    if "notional" in df.columns and df["notional"].notna().any():
        curr_notional = float(df["notional"].sum(skipna=True))
    else:
        curr_notional = float((df["net"].abs() * df["avg_px"]).sum(skipna=True)) if {"net","avg_px"}.issubset(df.columns) else 0.0
    
    # Pull previous values from session
    prev_pl       = st.session_state.kpi_prev.get("pl")
    prev_notional = st.session_state.kpi_prev.get("notional")
    
    # Compute *numeric* deltas (None on first run => no arrow)
    delta_pl_num       = None if prev_pl is None else curr_pl - prev_pl
    delta_notional_num = None if prev_notional is None else curr_notional - prev_notional
    
    k = st.columns(3)
    with k[0]:
        with st.container(border=True):
            st.metric(
                "Floating P/L",
                fmt_money(curr_pl),                       # formatted value
                delta=None if delta_pl_num is None else delta_pl_num,   # numeric delta
                delta_color="normal",
            )
    with k[1]:
        with st.container(border=True):
            st.metric(
                "Notional Volume",
                fmt_money(curr_notional),
                delta=None if delta_notional_num is None else delta_notional_num,
                delta_color="normal",
            )
    with k[2]:
        with st.container(border=True):
            if "margin" in df.columns and df["margin"].notna().any():
                curr_margin = float(df["margin"].sum(skipna=True))
                # If you want margin delta later, uncomment:
                # prev_margin = st.session_state.kpi_prev.get("margin")
                # delta_margin_num = None if prev_margin is None else curr_margin - prev_margin
                st.metric("Utilised Margin", fmt_money(curr_margin))
                # st.session_state.kpi_prev["margin"] = curr_margin
            else:
                st.metric("Utilised Margin", "$0.00")
    
    # Persist *after* rendering
    st.session_state.kpi_prev["pl"] = curr_pl
    st.session_state.kpi_prev["notional"] = curr_notional

    st.divider()

    # Filters
    symbols = sorted(df["symbol"].dropna().astype(str).unique())
    takers  = sorted(df["taker"].dropna().astype(str).unique())

    col1, col2 = st.columns(2, vertical_alignment="top")
    with col1:
        symbol_sel = st.selectbox("Symbols", options=["(All)"] + symbols, index=0)
    with col2:
        taker_sel = st.selectbox("Platforms", options=["(All)"] + takers, index=0)

    # Apply filters
    view = df.copy()
    if symbol_sel != "(All)":
        view = view[view["symbol"] == symbol_sel]
    if taker_sel != "(All)":
        view = view[view["taker"] == taker_sel]

    # Enforce numeric types (important for sorting)
    for c in ["net", "avg_px", "pl", "notional", "base_exposure", "quote_exposure", "margin"]:
        if c in view.columns:
            view[c] = pd.to_numeric(view[c], errors="coerce").round(2)

    view = view.sort_values(by="pl", key=lambda s: s.abs(), ascending=False)

    if view.empty:
        st.info("No positions for the selected symbol / platform.")
    else:
        st.dataframe(view, use_container_width=True, hide_index=True)

    # Charts (horizontal bars)
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

        st.divider()
        st.write("**Profit / Loss by Symbol**")
        st.bar_chart(pl_by_symbol, y="pl", x="symbol", horizontal=False, use_container_width=True)

        st.write("**Exposure by Symbol (Volume)**")
        st.bar_chart(net_by_symbol, y="net", x="symbol", horizontal=False, use_container_width=True)


# -------------------------------#
# Page entrypoint
# -------------------------------#
def dashboard_page():
    first_name = st.session_state.get("first_name", "there")
    st.subheader(f"Welcome, {first_name}", anchor=False)
    exposure_panel()  # render the auto-refreshing exposure panel


if __name__ == "__main__":
    dashboard_page()
