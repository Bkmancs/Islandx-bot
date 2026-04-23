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
import random

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

# 🌍 ZONAS PRINCIPALES PARA EL RANKING
ZONAS = {
    "medano": {"lat": 28.0467, "lon": -16.5366, "nombre": "El Médano 🌬️"},
    "palm_mar": {"lat": 28.0065, "lon": -16.6805, "nombre": "Palm-Mar 🏝️"},
    "las_americas": {"lat": 28.0619, "lon": -16.7300, "nombre": "Las Américas 🏄"},
    "adeje": {"lat": 28.1210, "lon": -16.7260, "nombre": "Costa Adeje 🪂"},
    "teide": {"lat": 28.2724, "lon": -16.6425, "nombre": "Teide 🏔️"},
    "las_lajas": {"lat": 28.3500, "lon": -16.4500, "nombre": "Las Lajas 🌳"},
    "masca": {"lat": 28.3600, "lon": -16.8000, "nombre": "Masca 🏞️"},
}

# 🌳 ÁREAS RECREATIVAS (sin afectar ranking)
AREAS_RECREATIVAS = {
    "las_lajas": {"lat": 28.3500, "lon": -16.4500, "nombre": "Las Lajas 🌳"},
    "arenas_negras": {"lat": 28.2500, "lon": -16.7000, "nombre": "Arenas Negras 🏖️"},
    "masca": {"lat": 28.3600, "lon": -16.8000, "nombre": "Masca 🏞️"},
}

# 🧠 NORMALIZACIÓN DE TEXTO
ZONAS_MAPPING = {key: key for key in ZONAS.keys()}
AREAS_MAPPING = {key: key for key in AREAS_RECREATIVAS.keys()}

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
    for z in {**ZONAS, **AREAS_RECREATIVAS}:
        try:
            lat = (ZONAS.get(z) or AREAS_RECREATIVAS.get(z))["lat"]
            lon = (ZONAS.get(z) or AREAS_RECREATIVAS.get(z))["lon"]
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
        "zona": (ZONAS.get(zona_key) or AREAS_RECREATIVAS.get(zona_key))["nombre"],
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

# 🏄 RANKING Y PUNTAJE COMBINADO
def calcular_puntaje(info):
    puntaje = 0
    viento_kmh = info["viento"] * 3.6
    temp = info["temp"]
    nubes = info["nubes"]
    if 10 <= viento_kmh <= 25: puntaje += 5
    elif 5 <= viento_kmh < 10 or 25 < viento_kmh <= 30: puntaje += 3
    if 18 <= temp <= 28: puntaje += 5
    elif 15 <= temp < 18 or 28 < temp <= 30: puntaje += 3
    if nubes <= 30: puntaje += 5
    elif nubes <= 60: puntaje += 3
    return puntaje

def ranking_climas():
    # Ranking fijo 6 locaciones, siempre Palm-Mar y Teide
    ranking = [ZONAS["palm_mar"], ZONAS["teide"]]
    otras = [z for k,z in ZONAS.items() if k not in ["palm_mar","teide"]]
    ranking += random.sample(otras, min(4, len(otras)))
    ranking_info = []
    for z in ranking:
        zona_key = [k for k,v in ZONAS.items() if v==z][0]
        info = info_zona(zona_key)
        if info:
            info["puntaje"] = calcular_puntaje(info)
            info["actividad"] = actividad_recomendada(info)
            ranking_info.append(info)
    mejor = max(ranking_info, key=lambda x: x["puntaje"]) if ranking_info else None
    mensaje = "📊 Ranking condiciones:\n\n"
    for i, info in enumerate(ranking_info, 1):
        mensaje += (f"{i}. {info['zona']}\n"
                    f"   🌡️ Temp: {info['temp']}°C\n"
                    f"   🌬️ Viento: {round(info['viento']*3.6,1)} km/h\n"
                    f"   ☁️ Nubes: {info['nubes']}%\n"
                    f"   👉 Recomendado: {info['actividad']}\n\n")
    if mejor:
        mensaje += f"🔥 Mejor spot actualmente según puntaje: {mejor['zona']}!\n"
    return mensaje

# 🌳 ÁREAS RECREATIVAS
def mostrar_areas():
    mensaje = "🌳 Áreas recreativas:\n\n"
    for z in AREAS_RECREATIVAS:
        info = info_zona(z)
        if info:
            info["actividad"] = actividad_recomendada(info)
            mensaje += (f"📍 {info['zona']}\n"
                        f"🌡️ Temp: {info['temp']}°C\n"
                        f"🌬️ Viento: {round(info['viento']*3.6,1)} km/h\n"
                        f"☁️ Nubes: {info['nubes']}%\n"
    return mensaje

# 🚀 COMANDOS
async def iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "👋 ¡Bienvenido! Soy Calimabot, tu asistente del clima en Tenerife.\n\n"
        "📍 Puedes pedirme:\n"
        "- Clima en una zona: ej. 'El Médano'\n"
        "- Ranking de condiciones: escribe 'ranking'\n"
        "- Mejor spot ahora: /bestspot\n"
        "- Áreas recreativas: /areas\n\n"
        "No olvides reservar tu excursión en www.islandxperience.com\n"
        "Te deseamos una feliz estadía."
    )
    await update.message.reply_text(mensaje)

async def mejor_spot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ranking_info = [info_zona(z) for z in ZONAS if info_zona(z)]
    for info in ranking_info:
        info["puntaje"] = calcular_puntaje(info)
        info["actividad"] = actividad_recomendada(info)
    mejor = max(ranking_info, key=lambda x: x["puntaje"]) if ranking_info else None
    if mejor:
        msg = (f"🔥 Mejor spot ahora según puntaje:\n"
               f"📍 {mejor['zona']}\n"
               f"🌡️ Temp: {mejor['temp']}°C\n"
               f"🌬️ Viento: {round(mejor['viento']*3.6,1)} km/h\n"
               f"☁️ Nubes: {mejor['nubes']}%\n"
               f"👉 Recomendado: {mejor['actividad']}")
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("No hay datos disponibles.")

async def areas_recreativas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(mostrar_areas())

# 💬 MENSAJES
async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = normalizar_texto(update.message.text)
    if any(s in texto for s in SALUDOS):
        await update.message.reply_text(
            f"👋 {update.message.text.capitalize()}!\n"
            "📍 Puedes pedirme:\n"
            "- Clima en una zona: ej. 'El Médano'\n"
            "- Ranking de condiciones: escribe 'ranking'\n"
            "- Mejor spot ahora: /bestspot\n"
            "- Áreas recreativas: /areas\n"
            "Pronto tendré nuevas funciones."
        )
        return
    for key, zona_key in ZONAS_MAPPING.items():
        if key in texto:
            info = info_zona(zona_key)
            if info:
                info["actividad"] = actividad_recomendada(info)
                msg = (f"📍 {info['zona']}\n"
                       f"🌡️ Temp: {info['temp']}°C\n"
                       f"🌬️ Viento: {round(info['viento']*3.6,1)} km/h\n"
                       f"☁️ Nubes: {info['nubes']}%\n"
                       f"👉 Recomendado: {info['actividad']}")
                await update.message.reply_text(msg)
                return
    if "ranking" in texto:
        await update.message.reply_text(ranking_climas())
        return
    if "bestspot" in texto:
        await mejor_spot(update, context)
        return
    if "area" in texto or "recreativa" in texto:
        await areas_recreativas(update, context)
        return
    await update.message.reply_text(
        "🤖 No entendí tu mensaje.\n"
        "📍 Puedes pedirme:\n"
        "- Clima en una zona: ej. 'El Médano'\n"
        "- Ranking de condiciones: escribe 'ranking'\n"
        "- Mejor spot ahora: /bestspot\n"
        "- Áreas recreativas: /areas\n"
        "Pronto tendré nuevas funciones."
    )

# 🔧 SCHEDULER
def programar_posts(app):
    tz_canarias = timezone("Atlantic/Canary")
    scheduler = BackgroundScheduler(timezone=tz_canarias)
    scheduler.add_job(actualizar_cache, "interval", minutes=10)
    for h in [7, 10, 14, 17]:
        scheduler.add_job(lambda: asyncio.run_coroutine_threadsafe(enviar_post(app), app.loop),
                          "cron", hour=h, minute=0)
    scheduler.start()

async def enviar_post(app):
    mensaje = "🌴 ISLANDXPERIENCES TENERIFE\n\n"
    ranking_info = [info_zona(z) for z in ZONAS if info_zona(z)]
    for info in ranking_info:
        info["actividad"] = actividad_recomendada(info)
        mensaje += (f"📍 {info['zona']}\n"
                    f"🌡️ Temp: {info['temp']}°C\n"
                    f"🌬️ Viento: {round(info['viento']*3.6,1)} km/h\n"
                    f"☁️ Nubes: {info['nubes']}%\n"
                    f"👉 Recomendado: {info['actividad']}\n\n")
    await app.bot.send_message(chat_id=CANAL_ID, text=mensaje)

# 🔧 MAIN
def main():
    actualizar_cache()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", iniciar))
    app.add_handler(CommandHandler("bestspot", mejor_spot))
    app.add_handler(CommandHandler("areas", areas_recreativas))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    programar_posts(app)
    print("🚀 Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
