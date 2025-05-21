import streamlit as st
import requests
import datetime
import feedparser
import re
import matplotlib.pyplot as plt
import pandas as pd
from textblob import TextBlob
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

nltk.download('vader_lexicon')

# === Streamlit App Configuration ===
st.set_page_config(
    page_title="🛡️ Crypto Scam Risk Analyzer",
    layout="wide",
    page_icon="🛡️"
)

# === Gradient Theme Styling ===
st.markdown("""
    <style>
        /* Base Colors */
        :root {
            --primary: #6CB4EE;  /* Light blue */
            --secondary: #7C4DFF;  /* Medium purple */
            --accent: #8A2BE2;  /* Blue violet */
            --background: #0f172a;  /* Deep navy */
            --sidebar: #1e293b;  /* Darker navy */
            --text: #f0f9ff;  /* Ice blue */
        }

        /* Main App Styling */
        .stApp {
            background: linear-gradient(135deg, var(--background) 60%, #1e3b8a);
            color: var(--text);
            font-family: 'Segoe UI', sans-serif;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background: var(--sidebar) !important;
            border-right: 2px solid var(--secondary);
            box-shadow: 4px 0 15px rgba(0,0,0,0.2);
        }

        /* Headers & Text */
        h1, h2, h3, h4, h5, h6 {
            color: var(--primary) !important;
            font-weight: 600;
            letter-spacing: -0.5px;
        }

        /* Inputs & Buttons */
        .stTextInput>div>div>input {
            background: #1e293b !important;
            color: var(--text) !important;
            border: 1px solid #334155 !important;
            border-radius: 8px !important;
            padding: 10px 15px !important;
        }
        
        .stButton>button {
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%) !important;
            color: white !important;
            border-radius: 12px !important;
            border: none !important;
            padding: 12px 24px !important;
            font-weight: 600;
            transition: all 0.3s ease !important;
        }

        /* Metrics & Cards */
        .stMetric {
            background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
            border-radius: 12px;
            padding: 15px;
            border-left: 4px solid var(--primary);
            transition: transform 0.3s ease;
        }

        /* Charts */
        .stPlot {
            background: #1e293b !important;
            border-radius: 12px;
            border: 1px solid #334155;
        }

        /* Hover Effects */
        .element-container:hover {
            transform: scale(1.01);
            transition: transform 0.3s ease;
        }
    </style>
""", unsafe_allow_html=True)

# === App Header ===
st.markdown("""
    <h1 style='text-align: center; 
    background: linear-gradient(135deg, #6CB4EE 0%, #8A2BE2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    🛡️ Cryptocurrency Scam Risk Analyzer</h1>
""", unsafe_allow_html=True)
st.markdown("---")

# === Sidebar Input ===
with st.sidebar:
    st.header("🔍 Analyze a Cryptocurrency")
    coin_name = st.text_input("Enter the coin name (e.g. bitcoin):", "bitcoin").lower()
    analyze_button = st.button("🚀 Run Analysis")

# === Helper Functions ===
def fetch_coin_data(coin_name):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_name}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("❌ Could not fetch data from CoinGecko")
        st.stop()

def fetch_historical_data(coin_name):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_name}/market_chart?vs_currency=usd&days=7"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("❌ Could not fetch historical data")
        st.stop()

def plot_trends(historical_data, coin_name):
    prices = historical_data['prices']
    market_caps = historical_data['market_caps']
    volumes = historical_data['total_volumes']

    df = pd.DataFrame({
        'date': [datetime.datetime.fromtimestamp(entry[0]/1000) for entry in prices],
        'price': [entry[1] for entry in prices],
        'market_cap': [entry[1] for entry in market_caps],
        'volume': [entry[1] for entry in volumes]
    })

    plt.style.use('dark_background')
    fig, axs = plt.subplots(3, 1, figsize=(10, 12))
    fig.patch.set_facecolor('#0f172a')
    
    # Price Trend
    axs[0].plot(df['date'], df['price'], label='Price (USD)', color='#6CB4EE')
    axs[0].set_title(f'{coin_name} - Price Trend', color='white')
    axs[0].grid(True, color='#1e293b')
    
    # Market Cap Trend
    axs[1].plot(df['date'], df['market_cap'], label='Market Cap', color='#7C4DFF')
    axs[1].set_title(f'{coin_name} - Market Cap Trend', color='white')
    axs[1].grid(True, color='#1e293b')
    
    # Volume Trend
    axs[2].plot(df['date'], df['volume'], label='Volume', color='#FF79C6')
    axs[2].set_title(f'{coin_name} - Volume Trend', color='white')
    axs[2].grid(True, color='#1e293b')
    
    plt.tight_layout()
    st.pyplot(fig)

def analyze_volume(volume):
    if volume < 10_000:
        return "🔴 Very low volume, 🚩 Big danger", True
    elif volume < 100_000:
        return "🟠 Low volume, 😐 Be cautious", True
    elif volume < 10_000_000:
        return "🟢 Healthy volume, ✅ Actively traded", False
    else:
        return "🟢 Very high volume, ⭐ Trusted & popular", False

def analyze_liquidity(volume, market_cap):
    if market_cap == 0:
        return "❗ Missing market cap data", True
    if volume / market_cap < 0.01:
        return "🚨 Low liquidity, Risk of price slippage", True
    else:
        return "✅ Good liquidity", False

def analyze_valuation(fdv, market_cap):
    if market_cap == 0 or fdv == 0:
        return "❗ Missing FDV or Market Cap data", True
    ratio = fdv / market_cap
    if ratio > 10:
        return "🚨 High inflation risk", True
    elif ratio > 5:
        return "⚠ Possible inflation risk", True
    else:
        return "✅ Normal valuation", False

def analyze_blacklist(coin_name, description):
    blacklist = ['scam', 'fraud', 'blacklist', 'free', 'guaranteed', 'investment', 'lottery', 'prize']
    for word in blacklist:
        if word in coin_name.lower() or word in description.lower():
            return "🚨 Coin name or description has suspicious keywords", True
    return "✅ Coin not on the blacklist", False

def check_suspicious_links(description):
    suspicious_words = ['guaranteed', 'double your money', 'safe investment']
    shortener_patterns = r'bit\.ly|tinyurl\.com|goo\.gl|t\.co'
    links = re.findall(r'https?://[^\s]+', description.lower())

    for word in suspicious_words:
        if word in description.lower():
            return "🚨 Description contains scam-like wording", True

    if any(re.search(shortener_patterns, link) for link in links):
        return "⚠ Description contains shortened or suspicious links", True

    return "✅ No suspicious links found in description", False

def check_social_links(coin_data):
    bad = False
    links = []
    if coin_data['links']['subreddit_url']:
        links.append(coin_data['links']['subreddit_url'])
    for link in links:
        try:
            response = requests.get(link, timeout=5)
            if response.status_code != 200:
                bad = True
        except:
            bad = True

    if bad:
        return "⚠ Reddit link is broken or suspicious", True
    return "✅ Reddit link is active", False

def fetch_reddit_posts(coin_name):
    url = f'https://www.reddit.com/r/cryptocurrency/search.json?q={coin_name}&restrict_sr=1&limit=10'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)

    sentiment_scores = []
    posts_list = []
    scam_flag = False
    if response.status_code == 200:
        posts = response.json()['data']['children']
        for post in posts:
            title = post['data']['title']
            posts_list.append(title)
            score = TextBlob(title).sentiment.polarity
            sentiment_scores.append(score)
            if score < -0.5:
                scam_flag = True

    average = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    return scam_flag, average, posts_list

def get_news_from_rss(coin_name):
    feed_url = "https://cointelegraph.com/rss"
    feed = feedparser.parse(feed_url)
    return [entry.title for entry in feed.entries if coin_name.lower() in entry.title.lower()][:5]

def analyze_news_sentiment(titles):
    sid = SentimentIntensityAnalyzer()
    total = 0
    count = 0
    scam_flag = False

    for title in titles:
        score = sid.polarity_scores(title)['compound']
        total += score
        count += 1
        if score < -0.5:
            scam_flag = True

    if count == 0:
        return "❌ No news found", 0, scam_flag
    avg = total / count
    if avg >= 0.5:
        sentiment = "🟢 News sentiment positive"
    elif avg <= -0.5:
        sentiment = "🔴 News sentiment negative"
    else:
        sentiment = "🟠 News sentiment neutral"
    return sentiment, avg, scam_flag

def check_coin_age(genesis_date):
    if not genesis_date:
        return "❗ Genesis date not available", False
    today = datetime.datetime.today()
    age_in_days = (today - datetime.datetime.strptime(genesis_date, "%Y-%m-%d")).days
    if age_in_days < 30:
        return "🔴 Coin is very new, 🚩 Potential risk", True
    return "🟢 Coin is not new, ✅ Safe", False

def analyze_price_volatility(historical_data):
    prices = [entry[1] for entry in historical_data['prices']]
    price_changes = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
    avg_volatility = sum(abs(change) for change in price_changes) / len(price_changes)
    if avg_volatility > 0.2:
        return "🚨 High price volatility, risk of pump and dump", True
    return "✅ Stable price volatility", False

def plot_risk_pie_chart(scam_score, total_checks):
    risk = scam_score
    safe = total_checks - scam_score
    labels = ['Risky', 'Safe']
    sizes = [risk, safe]
    colors = ['#FF79C6', '#8A2BE2']
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots()
    fig.patch.set_facecolor('#0f172a')
    ax.pie(sizes, labels=labels, colors=colors, 
          autopct='%1.1f%%', startangle=90, 
          textprops={'color': 'white'})
    ax.axis('equal')
    plt.title(f"Risk Analysis", color='#6CB4EE')
    st.pyplot(fig)

# === MAIN LOGIC ===
if analyze_button:
    with st.spinner("🔎 Fetching and analyzing coin data..."):
        coin_data = fetch_coin_data(coin_name)
        historical_data = fetch_historical_data(coin_name)

        description = coin_data['description']['en']
        volume = coin_data['market_data']['total_volume']['usd']
        market_cap = coin_data['market_data']['market_cap']['usd']
        fdv = coin_data['market_data']['fully_diluted_valuation']['usd']
        symbol = coin_data['symbol'].upper()
        name = coin_data['name']
        price = coin_data['market_data']['current_price']['usd']
        website = coin_data['links']['homepage'][0]
        genesis_date = coin_data.get('genesis_date', None)

        st.markdown("## 💰 Coin Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Price (USD)", f"${price:,.2f}")
        col2.metric("Market Cap", f"${market_cap:,.0f}")
        col3.markdown(f"🔗 [Official Website]({website})")
        st.caption(f"**Symbol:** {symbol} | **Genesis Date:** {genesis_date if genesis_date else 'N/A'}")

        st.markdown("---")
        st.markdown("## 📈 Market Trends")
        plot_trends(historical_data, coin_name)

        st.markdown("---")
        st.markdown("## 🧪 Risk Factor Analysis")
        checks = [
            analyze_volume(volume),
            analyze_liquidity(volume, market_cap),
            analyze_valuation(fdv, market_cap),
            analyze_blacklist(coin_name, description),
            check_suspicious_links(description),
            check_social_links(coin_data),
            check_coin_age(genesis_date),
            analyze_price_volatility(historical_data),
        ]

        scam_score = 0
        for msg, flag in checks:
            if flag:
                st.error(msg)
                scam_score += 1
            else:
                st.success(msg)

        st.markdown("---")
        st.markdown("## 📜 Reddit Sentiment")
        reddit_flag, reddit_avg, reddit_posts = fetch_reddit_posts(coin_name)
        st.write(f"🔍 Average Reddit Sentiment: `{reddit_avg:.2f}`")
        for post in reddit_posts[:5]:
            st.markdown(f"- {post}")
        if reddit_flag:
            st.warning("⚠ Negative sentiment detected")

        st.markdown("## 📰 News Sentiment")
        news_titles = get_news_from_rss(coin_name)
        news_sentiment, news_avg, news_flag = analyze_news_sentiment(news_titles)
        st.info(news_sentiment)
        for title in news_titles:
            st.markdown(f"- {title}")
        if news_flag:
            st.warning("⚠ Negative news sentiment detected")

        scam_score += int(reddit_flag) + int(news_flag)

        st.markdown("---")
        st.markdown("## 📊 Risk Overview")
        plot_risk_pie_chart(scam_score, len(checks) + 2)

        st.markdown("## 🏁 Final Verdict")
        if scam_score >= 5:
            st.error("🚨 This coin shows strong signs of being a scam! Be extremely cautious.")
        elif scam_score >= 3:
            st.warning("⚠ Some red flags are present. Proceed with caution.")
        else:
            st.success("✅ This coin appears safe based on current analysis.")

        st.markdown("---")
        st.caption("🔐 Data powered by CoinGecko and community sources. Always DYOR.")