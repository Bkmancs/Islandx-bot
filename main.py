import os
import requests
import asyncio
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
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


# 🧠 NORMALIZAR TEXTO USUARIO
def normalize_zone(text):
    text = text.lower().replace("_", " ").strip()

    mapping = {
        "medano": "medano",
        "el medano": "medano",

        "palm mar": "palm_mar",
        "palm-mar": "palm_mar",

        "los cristianos": "los_cristianos",

        "las americas": "las_americas",
        "americas": "las_americas",

        "adeje": "adeje",

        "teide": "teide"
    }

    return mapping.get(text, None)


# 🌤️ CLIMA
def get_weather_zone(zone_key):
    z = ZONES[zone_key]
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={z['lat']}&lon={z['lon']}&appid={WEATHER_API_KEY}&units=metric"
    return requests.get(url).json()


# 🏄 ACTIVIDAD INTELIGENTE
def get_activity(wind, zone_name, zone_key):
    wind_kmh = wind * 3.6

    if zone_key == "teide":
        if wind_kmh > 30:
            return "🌬️ Condiciones ventosas, precaución en senderos"
        else:
            return "🥾 Senderismo recomendado / 🌌 Astrofotografía nocturna"

    if wind_kmh >= 25:
        return f"🌬️ Kitesurf perfecto en {zone_name}"
    elif 15 <= wind_kmh < 25:
        return f"🏄 Buenas condiciones de surf en {zone_name}"
    elif 8 <= wind_kmh < 15:
        return f"🌊 Ideal para kayak/paddle en {zone_name}"
    else:
        return f"🏝️ Mar tranquilo en {zone_name}"


# 📍 INFO COMPLETA
def get_zone_full_info(zone_key):
    data = get_weather_zone(zone_key)

    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    desc = data["weather"][0]["description"]

    zone_name = ZONES[zone_key]["name"]
    activity = get_activity(wind, zone_name, zone_key)

    wind_kmh = round(wind * 3.6, 1)

    return f"""
📍 {zone_name}

🌡️ {temp}°C
🌬️ {wind_kmh} km/h
☁️ {desc}

👉 {activity}
"""


# 🌤️ /weather
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:
        await update.message.reply_text("📍 Ejemplo: /weather los cristianos")
        return

    zone_input = " ".join(context.args)
    zone_key = normalize_zone(zone_input)

    if not zone_key:
        await update.message.reply_text("❌ Zona no reconocida. Usa /help")
        return

    data = get_weather_zone(zone_key)

    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    desc = data["weather"][0]["description"]

    zone_name = ZONES[zone_key]["name"]
    activity = get_activity(wind, zone_name, zone_key)

    wind_kmh = round(wind * 3.6, 1)

    message = f"""
🌍 {zone_name}

🌡️ {temp}°C
🌬️ {wind_kmh} km/h
☁️ {desc}

👉 {activity}
"""

    await update.message.reply_text(message)


# 🏄 /activities
async def activities(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = "🏄 Tenerife Live Conditions\n"

    for z in ZONES:
        message += "\n" + get_zone_full_info(z) + "\n"

    await update.message.reply_text(message)


# 🔥 /bestspot
async def bestspot(update: Update, context: ContextTypes.DEFAULT_TYPE):

    best_zone = None
    best_score = -1
    best_data = None

    for key in ZONES:
        data = get_weather_zone(key)
        wind = data["wind"]["speed"]

        if wind > best_score:
            best_score = wind
            best_zone = key
            best_data = data

    temp = best_data["main"]["temp"]
    desc = best_data["weather"][0]["description"]

    zone_name = ZONES[best_zone]["name"]
    activity = get_activity(best_score, zone_name, best_zone)

    wind_kmh = round(best_score * 3.6, 1)

    message = f"""
🔥 BEST SPOT NOW

📍 {zone_name}

🌡️ {temp}°C
🌬️ {wind_kmh} km/h
☁️ {desc}

👉 {activity}
"""

    await update.message.reply_text(message)


# 📘 /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 IslandX Help\n\n"
        "/weather <zona>\n"
        "Ej: /weather los cristianos\n\n"
        "/activities → Todas las zonas\n"
        "/bestspot → Mejor spot ahora\n\n"
        "Zonas: Médano, Palm-Mar, Los Cristianos, Las Américas, Adeje, Teide"
    )


# 👋 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌴 IslandX Alerts\n\n"
        "Tu asistente en Tenerife\n\n"
        "🌤️ Clima por zona\n"
        "🏄 Actividades en tiempo real\n"
        "🔥 Mejor spot del momento\n\n"
        "Usa /help para comenzar"
    )


# 📡 AUTO POST
def send_post(app):

    async def send():
        data = get_weather_zone("medano")

        temp = data["main"]["temp"]
        wind = data["wind"]["speed"]
        desc = data["weather"][0]["description"]

        wind_kmh = round(wind * 3.6, 1)

        message = f"""
🌴 IslandX Update

🌡️ {temp}°C
🌬️ {wind_kmh} km/h
☁️ {desc}
"""

        await app.bot.send_message(chat_id=CHANNEL_ID, text=message)

    asyncio.run(send())


# 🔧 MAIN
def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("activities", activities))
    app.add_handler(CommandHandler("bestspot", bestspot))
    app.add_handler(CommandHandler("help", help_command))

    scheduler = BackgroundScheduler()
    scheduler.add_job(send_post, "cron", hour=7, minute=0, args=[app])
    scheduler.add_job(send_post, "cron", hour=10, minute=0, args=[app])
    scheduler.add_job(send_post, "cron", hour=14, minute=0, args=[app])
    scheduler.start()

    print("🚀 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
