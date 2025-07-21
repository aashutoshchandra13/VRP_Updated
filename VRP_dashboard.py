# Streamlit + NSEPython based app to calculate IV Percentile, Realized Volatility, and VRP for NIFTY

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from nsepython import index_history, nse_fno, oi_chain_builder, expiry_list
import matplotlib.pyplot as plt

def run_dashboard():
    # -----------------------
    # CONFIG
    # -----------------------
    symbol = "NIFTY 50"
    oi_symbol = "NIFTY"
    vix_symbol = "INDIA VIX"
    start_date = "20-Jun-2025"
    end_date = datetime.now().strftime("%d-%b-%Y")

    # -----------------------
    # DATA FETCHING
    # -----------------------
    # INDIA VIX historical data
    vix_df = index_history(vix_symbol, start_date, end_date)
    vix_df["CLOSE"] = pd.to_numeric(vix_df["CLOSE"], errors='coerce')
    vix_df["HistoricalDate"] = pd.to_datetime(vix_df["HistoricalDate"], dayfirst=True)
    vix_df.sort_values("HistoricalDate", inplace=True)
    vix_today = vix_df["CLOSE"].iloc[-1]

    # NIFTY spot price
    spot = nse_fno(oi_symbol)["underlyingValue"]
    try:
        spot_float = float(spot)
    except:
        spot_float = None

    # Option Chain for IV
    try:
        oi_data, ltp, _ = oi_chain_builder(oi_symbol, expiry_choice, "full")
        oi_data["Strike Price"] = pd.to_numeric(oi_data["Strike Price"])
        oi_data["CALLS_IV"] = pd.to_numeric(oi_data["CALLS_IV"], errors='coerce')
        oi_data["PUTS_IV"] = pd.to_numeric(oi_data["PUTS_IV"], errors='coerce')

        atm_strike = round(ltp / 50) * 50
        atm_row = oi_data[oi_data["Strike Price"] == atm_strike]
        atm_iv_calls = atm_row["CALLS_IV"].mean()
        atm_iv_puts = atm_row["PUTS_IV"].mean()
        avg_iv = (atm_iv_calls + atm_iv_puts) / 2
    except Exception as e:
        st.error(f"Option chain fetch failed: {e}")
        avg_iv = None
        atm_strike = None

    # REALIZED VOLATILITY
    nifty_close = index_history(symbol, start_date, end_date)
    nifty_close["HistoricalDate"] = pd.to_datetime(nifty_close["HistoricalDate"], dayfirst=True)
    nifty_close.sort_values("HistoricalDate", inplace=True)
    nifty_close["CLOSE"] = pd.to_numeric(nifty_close["CLOSE"], errors='coerce')
    nifty_close["log_return"] = np.log(nifty_close["CLOSE"] / nifty_close["CLOSE"].shift(1))
    nifty_close["RV"] = nifty_close["log_return"].rolling(rv_window).std() * np.sqrt(252) * 100
    rv_today = nifty_close["RV"].iloc[-1]

    # VRP
    vrp = avg_iv - rv_today if avg_iv is not None else None

    # -----------------------
    # DISPLAY
    # -----------------------
    st.title("NIFTY Volatility Risk Premium (VRP) Dashboard")

    if spot_float is not None:
        st.metric("📈 NIFTY Spot", f"{spot_float:.2f}")
    else:
        st.metric("📈 NIFTY Spot", "Data not available")

    st.metric("🌀 INDIA VIX", f"{float(vix_today):.2f}")
    st.metric(f"📉 Realized Volatility ({rv_window}D)", f"{float(rv_today):.2f} %")

    if avg_iv is not None:
        st.metric("⚡ Avg ATM IV", f"{avg_iv:.2f} %")
        st.metric("🧮 VRP (IV - RV)", f"{vrp:.2f} %", delta=f"{vrp - vrp_threshold:.2f} vs threshold")
    else:
        st.warning("Could not compute IV due to missing option chain data.")


# -----------------------
# SIDEBAR
# -----------------------
st.sidebar.title("Settings")

# Expiry selector
try:
    all_expiries = expiry_list("NIFTY")
    expiry_choice = st.sidebar.selectbox("Select Expiry", all_expiries)
except Exception as e:
    st.sidebar.error(f"Error fetching expiries: {e}")
    expiry_choice = "latest"

rv_window = st.sidebar.slider("RV Lookback Days", min_value=10, max_value=60, value=20)
vrp_threshold = st.sidebar.slider("VRP Threshold (%)", min_value=0.0, max_value=5.0, value=1.0, step=0.1)

# -----------------------
# REFRESH BUTTON
# -----------------------
if st.sidebar.button("🔄 Refresh Data"):
    run_dashboard()
else:
    st.info("Click 'Refresh Data' to update the dashboard.")
