import os
import json
import asyncio
import subprocess
import threading
import time
import traceback
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# --- CONFIGURACIÓN ---
load_dotenv()

TOKEN           = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_DEFAULT = os.getenv("CHAT_ID_DEFAULT", "")

CHECK_INTERVAL = 5   # Segundos entre comprobaciones
MARGEN_SALIDA  = 10  # Fallos seguidos para confirmar que salió

REMINDERS_FILE = Path(__file__).parent / "reminders.json"

# Lista global de dispositivos (se llena en main())
DISPOSITIVOS: list[dict] = []


# ------------------------------------------------------------
# ALMACENAMIENTO DE RECORDATORIOS
#
# Formato en reminders.json:
# [
#   {"tarea": "Tirar la basura", "pendiente_para": ["Nico", "Mama"]},
#   ...
# ]
#
# Cuando un dispositivo llega a casa, se le mandan los recordatorios
# donde su nombre está en "pendiente_para". Luego se lo tilda.
# Si pendiente_para queda vacío, el recordatorio se borra solo.
# ------------------------------------------------------------
def cargar_recordatorios() -> list[dict]:
    if REMINDERS_FILE.exists():
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def guardar_recordatorios(lista: list[dict]):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------
# PARSEAR DISPOSITIVOS
# Formato: DEVICES=Nombre:IP:ChatId(opcional)
# ------------------------------------------------------------
def parsear_dispositivos():
    raw = os.getenv("DEVICES", "")
    if not raw:
        raise ValueError("❌ No se encontró la variable DEVICES en el .env")

    dispositivos = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        partes = entry.split(":")
        if len(partes) < 2:
            print(f"⚠️  Entrada inválida ignorada: '{entry}'")
            continue

        nombre  = partes[0].strip()
        ip      = partes[1].strip()
        chat_id = partes[2].strip() if len(partes) > 2 else CHAT_ID_DEFAULT

        if not chat_id:
            print(f"⚠️  '{nombre}' sin chat_id y CHAT_ID_DEFAULT no definido. Ignorado.")
            continue

        dispositivos.append({"nombre": nombre, "ip": ip, "chat_id": chat_id})

    return dispositivos


# ------------------------------------------------------------
# DETECCIÓN DE RED
# ------------------------------------------------------------
def esta_en_red(ip):
    cmd = ["sudo", "arping", "-c", "1", "-W", "1", ip]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0


def vigilar_dispositivo(dispositivo, loop, app):
    nombre  = dispositivo["nombre"]
    ip      = dispositivo["ip"]
    chat_id = dispositivo["chat_id"]

    esta_en_casa      = False
    contador_ausencia = 0

    print(f"[{nombre}] 👀 Vigilando {ip}...")

    while True:
        presente_ahora = esta_en_red(ip)
        ts = time.strftime('%H:%M:%S')

        if presente_ahora:
            contador_ausencia = 0
            if not esta_en_casa:
                print(f"[{ts}] [{nombre}] ✅ Llegada detectada.")
                esta_en_casa = True
                asyncio.run_coroutine_threadsafe(
                    on_llegada(app, chat_id, nombre),
                    loop
                )
        else:
            if esta_en_casa:
                contador_ausencia += 1
                if contador_ausencia >= MARGEN_SALIDA:
                    print(f"[{ts}] [{nombre}] 🚶 Fuera de rango. Reset de estado.")
                    esta_en_casa      = False
                    contador_ausencia = 0

        time.sleep(CHECK_INTERVAL)


# ------------------------------------------------------------
# ON LLEGADA — manda los recordatorios pendientes para ese usuario
# ------------------------------------------------------------
async def on_llegada(app, chat_id, nombre):
    lista = cargar_recordatorios()

    # Filtrar solo los que le faltan a este usuario
    pendientes = [r for r in lista if nombre in r.get("pendiente_para", [])]

    saludo = f"🏠 *¡{nombre} llegó a casa!*"

    if not pendientes:
        await app.bot.send_message(chat_id=chat_id, text=saludo, parse_mode="Markdown")
        return

    # Tildar a este usuario en cada recordatorio pendiente
    for r in lista:
        if nombre in r.get("pendiente_para", []):
            r["pendiente_para"].remove(nombre)

    # Borrar los que ya recibieron todos los usuarios
    lista = [r for r in lista if r["pendiente_para"]]
    guardar_recordatorios(lista)

    lista_texto = "\n".join(f"  {i+1}. {r['tarea']}" for i, r in enumerate(pendientes))
    await app.bot.send_message(
        chat_id=chat_id,
        text=f"{saludo}\n\n📋 *Recordatorios:*\n{lista_texto}",
        parse_mode="Markdown",
    )


# ------------------------------------------------------------
# COMANDOS DEL BOT
# ------------------------------------------------------------
async def cmd_agregar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/agregar <tarea>  →  agrega un recordatorio para todos los dispositivos"""
    tarea = " ".join(ctx.args).strip() if ctx.args else ""
    if not tarea:
        await update.message.reply_text("Uso: /agregar <tarea>\nEjemplo: /agregar Tirar la basura")
        return

    todos = [d["nombre"] for d in DISPOSITIVOS]
    lista = cargar_recordatorios()
    lista.append({"tarea": tarea, "pendiente_para": todos})
    guardar_recordatorios(lista)

    destinatarios = ", ".join(todos)
    await update.message.reply_text(
        f"✅ Agregado: {tarea}\nSe mandará cuando lleguen: {destinatarios}"
    )


async def cmd_ver(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/ver  →  muestra los recordatorios y a quién le faltan"""
    lista = cargar_recordatorios()
    if not lista:
        await update.message.reply_text("📭 No hay recordatorios pendientes.")
        return
    lineas = []
    for i, r in enumerate(lista):
        falta = ", ".join(r["pendiente_para"]) or "—"
        lineas.append(f"{i+1}. {r['tarea']}  [falta: {falta}]")
    await update.message.reply_text(
        "📋 Recordatorios:\n" + "\n".join(lineas)
    )


async def cmd_borrar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/borrar <número>  →  borra el recordatorio manualmente"""
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("Uso: /borrar <número>\nUsá /ver para ver los números.")
        return

    idx = int(ctx.args[0]) - 1
    lista = cargar_recordatorios()

    if idx < 0 or idx >= len(lista):
        await update.message.reply_text("❌ Número fuera de rango.")
        return

    eliminado = lista.pop(idx)["tarea"]
    guardar_recordatorios(lista)
    await update.message.reply_text(f"🗑️ Eliminado: {eliminado}")


async def cmd_limpiar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/limpiar  →  borra todos los recordatorios"""
    guardar_recordatorios([])
    await update.message.reply_text("🧹 Todos los recordatorios eliminados.")


async def cmd_ayuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Comandos disponibles:\n\n"
        "/agregar <tarea> — agrega un recordatorio para todos\n"
        "/ver — lista los recordatorios y a quién le faltan\n"
        "/borrar <número> — elimina un recordatorio manualmente\n"
        "/limpiar — borra todo\n\n"
        "Los recordatorios se mandan solos cuando alguien llega a casa "
        "y se borran una vez que todos lo recibieron."
    )


async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    print("[ERROR] Excepción en el bot:")
    traceback.print_exception(type(ctx.error), ctx.error, ctx.error.__traceback__)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    global DISPOSITIVOS
    DISPOSITIVOS = parsear_dispositivos()

    if not DISPOSITIVOS:
        print("❌ No hay dispositivos válidos. Revisá el .env.")
        return

    print(f"🚀 Sistema iniciado. Vigilando {len(DISPOSITIVOS)} dispositivo(s):")
    for d in DISPOSITIVOS:
        print(f"   • {d['nombre']} → {d['ip']} (chat: {d['chat_id']})")
    print()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("agregar", cmd_agregar))
    app.add_handler(CommandHandler("ver",     cmd_ver))
    app.add_handler(CommandHandler("borrar",  cmd_borrar))
    app.add_handler(CommandHandler("limpiar", cmd_limpiar))
    app.add_handler(CommandHandler("ayuda",   cmd_ayuda))
    app.add_handler(CommandHandler("help",    cmd_ayuda))
    app.add_error_handler(error_handler)

    async def post_init(application: Application):
        loop = asyncio.get_event_loop()
        for d in DISPOSITIVOS:
            t = threading.Thread(
                target=vigilar_dispositivo,
                args=(d, loop, application),
                daemon=True,
                name=d["nombre"],
            )
            t.start()

    app.post_init = post_init

    try:
        app.run_polling()
    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido.")


if __name__ == "__main__":
    main()