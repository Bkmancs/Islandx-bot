import os
import json
import time
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.background import BackgroundScheduler

# 🔑 ENV
TOKEN = os.environ.get("TOKEN")

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
CACHE_TIME = 600  # 10 minutos

# 🌊 FUNCIONES OPEN-METEO
def fetch_weather(zone_key):
    z = ZONES[zone_key]
    url = f"https://api.open-meteo.com/v1/forecast?latitude={z['lat']}&longitude={z['lon']}&hourly=temperature_2m,windspeed_10m,wave_height&timezone=auto"
    try:
        data = requests.get(url, timeout=5).json()
        return data
    except:
        return None

def get_cached_weather(zone_key):
    now = time.time()
    if zone_key in CACHE:
        data, ts = CACHE[zone_key]
        if now - ts < CACHE_TIME:
            return data
    data = fetch_weather(zone_key)
    CACHE[zone_key] = (data, now)
    return data

# 🌡️ INFO POR ZONA
def get_zone_info(zone_key, hour_index=0):
    data = get_cached_weather(zone_key)
    if not data:
        return None
    temp = data['hourly']['temperature_2m'][hour_index]
    wind = data['hourly']['windspeed_10m'][hour_index]
    wave = data['hourly']['wave_height'][hour_index]
    return {
        "zone": ZONES[zone_key]["name"],
        "temp": temp,
        "wind": wind,
        "wave": wave
    }

# 🏄 ACTIVIDAD
def get_activity(info, zone_key):
    wind = info["wind"]
    wave = info["wave"]
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
def get_ranking(hour_index=0):
    ranking = []
    for z in ZONES:
        info = get_zone_info(z, hour_index)
        if info:
            score = info["wind"] * 0.7 + info["wave"] * 3  # pondera viento y oleaje
            ranking.append({"zone": info["zone"], "score": score, "wind": info["wind"], "wave": info["wave"]})
    ranking.sort(key=lambda x: x["score"], reverse=True)
    msg = "📊 Ranking condiciones:\n\n"
    for i, r in enumerate(ranking, 1):
        msg += f"{i}. {r['zone']} → Viento {round(r['wind'],1)} km/h, Oleaje {round(r['wave'],1)} m\n"
    return msg

# 🧠 USUARIO
def get_user(user_id):
    return USER_DATA.get(str(user_id), {})

def update_user(user_id, key, value):
    user_id = str(user_id)
    if user_id not in USER_DATA:
        USER_DATA[user_id] = {}
    USER_DATA[user_id][key] = value
    save_users(USER_DATA)

def get_lang(update):
    user_id = update.effective_user.id
    lang = (update.effective_user.language_code or "en")[:2]
    update_user(user_id, "lang", lang)
    return lang

# 💬 MENSAJES
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user_id = update.effective_user.id
    lang = get_lang(update)

    zone_key = None
    for k in ZONES:
        if k.replace("_"," ") in text or ZONES[k]["name"].split()[0].lower() in text:
            zone_key = k
            break

    if zone_key:
        info = get_zone_info(zone_key)
        msg = f"📍 {info['zone']}\n🌡️ {info['temp']}°C\n🌬️ {info['wind']} km/h\n🌊 {info['wave']} m\n👉 {get_activity(info, zone_key)}"
        await update.message.reply_text(msg)
        update_user(user_id, "favorite_zone", zone_key)
        return

    if "ranking" in text:
        await update_message(update, get_ranking())
        return

    if "hola" in text or "hi" in text:
        greetings = {"es":"👋 Hola!", "en":"👋 Hi!"}
        await update.message.reply_text(greetings.get(lang,"👋 Hello"))
        return

    await update.message.reply_text("🤖 Prueba: clima, ranking, actividades, bestspot")

# 🚀 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update)
    msg = {"es":"🌴 IslandX listo","en":"🌴 IslandX ready"}
    await update.message.reply_text(msg.get(lang,"🌴 Ready"))

# 🔥 BEST SPOT
async def bestspot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    best = None
    best_score = -1
    for z in ZONES:
        info = get_zone_info(z)
        score = info["wind"] * 0.7 + info["wave"] * 3
        if score > best_score:
            best_score = score
            best = info
    if not best:
        await update.message.reply_text("⚠️ error")
        return
    await update.message.reply_text(f"🔥 BEST SPOT\n📍 {best['zone']}\n🌬️ {round(best['wind'],1)} km/h\n🌊 {round(best['wave'],1)} m")

# 📘 HELP
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📘 Comandos:\n- clima en <zona>\n- ranking\n- bestspot")

# 🔧 MAIN
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("bestspot", bestspot))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Bot running")
    app.run_polling()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
