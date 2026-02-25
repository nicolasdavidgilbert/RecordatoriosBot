# 🏠 RecordatoriosBot

Bot de Telegram que detecta cuando alguien llega a casa (vía `arping` en la red local) y le envía sus recordatorios pendientes automáticamente.

---

## ¿Cómo funciona?

1. El bot monitorea las IPs de los dispositivos configurados en la red local usando `arping`
2. Cuando detecta que un dispositivo se conecta, le manda por Telegram todos sus recordatorios pendientes
3. Una vez que **todos** los dispositivos recibieron un recordatorio, este se borra automáticamente
4. Los recordatorios se gestionan con comandos de Telegram

---

## Requisitos

- Python 3.12+
- `arping` instalado (`sudo apt install arping`)
- El script necesita correr con permisos para usar `sudo arping` (o configurar sudoers sin contraseña para ese comando)
- Un bot de Telegram creado con [@BotFather](https://t.me/BotFather)

---

## Instalación

```bash
# Clonar o descargar el proyecto
cd RecordatoriosBot

# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install python-dotenv requests "python-telegram-bot[job-queue]"
```

---

## Configuración

Copiá `.env.example` como `.env` y completá los valores:

```bash
cp .env.example .env
```

### Variables del `.env`

| Variable | Descripción |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token del bot (obtenelo con @BotFather) |
| `CHAT_ID_DEFAULT` | Chat ID por defecto si no se especifica uno por dispositivo |
| `DEVICES` | Lista de dispositivos a vigilar (ver formato abajo) |

### Formato de `DEVICES`

```
DEVICES=Nombre:IP:ChatId(opcional)
```

- **Nombre** — identificador del dispositivo (aparece en logs y mensajes)
- **IP** — IP local del dispositivo en la red
- **ChatId** — chat de Telegram donde avisar; si se omite usa `CHAT_ID_DEFAULT`

**Ejemplos:**

```env
# Un solo dispositivo
DEVICES=Nico:192.168.1.100:1234567890

# Múltiples dispositivos, cada uno con su chat
DEVICES=Nico:192.168.1.100:1234567890,Mama:192.168.1.101:9876543210,Papa:192.168.1.102

# Todos al mismo chat (usando CHAT_ID_DEFAULT)
CHAT_ID_DEFAULT=1234567890
DEVICES=Nico:192.168.1.100,Mama:192.168.1.101
```

> Para obtener tu Chat ID, hablale a [@userinfobot](https://t.me/userinfobot) en Telegram.

---

## Uso

```bash
source .venv/bin/activate
python main.py
```

El bot arranca, empieza a vigilar los dispositivos y queda escuchando comandos de Telegram.

---

## Comandos disponibles

| Comando | Descripción |
|---|---|
| `/agregar <tarea>` | Agrega un recordatorio para todos los dispositivos |
| `/ver` | Muestra los recordatorios pendientes y a quién le faltan |
| `/borrar <número>` | Elimina un recordatorio manualmente |
| `/limpiar` | Borra todos los recordatorios |
| `/help` o `/ayuda` | Muestra la lista de comandos |

### Ejemplo de flujo

```
Vos: /agregar Tirar la basura
Bot: ✅ Agregado: Tirar la basura
     Se mandará cuando lleguen: Nico, Mama

--- Nico llega a casa ---
Bot → Nico: 🏠 ¡Nico llegó a casa!
            📋 Recordatorios:
              1. Tirar la basura

--- Mama llega a casa ---
Bot → Mama: 🏠 ¡Mama llegó a casa!
            📋 Recordatorios:
              1. Tirar la basura

(El recordatorio se borra automáticamente porque ya lo recibieron todos)
```

---

## Parámetros internos

Se pueden ajustar al principio de `main.py`:

| Variable | Default | Descripción |
|---|---|---|
| `CHECK_INTERVAL` | `5` | Segundos entre cada comprobación por dispositivo |
| `MARGEN_SALIDA` | `10` | Fallos seguidos para confirmar que el dispositivo salió de la red |

---

## Archivos del proyecto

```
RecordatoriosBot/
├── main.py           # Lógica principal del bot
├── reminders.json    # Recordatorios pendientes (se crea automáticamente)
├── .env              # Configuración privada (no subir al repo)
├── .env.example      # Plantilla de configuración
└── prueba_arping.py  # Script para probar la detección de un dispositivo
```

