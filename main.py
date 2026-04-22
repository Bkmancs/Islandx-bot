import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 🔑 VARIABLES DE ENTORNO (RENDER)
TOKEN = os.environ.get("TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

# 📡 CANAL
CHANNEL_ID = "@IslandXTenerife"


# 🌍 CLIMA
def get_weather_by_coords(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    return requests.get(url).json()


# 🌤️ WEATHER
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_weather_by_coords(28.2916, -16.6291)

    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    desc = data["weather"][0]["description"]

    message = f"""
🌤️ Tenerife Weather

🌡️ Temp: {temp}°C
🌬️ Wind: {wind} m/s
☁️ {desc}
"""

    await update.message.reply_text(message)


# 🏄 ACTIVITIES
async def activities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
🏄 Tenerife Activities

🌬️ El Médano → Kite/Wind
🌊 Los Cristianos → Kayak
🏝️ Palm-Mar → Snorkel/Paddle
🪂 Costa Adeje → Paragliding
🏄 Las Américas → Surf
"""
    await update.message.reply_text(message)


# 📡 AUTO POST CANAL
async def send_weather_post(app):
    data = get_weather_by_coords(28.2916, -16.6291)

    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    desc = data["weather"][0]["description"]

    message = f"""
🌴 IslandX Tenerife Update

🌡️ {temp}°C
🌬️ {wind} m/s
☁️ {desc}

🏄 El Médano → Kite/Wind
🌊 Los Cristianos → Kayak
🏝️ Palm-Mar → Calm water
🪂 Costa Adeje → Paragliding
"""

    await app.bot.send_message(chat_id=CHANNEL_ID, text=message)


# 👋 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 IslandX Bot ready!\n/weather\n/activities")


# 🔧 MAIN
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("activities", activities))

    # ⏰ SCHEDULER
    scheduler = AsyncIOScheduler()

    scheduler.add_job(send_weather_post, "cron", hour=8, minute=0, args=[app])
    scheduler.add_job(send_weather_post, "cron", hour=10, minute=0, args=[app])
    scheduler.add_job(send_weather_post, "cron", hour=14, minute=0, args=[app])

    scheduler.start()

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
