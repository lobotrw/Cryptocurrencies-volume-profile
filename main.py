import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
import matplotlib.colors as mcolors
import streamlit as st

import vprofile as vp

# Set Page Configurations
st.set_page_config(
    page_title="Crypto Volume Profile",
    page_icon="📈",
    layout="wide"
)

# Get Data
with open('symbols.txt', 'r') as file:
    content = file.read()
    # Remove square brackets and split by comma
    symbols = [symbol.strip().strip("'") for symbol in content.split(',')]


@st.cache_data(ttl=600, show_spinner=False)
def get_data(option, period, interval):
    df = yf.download(
                tickers  = option,
                period   = period,
                interval = interval,
                auto_adjust = True,
                multi_level_index = False,   # flat columns: 'Close', 'Volume' (yfinance >= 0.2.48)
                progress = False
                )
    return df

col1, col2 = st.columns([2, 1])

col1.title("Cryptocurrencies Volume Profile")

with col2:
    st.write("#")
    option = st.selectbox(
        "Select Cryptocurrency:",
        (symbols))   
     
    period = st.selectbox(
        "Select Period:",
        vp.PERIODS)

    interval = st.selectbox(
        "Select Interval:",
        vp.VALID_INTERVALS[period],
        help="Only intervals Yahoo serves for this period (1h: last 730 days only).")

    pct_threshold = st.number_input("Volume Threshold %:", 1, 100, 94)

    volume_unit = st.radio("Volume units:", ["USD (as reported by Yahoo)", "Coin units (USD volume ÷ close)"],
                           help="Yahoo crypto volume is USD-denominated and has grown a lot over the years, "
                                "so on long periods USD volume over-weights recent prices.")

    mode = st.radio("Levels:", ["Current levels (all data)", "Walk-forward check"],
                    help="Current levels use all bars up to the latest one and are drawn only from the latest bar "
                         "forward. Walk-forward builds the profile on the first part of the period and draws its "
                         "levels only over the later, unseen part.")
    formation_pct = st.slider("Formation share %", 30, 90, 70, step=5) if mode == "Walk-forward check" else 100

progress_text = "Data Loading in progress. Please wait..."
my_bar        = col1.progress(0, text=progress_text)

df = get_data(option, period, interval)   # was downloaded 100 times inside the progress loop
my_bar.progress(100, text=progress_text)

my_bar.empty()
st.toast(f'Loaded {option}!', icon="✅")

data       = pd.DataFrame(df)

if data.empty or data['Close'].dropna().nunique() < 2:
    st.error(f"No usable data for {option} with period={period} and interval={interval}. "
             "Yahoo limits intraday history (1h: last 730 days), and some symbols are delisted.")
    st.stop()

for c in ("Close", "High", "Low"):
    data[c] = data[c].ffill()
data['Volume'] = data['Volume'].fillna(0)
vol_series = data['Volume'] if volume_unit.startswith("USD") else data['Volume'] / data['Close']

n_form = max(2, int(len(data) * formation_pct / 100))
formation = data.iloc[:n_form]
edges, bin_centers, volume_profile = vp.volume_profile(formation, 99, vol_series.iloc[:n_form])
vol_cutoff, levels = vp.high_volume_levels(bin_centers, volume_profile, pct_threshold)

# Create the plot
fig, (ax2, ax) = plt.subplots(1, 2, figsize=(20, 10), gridspec_kw={'width_ratios': [1, 4]}, dpi=150)

# Plot Currency chart
ax.plot(data.index, data['Close'], color='black', alpha=0.5)

current_close = float(data['Close'].iloc[-1])  # Get the most recent closing price
x_last = data.index[-1]
x_span = data.index[-1] - data.index[0]

if mode == "Walk-forward check":
    x_from, x_to = formation.index[-1], x_last
    ax.axvspan(data.index[0], x_from, color='gray', alpha=0.12, label='formation period (profile built here)')
else:
    # levels are only known at the latest bar: draw them from there forward, never over the past
    x_from, x_to = x_last, x_last + x_span * 0.08
    ax.set_xlim(data.index[0], x_to)

for price in levels:
    above = current_close > price
    ax.hlines(y=price, xmin=x_from, xmax=x_to, color='aqua' if above else 'red',
              linestyle='-' if above else '--', alpha=0.6, linewidth=4)

# Plot volume profile
cmap = mcolors.LinearSegmentedColormap.from_list("", ["aqua", "red"], gamma=0.7)

ax2.barh(bin_centers, volume_profile, height=edges[1]-edges[0], color=cmap(volume_profile/volume_profile.max()))
ax2.set_ylim(ax.get_ylim())
ax2.axvline(x=vol_cutoff, color='gray', linestyle='--', linewidth=2, label=f'{vp.ordinal(pct_threshold)} percentile')

# Set labels and title
ax.set_xlabel('Date')
ax.set_ylabel('Price (USD)')
ax2.set_ylabel('Price (USD)')
ax2.set_xlabel('Volume (USD)' if volume_unit.startswith("USD") else 'Volume (coin units)')
ax2.legend()
if mode == "Walk-forward check":
    ax.legend(loc='upper left')

profile_span = f"{formation.index[0]:%Y-%m-%d} – {formation.index[-1]:%Y-%m-%d}"
plt.title(f'{option} Volume Profile ({"walk-forward: " if mode != "Current levels (all data)" else ""}profile {profile_span})')

col1.pyplot(fig)
col1.caption(
    f"Profile built from {len(formation)} bars ({profile_span}); each bar's volume is spread over its "
    f"Low–High range. {len(levels)} levels above the {vp.ordinal(pct_threshold)} percentile: "
    + ", ".join(f"{p:,.6g}" for p in levels))
plt.close(fig)


col2.info('''A streamlined web application for analyzing cryptocurrency volume profiles.
            
    Users can select from a wide range of cryptocurrencies, 
    time periods, and intervals to visualize price movements 
    and trading volumes.
           
    The app features interactive charts that highlight 
    significant volume thresholds, helping traders and 
    investors identify key price levels and potential 
    support/resistance zones.''', icon="ℹ️")

st.divider()
st.subheader("About")
st.write('''Crypto Volume Profile App 2024\n
This site is for informational purposes only. The information on our website is not financial advice, and you should not consider it to be financial advice.''')

st.write("@VanHes1ng")

st.write('''TradingView: https://www.tradingview.com/u/VanHe1sing/\n 
Telegram: https://t.me/IvanKocherzhat\n 
GitHub: https://github.com/VanHes1ng\n
X: https://x.com/Van_He1sing            
''')


with open('./wave.css') as f:
    css = f.read()

st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
