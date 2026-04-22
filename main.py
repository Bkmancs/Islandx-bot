import os
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# 🔑 ENV
TOKEN = os.environ.get("TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

CHANNEL_ID = "@IslandXTenerife"


# 🌍 SPOTS EN TENERIFE SUR
SPOTS = {
    "medano": "🌬️ El Médano → Kitesurf / Windsurf",
    "palm_mar": "🏝️ Palm-Mar → Paddle / Snorkel",
    "los_cristianos": "🌊 Los Cristianos → Kayak / Surf suave",
    "las_americas": "🏄 Las Américas → Surf / Wind variable",
    "adeje": "🪂 Costa Adeje → Parapente"
}


# 🌤️ CLIMA
def get_weather():
    url = f"http://api.openweathermap.org/data/2.5/weather?lat=28.2916&lon=-16.6291&appid={WEATHER_API_KEY}&units=metric"
    return requests.get(url).json()


# 🧠 DECISIÓN INTELIGENTE DE SPOT
def get_best_spot(wind):
    if wind >= 7:
        return SPOTS["medano"]
    elif 4 <= wind < 7:
        return SPOTS["las_americas"]
    elif 2 <= wind < 4:
        return SPOTS["los_cristianos"]
    else:
        return SPOTS["palm_mar"]


# 🌍 IDIOMA AUTOMÁTICO
def get_lang(update: Update):
    lang = update.effective_user.language_code
    return lang[:2] if lang else "es"


# 🌤️ WEATHER INTELIGENTE
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_weather()

    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    desc = data["weather"][0]["description"]

    spot = get_best_spot(wind)

    lang = get_lang(update)

    messages = {
        "es": f"""
🌤️ Clima Tenerife

🌡️ {temp}°C
🌬️ {wind} m/s
☁️ {desc}

🏄 Recomendación:
{spot}
""",
        "en": f"""
🌤️ Tenerife Weather

🌡️ {temp}°C
🌬️ {wind} m/s
☁️ {desc}

🏄 Recommended spot:
{spot}
"""
    }

    await update.message.reply_text(messages.get(lang, messages["es"]))


# 👋 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 IslandX Smart Assistant\n\nUse /weather"
    )


# 📡 AUTO POST CANAL
def send_post(app):
    async def send():
        data = get_weather()

        temp = data["main"]["temp"]
        wind = data["wind"]["speed"]
        desc = data["weather"][0]["description"]

        spot = get_best_spot(wind)

        message = f"""
🌴 IslandX Tenerife Update

🌡️ {temp}°C
🌬️ {wind} m/s
☁️ {desc}

🏄 {spot}
"""

        await app.bot.send_message(chat_id=CHANNEL_ID, text=message)

    asyncio.run(send())


# 🔧 MAIN
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("weather", weather))

    scheduler = BackgroundScheduler()
    scheduler.add_job(send_post, "cron", hour=8, minute=0, args=[app])
    scheduler.add_job(send_post, "cron", hour=10, minute=0, args=[app])
    scheduler.add_job(send_post, "cron", hour=14, minute=0, args=[app])
    scheduler.start()

    print("Smart bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
