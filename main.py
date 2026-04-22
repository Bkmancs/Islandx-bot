import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# 🔑 ENV VARIABLES
TOKEN = os.environ.get("TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

CHANNEL_ID = "@IslandXTenerife"


# 🌍 ZONAS TENERIFE
ZONES = {
    "medano": {"lat": 28.0467, "lon": -16.5366, "name": "El Médano 🌬️"},
    "palm_mar": {"lat": 28.0065, "lon": -16.6805, "name": "Palm-Mar 🏝️"},
    "los_cristianos": {"lat": 28.0525, "lon": -16.7160, "name": "Los Cristianos 🌊"},
    "las_americas": {"lat": 28.0619, "lon": -16.7300, "name": "Las Américas 🏄"},
    "adeje": {"lat": 28.1210, "lon": -16.7260, "name": "Costa Adeje 🪂"},
    "teide": {"lat": 28.2724, "lon": -16.6425, "name": "Teide 🏔️"}
}


# 🌤️ CLIMA POR ZONA
def get_weather_zone(zone_key):
    z = ZONES[zone_key]
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={z['lat']}&lon={z['lon']}&appid={WEATHER_API_KEY}&units=metric"
    return requests.get(url).json()


# 🧠 ACTIVIDAD SEGÚN VIENTO
def get_activity(wind, zone_name):
    if wind >= 7:
        return f"🌬️ Kitesurf perfecto en {zone_name}"
    elif 4 <= wind < 7:
        return f"🏄 Surf recomendado en {zone_name}"
    elif 2 <= wind < 4:
        return f"🌊 Kayak / Paddle en {zone_name}"
    else:
        return f"🏝️ Agua tranquila en {zone_name}"


# 📍 INFO COMPLETA POR ZONA
def get_zone_full_info(zone_key):
    data = get_weather_zone(zone_key)

    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    desc = data["weather"][0]["description"]

    zone_name = ZONES[zone_key]["name"]
    activity = get_activity(wind, zone_name)

    return f"""
📍 {zone_name}

🌡️ {temp}°C
🌬️ {wind} m/s
☁️ {desc}

👉 {activity}
"""


# 🌤️ WEATHER POR ZONA
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:
        await update.message.reply_text(
            "📍 Usa: /weather medano | palm_mar | los_cristianos | las_americas | adeje | teide"
        )
        return

    zone_key = context.args[0].lower()

    if zone_key not in ZONES:
        await update.message.reply_text("❌ Zona no válida")
        return

    data = get_weather_zone(zone_key)

    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    desc = data["weather"][0]["description"]

    zone_name = ZONES[zone_key]["name"]
    activity = get_activity(wind, zone_name)

    message = f"""
🌍 {zone_name}

🌡️ {temp}°C
🌬️ {wind} m/s
☁️ {desc}

👉 {activity}
"""

    await update.message.reply_text(message)


# 🏄 ACTIVITIES CON CLIMA REAL
async def activities(update: Update, context: ContextTypes.DEFAULT_TYPE):

    zones = [
        "medano",
        "las_americas",
        "los_cristianos",
        "palm_mar",
        "adeje",
        "teide"
    ]

    message = "🏄 Tenerife Live Activities & Weather\n"

    for z in zones:
        message += "\n" + get_zone_full_info(z) + "\n"

    await update.message.reply_text(message)


# 🔥 BEST SPOT
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
    activity = get_activity(best_score, zone_name)

    message = f"""
🔥 BEST SPOT TODAY

📍 {zone_name}

🌡️ {temp}°C
🌬️ {best_score} m/s
☁️ {desc}

👉 {activity}
"""

    await update.message.reply_text(message)


# 👋 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 IslandX Smart Bot\n\n"
        "/weather medano\n"
        "/activities\n"
        "/bestspot"
    )


# 📡 POST CANAL (OPCIONAL)
def send_post(app):

    import asyncio

    async def send():
        data = get_weather_zone("medano")

        temp = data["main"]["temp"]
        wind = data["wind"]["speed"]
        desc = data["weather"][0]["description"]

        message = f"""
🌴 IslandX Tenerife Update

🌡️ {temp}°C
🌬️ {wind} m/s
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

    scheduler = BackgroundScheduler()
    scheduler.add_job(send_post, "cron", hour=7, minute=0, args=[app])
    scheduler.add_job(send_post, "cron", hour=10, minute=0, args=[app])
    scheduler.add_job(send_post, "cron", hour=14, minute=0, args=[app])
    scheduler.start()

    print("🚀 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
