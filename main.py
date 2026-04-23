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
from pytz import timezone

# 🔑 CONFIGURACIÓN
TOKEN = os.environ.get("TOKEN")
WEATHER_API_KEY = "5102dbcdeb96dddb822639d35fa993c4"
CANAL_ID = "@IslandXTenerife"

# 🌐 KEEP ALIVE
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot activo"

def run_web():
    app_web.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web).start()

# 💾 MEMORIA JSON
USUARIOS_FILE = "usuarios.json"

def cargar_usuarios():
    try:
        with open(USUARIOS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def guardar_usuarios(datos):
    with open(USUARIOS_FILE, "w") as f:
        json.dump(datos, f)

USUARIOS = cargar_usuarios()

# 🌍 ZONAS
ZONAS = {
    "medano": {"lat": 28.0467, "lon": -16.5366, "nombre": "El Médano 🌬️"},
    "palm_mar": {"lat": 28.0065, "lon": -16.6805, "nombre": "Palm-Mar 🏝️"},
    "los_cristianos": {"lat": 28.0525, "lon": -16.7160, "nombre": "Los Cristianos 🌊"},
    "las_americas": {"lat": 28.0619, "lon": -16.7300, "nombre": "Las Américas 🏄"},
    "adeje": {"lat": 28.1210, "lon": -16.7260, "nombre": "Costa Adeje 🪂"},
    "teide": {"lat": 28.2724, "lon": -16.6425, "nombre": "Teide 🏔️"}
}

# 🧠 NORMALIZACIÓN DE TEXTO
ZONAS_MAPPING = {
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

SALUDOS = ["hola", "buenos días", "buenos dias", "buenas tardes", "buenas noches"]

def normalizar_texto(texto):
    texto = texto.lower().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = texto.replace("-", " ").replace("_", " ")
    return texto

# 🌤️ CACHE
CACHE_CLIMA = {}
ULTIMA_ACTUALIZACION = 0

def actualizar_cache():
    global CACHE_CLIMA, ULTIMA_ACTUALIZACION
    nueva_cache = {}
    for z in ZONAS:
        try:
            lat = ZONAS[z]["lat"]
            lon = ZONAS[z]["lon"]
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=es"
            datos = requests.get(url, timeout=5).json()
            nueva_cache[z] = datos
        except Exception as e:
            print(f"Error obteniendo {z}: {e}")
    CACHE_CLIMA = nueva_cache
    ULTIMA_ACTUALIZACION = time.time()
    print("🟢 Cache actualizada")

def info_zona(zona_key):
    datos = CACHE_CLIMA.get(zona_key)
    if not datos:
        return None
    temp = datos["main"]["temp"]
    viento = datos["wind"]["speed"]
    nubes = datos["clouds"]["all"]
    desc = datos["weather"][0]["description"]
    return {
        "zona_key": zona_key,
        "zona": ZONAS[zona_key]["nombre"],
        "temp": temp,
        "viento": viento,
        "nubes": nubes,
        "desc": desc
    }

# 🏄 RECOMENDACIÓN DE DEPORTE
def actividad_recomendada(info):
    viento_kmh = info["viento"] * 3.6
    z = info["zona_key"]
    if z == "teide":
        return "🥾 Senderismo / 🌌 Astrofotografía"
    if viento_kmh >= 25:
        return "🌬️ Kitesurf"
    elif 15 <= viento_kmh < 25:
        return "🏄 Surf"
    elif 8 <= viento_kmh < 15:
        return "🌊 Paddle / Kayak"
    else:
        return "🏝️ Mar tranquilo"

# 📊 RANKING
def ranking_climas():
    ranking = []
    for z in ZONAS:
        if z == "los_cristianos":
            continue  # no aparece en ranking
        info = info_zona(z)
        if info:
            ranking.append(info)
    ranking.sort(key=lambda x: x["viento"], reverse=True)
    mejor = ranking[0] if ranking else None
    mensaje = "📊 Ranking condiciones:\n\n"
    for i, info in enumerate(ranking, 1):
        mensaje += (f"{i}. {info['zona']}\n"
                    f"   🌡️ Temp: {info['temp']}°C\n"
                    f"   🌬️ Viento: {round(info['viento']*3.6,1)} km/h\n"
                    f"   ☁️ Nubes: {info['nubes']}%\n"
                    f"   👉 Recomendado: {actividad_recomendada(info)}\n\n")
    if mejor:
        mensaje += f"🔥 Mejor spot actualmente: {mejor['zona']}!\n"
    return mensaje

# 🚀 COMANDOS
async def iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "👋 ¡Bienvenido! Soy Calimabot, tu asistente del clima en Tenerife.\n\n"
        "📍 Puedes pedirme:\n"
        "- Clima en una zona: ej. 'El Médano'\n"
        "- Ranking de condiciones: escribe 'ranking'\n"
        "- Mejor spot ahora: /bestspot\n\n"
        "No olvides reservar tu excursión en www.islandxperience.com\n"
        "Te deseamos una feliz estadía."
    )
    await update.message.reply_text(mensaje)

async def mejor_spot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mejor = None
    max_viento = -1
    for z in ZONAS:
        info = info_zona(z)
        if info and info["viento"] > max_viento:
            max_viento = info["viento"]
            mejor = info
    if mejor:
        msg = (f"🔥 Mejor spot ahora:\n"
               f"📍 {mejor['zona']}\n"
               f"🌡️ Temp: {mejor['temp']}°C\n"
               f"🌬️ Viento: {round(mejor['viento']*3.6,1)} km/h\n"
               f"☁️ Nubes: {mejor['nubes']}%\n"
               f"👉 {actividad_recomendada(mejor)}")
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("No hay datos disponibles.")

# 💬 MENSAJES
async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = normalizar_texto(update.message.text)

    # Detectar saludo
    if any(s in texto for s in SALUDOS):
        await update.message.reply_text(
            f"👋 {update.message.text.capitalize()}!\n"
            "📍 Puedes pedirme:\n"
            "- Clima en una zona: ej. 'El Médano'\n"
            "- Ranking de condiciones: escribe 'ranking'\n"
            "- Mejor spot ahora: /bestspot\n"
            "Pronto tendré nuevas funciones."
        )
        return

    # Detectar palabra clave de zona
    for key, zona_key in ZONAS_MAPPING.items():
        if key in texto:
            info = info_zona(zona_key)
            if info:
                msg = (f"📍 {info['zona']}\n"
                       f"🌡️ Temp: {info['temp']}°C\n"
                       f"🌬️ Viento: {round(info['viento']*3.6,1)} km/h\n"
                       f"☁️ Nubes: {info['nubes']}%\n"
                       f"👉 {actividad_recomendada(info)}")
                await update.message.reply_text(msg)
                return

    # Detectar ranking
    if "ranking" in texto:
        await update.message.reply_text(ranking_climas())
        return

    # Detectar bestspot como palabra
    if "bestspot" in texto:
        await mejor_spot(update, context)
        return

    # Mensaje de error genérico
    await update.message.reply_text(
        "🤖 No entendí tu mensaje.\n"
        "📍 Puedes pedirme:\n"
        "- Clima en una zona: ej. 'El Médano'\n"
        "- Ranking de condiciones: escribe 'ranking'\n"
        "- Mejor spot ahora: /bestspot\n"
        "Pronto tendré nuevas funciones."
    )

# 📡 AUTO-POST AL CANAL
async def enviar_post(app):
    mensaje = "🌴 ISLANDXPERIENCES TENERIFE\n\n"
    for z in ZONAS:
        info = info_zona(z)
        if info:
            mensaje += (f"📍 {info['zona']}\n"
                        f"🌡️ Temp: {info['temp']}°C\n"
                        f"🌬️ Viento: {round(info['viento']*3.6,1)} km/h\n"
                        f"☁️ Nubes: {info['nubes']}%\n"
                        f"👉 {actividad_recomendada(info)}\n\n")
    await app.bot.send_message(chat_id=CANAL_ID, text=mensaje)

# 🔧 SCHEDULER
def programar_posts(app):
    tz_canarias = timezone("Atlantic/Canary")
    scheduler = BackgroundScheduler(timezone=tz_canarias)
    scheduler.add_job(actualizar_cache, "interval", minutes=10)
    for h in [7, 10, 14, 17]:
        scheduler.add_job(lambda: asyncio.run_coroutine_threadsafe(enviar_post(app), app.loop),
                          "cron", hour=h, minute=0)
    scheduler.start()

# 🔧 MAIN
def main():
    actualizar_cache()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", iniciar))
    app.add_handler(CommandHandler("bestspot", mejor_spot))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    programar_posts(app)
    print("🚀 Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
