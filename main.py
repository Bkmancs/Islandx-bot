import os
import requests
import asyncio
import threading
import time
import json
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.background import BackgroundScheduler


# 🔑 ENV
TOKEN = os.environ.get("TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

CHANNEL_ID = "@IslandXTenerife"


# 🌐 KEEP ALIVE
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot alive"

def run_web():
    app_web.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web).start()


# 💾 MEMORIA JSON
USER_FILE = "users.json"

def load_users():
    try:
        with open(USER_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(USER_FILE, "w") as f:
        json.dump(data, f)


USER_DATA = load_users()


# 🌍 ZONAS
ZONES = {
    "medano": {"lat": 28.0467, "lon": -16.5366, "name": "El Médano 🌬️"},
    "palm_mar": {"lat": 28.0065, "lon": -16.6805, "name": "Palm-Mar 🏝️"},
    "los_cristianos": {"lat": 28.0525, "lon": -16.7160, "name": "Los Cristianos 🌊"},
    "las_americas": {"lat": 28.0619, "lon": -16.7300, "name": "Las Américas 🏄"},
    "adeje": {"lat": 28.1210, "lon": -16.7260, "name": "Costa Adeje 🪂"},
    "teide": {"lat": 28.2724, "lon": -16.6425, "name": "Teide 🏔️"}
}


# 🧠 CACHE
CACHE = {}
FORECAST_CACHE = {}
CACHE_TIME = 600


# 🌤️ WEATHER
def get_weather(zone_key):
    try:
        z = ZONES[zone_key]
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={z['lat']}&lon={z['lon']}&appid={WEATHER_API_KEY}&units=metric"
        return requests.get(url, timeout=5).json()
    except:
        return None


def get_cached_weather(zone_key):
    now = time.time()

    if zone_key in CACHE:
        data, ts = CACHE[zone_key]
        if now - ts < CACHE_TIME:
            return data

    data = get_weather(zone_key)
    CACHE[zone_key] = (data, now)
    return data


# 🏄 ACTIVITY
def get_activity(wind, zone):
    kmh = wind * 3.6

    if zone == "teide":
        return "🥾 hiking / 🌌 astronomy"

    if kmh > 25:
        return "🔥 kitesurf"
    elif kmh > 15:
        return "🏄 surf"
    elif kmh > 8:
        return "🌊 paddle"
    else:
        return "🏝️ calm sea"


# 📍 INFO
def get_zone_info(zone_key):

    data = get_cached_weather(zone_key)
    if not data:
        return None

    return {
        "zone": ZONES[zone_key]["name"],
        "temp": data["main"]["temp"],
        "wind": data["wind"]["speed"],
        "desc": data["weather"][0]["description"],
    }


# 📊 RANKING
def get_ranking():

    ranking = []

    for z in ZONES:
        data = get_cached_weather(z)
        if not data:
            continue

        wind = data["wind"]["speed"]
        score = wind * 3.6

        ranking.append({
            "zone": ZONES[z]["name"],
            "score": score
        })

    ranking.sort(key=lambda x: x["score"], reverse=True)

    msg = "📊 Ranking condiciones\n\n"

    for i, r in enumerate(ranking, 1):
        msg += f"{i}. {r['zone']} → {round(r['score'],1)} km/h\n"

    return msg


# 🧠 ZONA
def normalize_zone(text):
    text = text.lower()

    if "medano" in text:
        return "medano"
    if "palm" in text:
        return "palm_mar"
    if "cristianos" in text:
        return "los_cristianos"
    if "americas" in text:
        return "las_americas"
    if "adeje" in text:
        return "adeje"
    if "teide" in text:
        return "teide"

    return None


# 🌍 MEMORIA USUARIO
def get_user(user_id):
    return USER_DATA.get(str(user_id), {})


def update_user(user_id, key, value):
    user_id = str(user_id)

    if user_id not in USER_DATA:
        USER_DATA[user_id] = {}

    USER_DATA[user_id][key] = value
    save_users(USER_DATA)


# 🌍 LANG (CON MEMORIA)
def get_lang(update):

    user_id = update.effective_user.id
    lang = (update.effective_user.language_code or "en")[:2]

    update_user(user_id, "lang", lang)

    return lang


# 💬 CHAT
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()
    user_id = update.effective_user.id

    lang = get_lang(update)
    user_data = get_user(user_id)

    zone = normalize_zone(text)

    # 🌍 guardar zona favorita si la menciona
    if zone:
        update_user(user_id, "favorite_zone", zone)

        info = get_zone_info(zone)

        msg = f"""
📍 {info['zone']}

🌡️ {info['temp']}°C
🌬️ {round(info['wind']*3.6,1)} km/h
☁️ {info['desc']}

👉 {get_activity(info['wind'], zone)}
"""

        await update.message.reply_text(msg)
        return

    # 📊 ranking
    if "ranking" in text or "condiciones" in text:
        await update.message.reply_text(get_ranking())
        return

    # 🏄 activities
    if "actividades" in text or "que hacer" in text:

        msg = "🏄 IslandX Live\n\n"

        for z in ZONES:
            info = get_zone_info(z)
            if info:
                msg += f"{info['zone']} → {round(info['wind']*3.6,1)} km/h\n"

        await update.message.reply_text(msg)
        return

    # 👋 saludo
    if any(x in text for x in ["hola", "hi", "hello"]):

        replies = {
            "es": "👋 Hola!",
            "en": "👋 Hi!",
            "de": "👋 Hallo!",
            "fr": "👋 Salut!"
        }

        await update.message.reply_text(replies.get(lang, "👋 Hello"))
        return

    await update.message.reply_text("🤖 Prueba: clima, ranking, actividades")


# 🚀 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    lang = get_lang(update)

    msg = {
        "es": "🌴 IslandX listo",
        "en": "🌴 IslandX ready",
        "de": "🌴 bereit",
        "fr": "🌴 prêt"
    }

    await update.message.reply_text(msg.get(lang, "🌴 ready"))


# 🔥 BEST SPOT
async def bestspot(update: Update, context: ContextTypes.DEFAULT_TYPE):

    best = None
    best_score = -1

    for z in ZONES:
        info = get_zone_info(z)
        if not info:
            continue

        score = info["wind"] * 3.6

        if score > best_score:
            best_score = score
            best = info

    if not best:
        await update.message.reply_text("⚠️ error")
        return

    await update.message.reply_text(f"""
🔥 BEST SPOT

📍 {best['zone']}
🌬️ {round(best_score,1)} km/h
""")


# 📘 HELP
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📘 Comandos:\n"
        "- clima en el médano\n"
        "- ranking\n"
        "- actividades\n"
        "- bestspot"
    )


# 🚀 MAIN
def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("bestspot", bestspot))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: None, "interval", hours=1)
    scheduler.start()

    print("🚀 bot running")
    app.run_polling()


if __name__ == "__main__":
    main()
