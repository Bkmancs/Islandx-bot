import os
import json
import time
import threading
import requests
import unicodedata
import random
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

# 🌍 ZONAS DE INTERÉS PARA RANKING
ZONAS = {
    "medano": {"lat": 28.0467, "lon": -16.5366, "nombre": "El Médano 🌬️"},
    "palm_mar": {"lat": 28.0065, "lon": -16.6805, "nombre": "Palm-Mar 🏝️"},
    "los_cristianos": {"lat": 28.0525, "lon": -16.7160, "nombre": "Los Cristianos 🌊"},
    "las_americas": {"lat": 28.0619, "lon": -16.7300, "nombre": "Las Américas 🏄"},
    "adeje": {"lat": 28.1210, "lon": -16.7260, "nombre": "Costa Adeje 🪂"},
    "teide": {"lat": 28.2724, "lon": -16.6425, "nombre": "Teide 🏔️"},
    "puerto_colon": {"lat": 28.061, "lon": -16.737, "nombre": "Puerto Colón ⚓"},
    "callao_salvaje": {"lat": 28.064, "lon": -16.753, "nombre": "Callao Salvaje 🏖️"},
    "los_gigantes": {"lat": 28.247, "lon": -16.854, "nombre": "Los Gigantes 🏞️"},
    "teresitas": {"lat": 28.511, "lon": -16.226, "nombre": "Playa de Las Teresitas 🏖️"},
    "bajamar": {"lat": 28.549, "lon": -16.286, "nombre": "Bajamar 🌊"},
    "taganana": {"lat": 28.667, "lon": -16.331, "nombre": "Taganana 🏝️"},
    "tabaiba": {"lat": 28.471, "lon": -16.248, "nombre": "Tabaiba 🌴"}
}

# ZONAS RECREATIVAS (solo clima)
AREAS_RECREATIVAS = {
    "las_lajas": {"lat": 28.057, "lon": -16.638, "nombre": "Las Lajas 🌳"},
    "arenas_negras": {"lat": 28.05, "lon": -16.63, "nombre": "Arenas Negras 🌲"},
    "masca": {"lat": 28.352, "lon": -16.841, "nombre": "Masca 🌄"},
    "anaga": {"lat": 28.526, "lon": -16.208, "nombre": "Bosque de Anaga 🌿"}
}

# Normalización de texto
ZONAS_MAPPING = {k: k for k in ZONAS.keys()}
ZONAS_MAPPING.update({
    "el medano": "medano",
    "palm mar": "palm_mar",
    "palm-mar": "palm_mar",
    "los cristianos": "los_cristianos",
    "las americas": "las_americas",
    "las américas": "las_americas",
    "americas": "las_americas",
    "puerto colon": "puerto_colon",
    "callao salvaje": "callao_salvaje",
    "los gigantes": "los_gigantes",
    "playa teresitas": "teresitas",
    "bajamar": "bajamar",
    "taganana": "taganana",
    "tabaiba": "tabaiba"
})

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
            time.sleep(0.1)  # evita exceder rate limit
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

# 🏄 Recomendación de deporte
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

def calcular_puntaje(info):
    puntaje = 0
    viento_kmh = info["viento"] * 3.6
    temp = info["temp"]
    nubes = info["nubes"]
    # viento ideal: 10-25 km/h
    if 10 <= viento_kmh <= 25:
        puntaje += 5
    elif 5 <= viento_kmh < 10 or 25 < viento_kmh <= 30:
        puntaje += 3
    # temperatura agradable: 18-28°C
    if 18 <= temp <= 28:
        puntaje += 5
    elif 15 <= temp < 18 or 28 < temp <= 30:
        puntaje += 3
    # menos nubes mejor
    if nubes <= 30:
        puntaje += 5
    elif nubes <= 60:
        puntaje += 3
    return puntaje

# 🏆 RANKING CLIMAS
def ranking_climas():
    ranking = []
    # Siempre incluir Palm-Mar
    info = info_zona("palm_mar")
    if info:
        info["puntaje"] = calcular_puntaje(info)
        info["deporte"] = actividad_recomendada(info)
        ranking.append(info)

    # Selección de 5 zonas restantes (solo costeras/relevantes)
    otras = [k for k in ZONAS if k != "palm_mar"]
    ranking_otros = []
    for z in otras:
        info = info_zona(z)
        if info:
            info["puntaje"] = calcular_puntaje(info)
            info["deporte"] = actividad_recomendada(info)
            ranking_otros.append(info)

    # Orden por viento y aleatorización para valores iguales
    ranking_otros.sort(key=lambda x: x["viento"], reverse=True)
    final = []
    i = 0
    while i < len(ranking_otros) and len(final) < 5:
        same_wind = [ranking_otros[i]]
        j = i + 1
        while j < len(ranking_otros) and ranking_otros[j]["viento"] == ranking_otros[i]["viento"]:
            same_wind.append(ranking_otros[j])
            j += 1
        random.shuffle(same_wind)
        final.append(same_wind[0])  # solo uno de los valores iguales
        i = j

    ranking.extend(final[:5])

    mensaje = "📊 Ranking condiciones:\n\n"
    for idx, info in enumerate(ranking, 1):
        mensaje += (f"{idx}. {info['zona']}\n"
                    f"   🌡️ Temp: {info['temp']}°C\n"
                    f"   🌬️ Viento: {round(info['viento']*3.6,1)} km/h\n"
                    f"   ☁️ Nubes: {info['nubes']}%\n"
                    f"   👉 Recomendado: {info['deporte']}\n\n")
    mejor = max(ranking, key=lambda x: x["puntaje"]) if ranking else None
    if mejor:
        mensaje += f"🔥 Mejor spot actualmente: {mejor['zona']}!\n"
    return mensaje

# 🌿 ÁREAS RECREATIVAS
async def areas_recreativas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = "🌿 Áreas recreativas de Tenerife:\n\n"
    for key, val in AREAS_RECREATIVAS.items():
        info = info_zona(key)
        if info:
            mensaje += (f"📍 {val['nombre']}\n"
                        f"🌡️ Temp: {info['temp']}°C\n"
                        f"🌬️ Viento: {round(info['viento']*3.6,1)} km/h\n"
                        f"☁️ Nubes: {info['nubes']}%\n\n")
        else:
            mensaje += f"📍 {val['nombre']}\n   No hay datos de clima.\n\n"
    await update.message.reply_text(mensaje)

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
    mejor = None
    max_puntaje = -1
    for z in ZONAS:
        info = info_zona(z)
        if info:
            puntaje = calcular_puntaje(info)
            if puntaje > max_puntaje:
                max_puntaje = puntaje
                info["deporte"] = actividad_recomendada(info)
                mejor = info
    if mejor:
        msg = (f"🔥 Mejor spot ahora:\n"
               f"📍 {mejor['zona']}\n"
               f"🌡️ Temp: {mejor['temp']}°C\n"
               f"🌬️ Viento: {round(mejor['viento']*3.6,1)} km/h\n"
               f"☁️ Nubes: {mejor['nubes']}%\n"
               f"👉 Recomendado: {mejor['deporte']}")
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("No hay datos disponibles.")

# 💬 MENSAJES
async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = normalizar_texto(update.message.text)

    # Saludos
    if any(s in texto for s in SALUDOS):
        await update.message.reply_text(
            f"👋 {update.message.text.capitalize()}!\n"
            "📍 Puedes pedirme:\n"
            "- Clima en una zona: ej. 'El Médano'\n"
            "- Ranking de condiciones: escribe 'ranking'\n"
            "- Mejor spot ahora: /bestspot\n"
            "- Áreas recreativas: /areas"
        )
        return

    # Zonas
    for key, zona_key in ZONAS_MAPPING.items():
        if key in texto:
            info = info_zona(zona_key)
            if info:
                msg = (f"📍 {info['zona']}\n"
                       f"🌡️ Temp: {info['temp']}°C\n"
                       f"🌬️ Viento: {round(info['viento']*3.6,1)} km/h\n"
                       f"☁️ Nubes: {info['nubes']}%")
                await update.message.reply_text(msg)
                return

    # Ranking
    if "ranking" in texto:
        await update.message.reply_text(ranking_climas())
        return

    # Bestspot
    if "bestspot" in texto:
        await mejor_spot(update, context)
        return

    # Áreas recreativas
    if "areas" in texto or "áreas" in texto:
        await areas_recreativas(update, context)
        return

    await update.message.reply_text(
        "🤖 No entendí tu mensaje.\n"
        "📍 Puedes pedirme:\n"
        "- Clima en una zona: ej. 'El Médano'\n"
        "- Ranking de condiciones: escribe 'ranking'\n"
        "- Mejor spot ahora: /bestspot\n"
        "- Áreas recreativas: /areas"
    )

# 🔧 SCHEDULER
def programar_posts(app):
    tz_canarias = timezone("Atlantic/Canary")
    scheduler = BackgroundScheduler(timezone=tz_canarias)
    
    # Actualizar cache cada 10 minutos
    scheduler.add_job(actualizar_cache, "interval", minutes=10)

    # Horas de envío al canal
    horas_envio = [7, 10, 14, 17, 20, 21]
    for h in horas_envio:
        # Usamos run_coroutine_threadsafe para correr la función asíncrona desde el scheduler
        scheduler.add_job(lambda h=h: asyncio.run_coroutine_threadsafe(enviar_post(app), app.loop),
                          "cron", hour=h, minute=0)
    
    scheduler.start()

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
