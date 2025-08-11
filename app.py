
import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Finance Dashboard", layout="wide")

def load_sample_vn30():
    try:
        p = "sample_vn30.csv"
        df = pd.read_csv(p, parse_dates=['date']).set_index('date')
        return df
    except Exception as e:
        st.error(f"Lỗi tải VN30: {e}")
        return pd.DataFrame()

def load_btc_data():
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": "30"}
    r = requests.get(url)
    data = r.json()
    prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
    prices['date'] = pd.to_datetime(prices['timestamp'], unit='ms')
    prices = prices.set_index('date')['price']
    return prices

st.title("Finance Dashboard")

vn30_data = load_sample_vn30()
btc_data = load_btc_data()

col1, col2 = st.columns(2)
with col1:
    st.subheader("VN30 Sample Data")
    st.line_chart(vn30_data['close'] if not vn30_data.empty else None)
with col2:
    st.subheader("Bitcoin (USD) - 30 ngày")
    st.line_chart(btc_data)

st.caption("Nguồn dữ liệu: CafeF (VN30), CoinGecko (Crypto)")
