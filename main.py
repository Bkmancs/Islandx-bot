import os
import json
import time
import threading
import requests
import unicodedata
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio

# 🔑 ENV
TOKEN = os.environ.get("TOKEN")
WEATHER_API_KEY = "5102dbcdeb96dddb822639d35fa993c4"
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

# 🧠 NORMALIZACIÓN DE ZONAS
ZONE_MAPPING = {
    "medano": "medano",
    "el medano": "medano",
    "palm mar": "palm_mar",
    "palm-mar": "palm_mar",
    "los cristianos": "los_cristianos",
    "las americas": "las_americas",
    "las américas": "las_americas",
    "americas": "las_americas",
    "adeje": "adeje",
    "teide": "teide"
}

def normalize_text(text):
    text = text.lower().strip()
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')
    text = text.replace("-", " ").replace("_", " ")
    return text

# 🌤️ CACHE
WEATHER_CACHE = {}
CACHE_TIME = 600  # 10 minutos
LAST_UPDATE = 0

def update_cache():
    global WEATHER_CACHE, LAST_UPDATE
    new_cache = {}
    for z in ZONES:
        try:
            lat = ZONES[z]["lat"]
            lon = ZONES[z]["lon"]
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
            data = requests.get(url, timeout=5).json()
            new_cache[z] = data
        except Exception as e:
            print(f"Error fetching {z}: {e}")
    WEATHER_CACHE = new_cache
    LAST_UPDATE = time.time()
    print("🟢 Cache updated")

def get_zone_info(zone_key):
    data = WEATHER_CACHE.get(zone_key)
    if not data:
        return None
    temp = data["main"]["temp"]
    wind = data["wind"]["speed"]
    desc = data["weather"][0]["description"]
    return {
        "zone_key": zone_key,
        "zone": ZONES[zone_key]["name"],
        "temp": temp,
        "wind": wind,
        "desc": desc
    }

# 🏄 ACTIVIDAD
def get_activity(info):
    wind = info["wind"] * 3.6  # convertir m/s a km/h
    zone_key = info["zone_key"]
    if zone_key == "teide":
        return "🥾 Senderismo / 🌌 Astrofotografía"
    if wind >= 25:
        return "🌬️ Kitesurf"
    elif 15 <= wind < 25:
        return "🏄 Surf"
    elif 8 <= wind < 15:
        return "🌊 Paddle / Kayak"
    else:
        return "🏝️ Mar tranquilo"

# 📊 RANKING
def get_ranking():
    ranking = []
    for z in ZONES:
        info = get_zone_info(z)
        if info:
            score = info["wind"] * 0.7  # solo viento por ahora
            ranking.append({"zone": info["zone"], "score": score, "wind": info["wind"]})
    ranking.sort(key=lambda x: x["score"], reverse=True)
    msg = "📊 Ranking condiciones:\n\n"
    for i, r in enumerate(ranking, 1):
        msg += f"{i}. {r['zone']} → Viento {round(r['wind']*3.6,1)} km/h\n"
    return msg

# 📝 ACTIVIDADES
def get_activities():
    msg = "🏄 Actividades por zona:\n\n"
    for z in ZONES:
        info = get_zone_info(z)
        if info:
            activity = get_activity(info)
            msg += f"📍 {info['zone']} → {activity}\n"
    return msg

# 🚀 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "👋 ¡Bienvenido! Soy Calimabot, tu asistente del clima en Tenerife.\n\n"
        "📍 Puedes pedirme:\n"
        "- Clima en una zona: ej. 'El Médano'\n"
        "- Ranking de condiciones: escribe 'ranking'\n"
        "- Actividades recomendadas: escribe 'actividades'\n"
        "- Mejor spot ahora: usa /bestspot\n"
    )
    await update.message.reply_text(welcome_msg)

# 🔥 BEST SPOT
async def bestspot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    best = None
    best_score = -1
    for z in ZONES:
        info = get_zone_info(z)
        if not info:
            continue
        score = info["wind"]
        if score > best_score:
            best_score = score
            best = info
    if best:
        msg = f"🔥 Mejor spot ahora:\n📍 {best['zone']}\n🌡️ {best['temp']}°C\n🌬️ {round(best['wind']*3.6,1)} km/h\n☁️ {best['desc']}\n👉 {get_activity(best)}"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("No hay datos disponibles")

# 💬 MENSAJES
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = normalize_text(update.message.text)

    if text in ZONE_MAPPING:
        zone_key = ZONE_MAPPING[text]
        info = get_zone_info(zone_key)
        if info:
            msg = f"📍 {info['zone']}\n🌡️ {info['temp']}°C\n🌬️ {round(info['wind']*3.6,1)} km/h\n☁️ {info['desc']}\n👉 {get_activity(info)}"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("❌ No hay datos disponibles para esta zona.")
    elif "ranking" in text:
        await update.message.reply_text(get_ranking())
    elif "actividad" in text or "actividades" in text:
        await update.message.reply_text(get_activities())
    else:
        await update.message.reply_text("🤖 No entendí tu mensaje. Prueba: clima en <zona>, ranking, actividades, bestspot")

# 📡 AUTO-POST
async def send_post(app):
    message = "🌴 IslandX Update\n\n"
    for z in ZONES:
        info = get_zone_info(z)
        if info:
            message += f"📍 {info['zone']}\n🌡️ {info['temp']}°C\n🌬️ {round(info['wind']*3.6,1)} km/h\n☁️ {info['desc']}\n👉 {get_activity(info)}\n\n"
    await app.bot.send_message(chat_id=CHANNEL_ID, text=message)

# 🔧 MAIN
def main():
    update_cache()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bestspot", bestspot))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler = BackgroundScheduler()
    scheduler.add_job(update_cache, "interval", minutes=10)
    for h in [7,10,14,17]:
        scheduler.add_job(lambda: asyncio.create_task(send_post(app)), "cron", hour=h, minute=0)
    scheduler.start()

    print("🚀 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
