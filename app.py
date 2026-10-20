
import os
from flask import Flask, jsonify, render_template
from flask_cors import CORS
import yfinance as yf
import requests
import random
from datetime import datetime
import pytz
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

# เตรียมตัววิเคราะห์อารมณ์ข่าว
nltk.download('vader_lexicon', quiet=True)

app = Flask(__name__)
CORS(app)
sia = SentimentIntensityAnalyzer()

# ใส่ API Key จาก newsapi.org ที่นี่เพื่อให้วิเคราะห์ข่าวได้
NEWS_API_KEY = 'YOUR_NEWS_API_KEY' 
TRACKED_STOCKS = ['SOFI', 'PLTR', 'NIO', 'MARA', 'AMD', 'F', 'PENN', 'LCID', 'TSLA', 'NVDA']

def get_sentiment_score(ticker):
    try:
        url = f'https://newsapi.org/v2/everything?q={ticker}+stock&sortBy=publishedAt&apiKey={NEWS_API_KEY}'
        response = requests.get(url).json()
        articles = response.get('articles', [])
        if not articles: return 0, "ไม่มีข่าวเด่น"
        scores = [sia.polarity_scores(art['title'])['compound'] for art in articles[:5]]
        return sum(scores) / len(scores), articles[0]['title']
    except: return 0, "ไม่สามารถเข้าถึงแหล่งข่าวได้"

def omniscient_weekly_analysis(ticker, price):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        avg_vol = info.get('averageVolume', 1000000)
        current_vol = info.get('volume', 0)
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
        history = stock.history(period="5d")
        if len(history) < 2: return None
        price_change = ((history['Close'].iloc[-1] - history['Close'].iloc[-2]) / history['Close'].iloc[-2]) * 100
        trend = 1 if price_change > 0 else -1
        sentiment_score, headline = get_sentiment_score(ticker)
        final_direction = 'Call' if (trend == 1 and sentiment_score >= -0.1) or (sentiment_score > 0.3) else 'Put'
        strike = round(price * 1.04, 2) if final_direction == 'Call' else round(price * 0.96, 2)
        score = 40
        reasons = []
        if vol_ratio > 2.0:
            score += 30
            reasons.append("Whale Flow ตรวจพบรายใหญ่")
        elif vol_ratio > 1.2:
            score += 15
            reasons.append("ปริมาณการเทรดปกติ")
        else:
            reasons.append("Volume ต่ำ (ความเสี่ยงสูง)")
        if abs(sentiment_score) > 0.4:
            score += 25
            reasons.append("ข่าวสารส่งผลรุนแรง")
        elif abs(sentiment_score) > 0.1:
            score += 10
            reasons.append("มีข่าวสนับสนุน")
        else:
            reasons.append("ไม่มีปัจจัยข่าวเด่น")
        if abs(price_change) > 1.2:
            score += 15
            reasons.append("โมเมนตัมรายสัปดาห์แข็งแกร่ง")
        else:
            reasons.append("ราคายังไม่มีทิศทางชัดเจน")
        score += 10
        reasons.append("Optimized Weekly Strike")
        final_win_rate = min(score, 97)
        if final_win_rate >= 85: verdict = "🔥 STRONG BUY"
        elif final_win_rate >= 70: verdict = "⚡ SPECULATIVE"
        else: verdict = "❌ AVOID"
        return {
            "ticker": ticker, "price": price, "type": final_direction,
            "strike": strike, "winRate": f"{final_win_rate}%",
            "reason": " + ".join(reasons), "verdict": verdict, "news": headline
        }
    except: return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    tz_th = pytz.timezone('Asia/Bangkok')
    now_th = datetime.now(tz_th).strftime('%Y-%m-%d %H:%M:%S')
    results = []
    for symbol in TRACKED_STOCKS:
        try:
            ticker_data = yf.Ticker(symbol)
            current_price = ticker_data.fast_info['last_price']
            data = omniscient_weekly_analysis(symbol, round(current_price, 2))
            if data: results.append(data)
        except: continue 
    return jsonify({"status": "open", "time_th": now_th, "data": results})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
