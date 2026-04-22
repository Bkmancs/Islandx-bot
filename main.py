import os
import requests
import asyncio
import threading
import time
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.background import BackgroundScheduler

# 🔑 ENV
TOKEN = os.environ.get("TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

CHANNEL_ID = "@IslandXTenerife"

# 🌐 KEEP ALIVE (Render)
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot alive"

def run_web():
    app_web.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web).start()


# 🌍 ZONAS
ZONES = {
    "medano": {"lat": 28.0467, "lon": -16.5366, "name": "El Médano 🌬️"},
    "palm_mar": {"lat": 28.0065, "lon": -16.6805, "name": "Palm-Mar 🏝️"},
    "los_cristianos": {"lat": 28.0525, "lon": -16.7160, "name": "Los Cristianos 🌊"},
    "las_americas": {"lat": 28.0619, "lon": -16.7300, "name": "Las Américas 🏄"},
    "adeje": {"lat": 28.1210, "lon": -16.7260, "name": "Costa Adeje 🪂"},
    "teide": {"lat": 28.2724, "lon": -16.6425, "name": "Teide 🏔️"}
}


# 🧠 CACHE (reduce API calls)
CACHE = {}
CACHE_TIME = 600  # 10 min


def get_weather_zone(zone_key):
    try:
        z = ZONES[zone_key]
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={z['lat']}&lon={z['lon']}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        return res.json()
    except:
        return None


def get_cached_weather(zone_key):
    now = time.time()

    if zone_key in CACHE:
        data, ts = CACHE[zone_key]
        if now - ts < CACHE_TIME:
            return data

    data = get_weather_zone(zone_key)
    CACHE[zone_key] = (data, now)
    return data


# 🏄 ACTIVIDAD
def get_activity(wind, zone_name, zone_key):
    wind_kmh = wind * 3.6

    if zone_key == "teide":
        return "🥾 Senderismo / 🌌 Astrofotografía" if wind_kmh < 30 else "🌬️ Mucho viento"

    if wind_kmh >= 25:
        return f"🌬️ Kitesurf perfecto en {zone_name}"
    elif 15 <= wind_kmh < 25:
        return f"🏄 Surf bueno en {zone_name}"
    elif 8 <= wind_kmh < 15:
        return f"🌊 Paddle / kayak en {zone_name}"
    else:
        return f"🏝️ Mar tranquilo en {zone_name}"


# 📍 INFO
def get_zone_full_info(zone_key):
    data = get_cached_weather(zone_key)

    if not data:
        return "⚠️ Error obteniendo datos"

    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    desc = data["weather"][0]["description"]

    zone_name = ZONES[zone_key]["name"]
    activity = get_activity(wind, zone_name, zone_key)

    return f"""
📍 {zone_name}

🌡️ {temp}°C
🌬️ {round(wind*3.6,1)} km/h
☁️ {desc}

👉 {activity}
"""


# 🧠 NORMALIZAR ZONAS
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


# 🌍 START MULTI-IDIOMA
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    lang = (update.effective_user.language_code or "").lower()

    if lang.startswith("es"):
        msg = "🌴 IslandX Alerts\nTu asistente en Tenerife\nEscribe normal 😉"

    elif lang.startswith("en"):
        msg = "🌴 IslandX Alerts\nYour Tenerife assistant\nJust type 😉"

    elif lang.startswith("de"):
        msg = "🌴 IslandX Alerts\nDein Teneriffa-Assistent\nEinfach schreiben 😉"

    elif lang.startswith("fr"):
        msg = "🌴 IslandX Alerts\nTon assistant à Tenerife\nÉcris 😉"

    else:
        msg = "🌍 IslandX ready. Type anything 😉"

    await update.message.reply_text(msg)


# 💬 CHAT INTELIGENTE
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()
    lang = (update.effective_user.language_code or "en").lower()

    zone_key = normalize_zone(text)

    # 🌍 zona
    if zone_key:
        await update.message.reply_text(get_zone_full_info(zone_key))
        return

    # 🔥 mejor spot
    if any(x in text for x in ["mejor", "best", "spot", "donde"]):

        best_zone = None
        best_score = -1
        best_data = None

        for key in ZONES:
            data = get_cached_weather(key)
            if not data:
                continue

            wind = data["wind"]["speed"]

            if wind > best_score:
                best_score = wind
                best_zone = key
                best_data = data

        if not best_zone:
            await update.message.reply_text("⚠️ No data available")
            return

        await update.message.reply_text("🔥 BEST SPOT\n\n" + get_zone_full_info(best_zone))
        return

    # 🌊 actividades
    if any(x in text for x in ["actividades", "que hacer", "planes"]):

        msg = "🏄 IslandX Live\n"
        for z in ZONES:
            msg += "\n" + get_zone_full_info(z)

        await update.message.reply_text(msg)
        return

    # 👋 saludo
    if any(x in text for x in ["hola", "hi", "hello"]):

        replies = {
            "es": "👋 Hola! Pregúntame por clima o spots",
            "en": "👋 Hi! Ask me about weather or spots",
            "de": "👋 Hallo! Frag nach Wetter",
            "fr": "👋 Salut! Demande météo"
        }

        await update.message.reply_text(replies.get(lang[:2], "👋 Hello!"))
        return

    # ❓ fallback
    await update.message.reply_text(
        "🤖 No te entendí.\nPrueba: clima, mejor spot, actividades"
    )


# 🔥 BEST SPOT (FIX ROBUSTO)
async def bestspot(update: Update, context: ContextTypes.DEFAULT_TYPE):

    best_zone = None
    best_score = -1

    for key in ZONES:
        data = get_cached_weather(key)
        if not data:
            continue

        wind = data["wind"]["speed"]

        if wind > best_score:
            best_score = wind
            best_zone = key

    if not best_zone:
        await update.message.reply_text("⚠️ Error calculando spot")
        return

    await update.message.reply_text(get_zone_full_info(best_zone))


# 📘 HELP
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 IslandX Help\n\n"
        "• escribe clima en el médano\n"
        "• mejor spot\n"
        "• actividades\n"
    )


# 📡 AUTO POST
def send_post(app):

    async def send():
        data = get_cached_weather("medano")

        if not data:
            return

        temp = data["main"]["temp"]
        wind = data["wind"]["speed"]
        desc = data["weather"][0]["description"]

        message = f"""
🌴 IslandX Update

🌡️ {temp}°C
🌬️ {round(wind*3.6,1)} km/h
☁️ {desc}
"""

        await app.bot.send_message(chat_id=CHANNEL_ID, text=message)

    asyncio.run(send())


# 🚀 MAIN
def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("bestspot", bestspot))

    # 💬 chat libre
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler = BackgroundScheduler()
    scheduler.add_job(send_post, "cron", hour=7, minute=0, args=[app])
    scheduler.add_job(send_post, "cron", hour=14, minute=0, args=[app])
    scheduler.start()

    print("🚀 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
