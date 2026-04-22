import os
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# 🔑 VARIABLES DE ENTORNO (RENDER)
TOKEN = os.environ.get("TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

# 📡 CANAL
CHANNEL_ID = "@IslandXTenerife"


# 🌍 TRADUCCIONES
TEXTS = {
    "es": {
        "weather": "🌤️ Clima en Tenerife",
        "activities": "🏄 Actividades en Tenerife",
        "update": "🌴 Actualización IslandX Tenerife"
    },
    "en": {
        "weather": "🌤️ Tenerife Weather",
        "activities": "🏄 Tenerife Activities",
        "update": "🌴 IslandX Tenerife Update"
    },
    "fr": {
        "weather": "🌤️ Météo à Tenerife",
        "activities": "🏄 Activités à Tenerife",
        "update": "🌴 Mise à jour IslandX Tenerife"
    },
    "de": {
        "weather": "🌤️ Wetter in Teneriffa",
        "activities": "🏄 Aktivitäten auf Teneriffa",
        "update": "🌴 IslandX Teneriffa Update"
    },
    "nl": {
        "weather": "🌤️ Weer op Tenerife",
        "activities": "🏄 Activiteiten op Tenerife",
        "update": "🌴 IslandX Tenerife Update"
    }
}


# 🌍 CLIMA
def get_weather_by_coords(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    return requests.get(url).json()


# 🌤️ WEATHER (ES por defecto)
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = "es"

    data = get_weather_by_coords(28.2916, -16.6291)

    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    desc = data["weather"][0]["description"]

    message = f"""
{TEXTS[lang]["weather"]}

🌡️ {temp}°C
🌬️ {wind} m/s
☁️ {desc}
"""

    await update.message.reply_text(message)


# 🌤️ WEATHER EN
async def weather_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_weather_by_coords(28.2916, -16.6291)

    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    desc = data["weather"][0]["description"]

    message = f"""
{TEXTS["en"]["weather"]}

🌡️ {temp}°C
🌬️ {wind} m/s
☁️ {desc}
"""

    await update.message.reply_text(message)


# 🏄 ACTIVITIES
async def activities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
🏄 Tenerife Activities

🌬️ El Médano → Kite / Windsurf
🌊 Los Cristianos → Kayak
🏝️ Palm-Mar → Snorkel / Paddle
🏄 Las Américas → Surf
🪂 Costa Adeje → Paragliding
"""
    await update.message.reply_text(message)


# 📡 POST AUTOMÁTICO (STABLE VERSION)
def send_weather_post_sync(app):
    async def send():
        data = get_weather_by_coords(28.2916, -16.6291)

        temp = data["main"]["temp"]
        wind = data["wind"]["speed"]
        desc = data["weather"][0]["description"]

        message = f"""
🌴 IslandX Tenerife Update

🌡️ {temp}°C
🌬️ {wind} m/s
☁️ {desc}

🏄 El Médano → Kite / Windsurf
🌊 Los Cristianos → Kayak
🏝️ Palm-Mar → Calm water
🏄 Las Américas → Surf
🪂 Costa Adeje → Paragliding
"""

        await app.bot.send_message(chat_id=CHANNEL_ID, text=message)

    asyncio.run(send())


# 👋 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 IslandX Bot ready!\n/weather\n/weather_en\n/activities"
    )


# 🔧 MAIN
def main():
    app = Application.builder().token(TOKEN).build()

    # HANDLERS
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("weather_en", weather_en))
    app.add_handler(CommandHandler("activities", activities))

    # ⏰ SCHEDULER
    scheduler = BackgroundScheduler()

    scheduler.add_job(send_weather_post_sync, "cron", hour=8, minute=0, args=[app])
    scheduler.add_job(send_weather_post_sync, "cron", hour=10, minute=0, args=[app])
    scheduler.add_job(send_weather_post_sync, "cron", hour=14, minute=0, args=[app])

    scheduler.start()

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
