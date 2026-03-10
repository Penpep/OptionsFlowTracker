import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Options Flow Scanner", layout="wide", page_icon="📈")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'IBM Plex Mono', monospace !important;
        background-color: #080c10;
        color: #c8d8e8;
    }
    .stApp { background-color: #080c10; }
    
    .metric-box {
        background: #0a120a;
        border: 1px solid #1a2a1a;
        padding: 12px 20px;
        border-radius: 2px;
    }
    .bull { color: #00ff88; font-weight: 700; }
    .bear { color: #ff3a5c; font-weight: 700; }
    .neutral { color: #aaaaaa; }
    .call { color: #00c6ff; font-weight: 700; }
    .put { color: #ff3a5c; font-weight: 700; }
    .unusual { color: #f7c948; font-weight: 700; }
    .header-title {
        font-size: 26px;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #e8f8e8;
    }
    .header-sub {
        font-size: 11px;
        letter-spacing: 0.25em;
        color: #00ff88;
        opacity: 0.8;
    }
    div[data-testid="stDataFrame"] {
        background: #060a06;
        border: 1px solid #1a2a1a;
    }
    .stSelectbox > div, .stTextInput > div > div {
        background-color: #0a120a !important;
        border-color: #1a2a1a !important;
        color: #c8d8e8 !important;
        font-family: 'IBM Plex Mono', monospace !important;
    }
    .stButton > button {
        background-color: #0a2a0a;
        border: 1px solid #00ff88;
        color: #00ff88;
        font-family: 'IBM Plex Mono', monospace;
        letter-spacing: 0.12em;
        border-radius: 2px;
    }
    .stButton > button:hover {
        background-color: #0d3a0d;
        border-color: #00ff88;
        color: #00ff88;
    }
</style>
""", unsafe_allow_html=True)

WATCHLIST = ["SPY","QQQ","AAPL","NVDA","TSLA","MSFT","META","AMZN","GOOGL","AMD","COIN","PLTR","HOOD","NFLX","GS","BA","MSTR","SOFI","BABA","DIS"]

def premium_label(val):
    if not val or val == 0:
        return "N/A"
    if val >= 1_000_000:
        return f"${val/1_000_000:.2f}M"
    if val >= 1_000:
        return f"${val/1_000:.0f}K"
    return f"${val:.0f}"

def sentiment_from_delta(delta, contract_type):
    if contract_type == "call":
        if delta > 0.5: return "BULLISH"
        if delta > 0.3: return "NEUTRAL"
        return "BEARISH"
    elif contract_type == "put":
        if delta < -0.5: return "BEARISH"
        if delta < -0.3: return "NEUTRAL"
        return "BULLISH"
    return "NEUTRAL"

def fetch_options_flow(ticker, api_key):
    url = f"https://api.polygon.io/v3/snapshot/options/{ticker}?limit=50&apiKey={api_key}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("status") == "ERROR" or "error" in data:
            return None, data.get("error", "API error — check your key or plan tier.")
        
        results = data.get("results", [])
        rows = []
        for item in results:
            det = item.get("details", {})
            greeks = item.get("greeks", {})
            day = item.get("day", {})

            contract_type = det.get("contract_type", "call")
            strike = det.get("strike_price", 0)
            exp = det.get("expiration_date", "N/A")
            vol = day.get("volume", 0)
            oi = item.get("open_interest", 1) or 1
            vwap = day.get("vwap", 0)
            premium = vol * vwap * 100
            delta = greeks.get("delta", 0) or 0
            iv = item.get("implied_volatility", 0)
            voi = round(vol / oi, 1)
            unusual = vol > oi * 3 or premium > 500_000
            sentiment = sentiment_from_delta(delta, contract_type)

            if vol == 0:
                continue

            rows.append({
                "⚡": "⚡" if unusual else "",
                "Ticker": ticker,
                "Type": contract_type.upper(),
                "Strike": f"${strike}",
                "Expiry": exp,
                "Premium": premium_label(premium),
                "Volume": int(vol),
                "OI": int(oi),
                "V/OI": f"{voi}x",
                "IV": f"{iv*100:.1f}%" if iv else "N/A",
                "Sentiment": sentiment,
                "_premium_val": premium,
                "_unusual": unusual,
                "_sentiment": sentiment,
                "_type": contract_type.upper(),
            })

        return rows, None
    except Exception as e:
        return None, str(e)

# ── Layout ──────────────────────────────────────────────────────────────────

col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown('<div class="header-sub">POLYGON.IO — LIVE OPTIONS DATA</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-title">OPTIONS FLOW SCANNER</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ CONFIG")
    api_key = st.text_input("Polygon.io API Key", type="password", placeholder="paste your key here...")
    st.markdown("---")
    ticker = st.selectbox("Ticker", WATCHLIST)
    st.markdown("---")
    st.markdown("### FILTERS")
    type_filter = st.selectbox("Contract Type", ["ALL", "CALL", "PUT"])
    sentiment_filter = st.selectbox("Sentiment", ["ALL", "BULLISH", "BEARISH", "NEUTRAL"])
    unusual_only = st.checkbox("⚡ Unusual Activity Only")
    st.markdown("---")
    auto_refresh = st.checkbox("Auto-refresh (15s)", value=False)
    refresh_btn = st.button("🔄 FETCH NOW")

# ── Main ─────────────────────────────────────────────────────────────────────

if not api_key:
    st.markdown("""
    <div style='text-align:center; padding: 60px; color: #2a5a2a; letter-spacing: 0.15em;'>
        <div style='font-size:32px; margin-bottom:16px;'>📡</div>
        <div style='font-size:13px;'>ENTER YOUR POLYGON.IO API KEY IN THE SIDEBAR TO BEGIN</div>
        <div style='font-size:10px; margin-top:12px; color:#1a3a1a;'>
            Free key at polygon.io · Delayed data on free tier · Real-time on Starter ($29/mo)
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    if refresh_btn or auto_refresh:
        with st.spinner(f"Fetching options flow for {ticker}..."):
            rows, err = fetch_options_flow(ticker, api_key)

        if err:
            st.error(f"⚠ {err}")
        elif rows:
            df = pd.DataFrame(rows)

            # Sentiment stats
            bull = sum(1 for r in rows if r["_sentiment"] == "BULLISH")
            bear = sum(1 for r in rows if r["_sentiment"] == "BEARISH")
            total = bull + bear or 1
            bull_pct = round(bull / total * 100)

            # Metrics row
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Contracts", len(rows))
            m2.metric("⚡ Unusual", sum(1 for r in rows if r["_unusual"]))
            m3.metric("🟢 Bullish", f"{bull_pct}%")
            m4.metric("🔴 Bearish", f"{100-bull_pct}%")
            m5.metric("Updated", datetime.now().strftime("%H:%M:%S"))

            st.progress(bull_pct / 100)

            # Apply filters
            if type_filter != "ALL":
                df = df[df["_type"] == type_filter]
            if sentiment_filter != "ALL":
                df = df[df["_sentiment"] == sentiment_filter]
            if unusual_only:
                df = df[df["_unusual"] == True]

            st.markdown(f"<div style='font-size:10px; color:#2a5a2a; letter-spacing:0.15em; margin-bottom:8px;'>{len(df)} CONTRACTS SHOWN</div>", unsafe_allow_html=True)

            # Display table (drop internal cols)
            display_df = df.drop(columns=["_premium_val", "_unusual", "_sentiment", "_type"])
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "⚡": st.column_config.TextColumn(width="small"),
                    "Volume": st.column_config.NumberColumn(format="%d"),
                    "OI": st.column_config.NumberColumn(format="%d"),
                }
            )
        else:
            st.warning("No flow data returned — market may be closed or no volume today.")

        if auto_refresh:
            time.sleep(15)
            st.rerun()
    else:
        st.markdown("""
        <div style='text-align:center; padding: 40px; color: #2a4a2a; letter-spacing: 0.15em;'>
            <div style='font-size:13px;'>PRESS "FETCH NOW" OR ENABLE AUTO-REFRESH TO START</div>
        </div>
        """, unsafe_allow_html=True)