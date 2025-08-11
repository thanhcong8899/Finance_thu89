"""
Finance Dashboard THU89 - Streamlit (light theme)
Features:
- Crypto (CoinGecko): BTC, ETH (live)
- VN30: scrape summary prices from CafeF (live) as fast option
- Fallback to sample data if live fetch fails
- Light UI theme
Usage:
- pip install -r requirements.txt
- streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time, json, os

st.set_page_config(page_title="Finance Dashboard THU89", layout="wide")

st.markdown("<h1 style='text-align:left;'>Finance Dashboard THU89</h1>", unsafe_allow_html=True)
st.markdown("**Light theme — Live: CoinGecko (crypto) + CafeF (VN30)**")

# Load config
cfg_path = os.path.join(os.path.dirname(__file__), 'config.json')
if os.path.exists(cfg_path):
    with open(cfg_path, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {"crypto":["bitcoin","ethereum"], "vn30_url": "https://cafef.vn/ty-gia.chn"}

# Helpers
def safe_fetch_crypto(coins):
    try:
        from pycoingecko import CoinGeckoAPI
        cg = CoinGeckoAPI()
        out = {}
        for coin in coins:
            hist = cg.get_coin_market_chart_by_id(id=coin, vs_currency='usd', days=30)
            prices = hist.get('prices', [])
            df = pd.DataFrame(prices, columns=['ts','price'])
            df['date'] = pd.to_datetime(df['ts'], unit='ms')
            df = df.set_index('date').resample('1H').mean().ffill()
            out[coin] = df[['price']]
        return out, 'live'
    except Exception as e:
        return None, str(e)

def safe_scrape_cafef(vn30_url):
    try:
        import requests
        from bs4 import BeautifulSoup
        r = requests.get(vn30_url, timeout=10, headers={'User-Agent':'Mozilla/5.0'})
        soup = BeautifulSoup(r.text, 'html.parser')
        # Attempt to find numeric prices on the page - look for table rows
        data = {}
        rows = soup.find_all('tr')
        for tr in rows:
            cols = tr.find_all(['td','th'])
            if len(cols) >= 2:
                code = cols[0].get_text(strip=True)
                price_text = cols[1].get_text(strip=True).replace(',','').strip()
                # remove non-numeric characters except dot
                price_text_clean = ''.join(ch for ch in price_text if (ch.isdigit() or ch=='.' or ch==','))
                price_text_clean = price_text_clean.replace(',','')
                try:
                    price = float(price_text_clean)
                    data[code] = price
                except:
                    continue
        if data:
            df = pd.DataFrame(list(data.items()), columns=['ticker','price']).set_index('ticker')
            return {'VN30_CAFEF': df}, 'live'
        else:
            return None, 'no-data'
    except Exception as e:
        return None, str(e)

# Sample data loaders (guarantee app runs)
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), 'sample_data')
def load_sample_crypto():
    p = os.path.join(SAMPLE_DIR, 'sample_crypto.csv')
    df = pd.read_csv(p, parse_dates=['date']).set_index('date')
    return {'bitcoin': df[['btc_price']].rename(columns={'btc_price':'price'}),
            'ethereum': df[['eth_price']].rename(columns={'eth_price':'price'})}

def load_sample_vn30():
    p = os.path.join(SAMPLE_DIR, 'sample_vn30.csv')
    if not os.path.exists(p):
        dates = pd.date_range(end=pd.Timestamp.today(), periods=10)
        df = pd.DataFrame({'date':dates, 'VCB':np.random.rand(10)*50+20, 'VNM':np.random.rand(10)*50+30})
        df.to_csv(p, index=False)
    df = pd.read_csv(p, parse_dates=['date']).set_index('date')
    out = {}
    for col in df.columns:
        out[col] = df[[col]].rename(columns={col:'price'})
    return out

# Try live fetch
crypto_data, crypto_src = safe_fetch_crypto(CONFIG.get('crypto', []))
vn30_data, vn30_src = safe_scrape_cafef(CONFIG.get('vn30_url','https://s.cafef.vn/thi-truong-chung-khoan.chn'))

# Fallbacks
if crypto_data is None:
    crypto_data = load_sample_crypto()
    crypto_src = 'sample'
if vn30_data is None:
    vn30_data = load_sample_vn30()
    vn30_src = 'sample'

# Indicators
def calc_ma_rsi(df, price_col='price'):
    df = df.copy().dropna()
    df['MA9'] = df[price_col].rolling(9).mean()
    df['MA21'] = df[price_col].rolling(21).mean()
    delta = df[price_col].diff()
    up = delta.clip(lower=0).rolling(14).mean()
    down = -delta.clip(upper=0).rolling(14).mean()
    rs = up/(down.replace(0, pd.NA))
    df['RSI14'] = 100 - 100/(1+rs)
    return df

# Layout
st.sidebar.header("Settings")
asset_tab = st.sidebar.radio("Chọn tab", ["Overview","Crypto","VN30"])

if asset_tab == "Overview":
    st.header("Snapshot overview")
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Crypto (source: %s)"%crypto_src)
        for coin, df in crypto_data.items():
            try:
                val = df['price'].dropna().iloc[-1]
                st.metric(label=coin.upper(), value=f"{val:,.2f}")
            except:
                st.write(coin, "n/a")
    with c2:
        st.subheader("VN30 (source: %s)"%vn30_src)
        keys = list(vn30_data.keys())[:6]
        for k in keys:
            try:
                if vn30_src == 'live':
                    val = vn30_data[k]['price'].iloc[0]
                else:
                    val = vn30_data[k]['price'].dropna().iloc[-1]
                st.metric(label=str(k), value=f"{val:,.2f}")
            except Exception as e:
                st.write(k, "n/a")

elif asset_tab == "Crypto":
    st.header("Crypto charts")
    coin = st.selectbox("Coin", list(crypto_data.keys()))
    df = crypto_data[coin].copy()
    df_ind = calc_ma_rsi(df)
    st.line_chart(df_ind[['price','MA9','MA21']].dropna())
    st.dataframe(df_ind.tail(20))
else:
    st.header("VN30 / Vietnam market")
    st.write("Source:", vn30_src)
    if vn30_src == 'live':
        df = list(vn30_data.values())[0]
        st.dataframe(df)
        st.bar_chart(df['price'].sort_values(ascending=False).head(20))
    else:
        tickers = list(vn30_data.keys())
        sel = st.multiselect("Chọn mã", tickers[:10], default=tickers[:4])
        if sel:
            data = pd.concat([vn30_data[s]['price'] for s in sel], axis=1)
            data.columns = sel
            st.line_chart(data)
            st.dataframe(data.tail(10))

st.markdown('---')
st.caption('Notes: demo app. For production use secure keys and respect site Terms of Service.')
