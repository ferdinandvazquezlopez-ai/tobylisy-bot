from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import yt_dlp
import os

TOKEN = os.getenv("TOKEN")

REGLAS = """
📌 REGLAS DEL CHAT – TOBY AND LISY

Saludos mi gente 🙌

Para mantener un ambiente sano y competitivo:

1️⃣ Contenido permitido
• Sin hate hacia participantes
• Sin desprecio a fandoms

2️⃣ Somos Team Imparcial 💥
Debate con respeto.

3️⃣ Debate sí, ofensas no 🔥
• Sin insultos
• Sin ataques personales

4️⃣ Horario del chat
Se cierra en la noche y abre en la mañana.

¡Disfrutemos sin odio! 🤝
"""

PALABRAS_PROHIBIDAS = [
    "idiota", "estupido", "bruto", "cabron", "pendejo",
    "imbecil", "basura", "ridiculo",
    "zangano", "loco", "asqueroso",
    "porqueria", "mierda", "jodio", "mamabicho", "moron",
    "stupid", "idiot", "dumb", "trash", "loser",
    "fuck", "shit", "bitch", "asshole", "bastard", "pulpo", "moco"
]

warnings = {}

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    if "instagram.com" in text or "tiktok.com" in text:
        ydl_opts = {
            "outtmpl": "video.%(ext)s",
            "format": "mp4/best"
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                filename = ydl.prepare_filename(info)

            with open(filename, "rb") as f:
                await update.message.reply_video(video=f)
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

async def reglas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(REGLAS)


async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"👋 Bienvenido/a {member.first_name}\n\n{REGLAS}"
        )



async def moderar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto = update.message.text.lower()
    user = update.message.from_user
    user_id = user.id

    for palabra in PALABRAS_PROHIBIDAS:
        if palabra in texto:
            try:
                await update.message.delete()
            except:
                pass

            warnings[user_id] = warnings.get(user_id, 0) + 1

            if warnings[user_id] == 1:
                await update.message.reply_text(
                    f"🟡 {user.first_name}, primera advertencia.\nRespeta las reglas."
                )

            elif warnings[user_id] == 2:
                await update.message.reply_text(
                    f"🟠 {user.first_name}, segunda advertencia.\nPróxima advertencia = expulsión."
                )

            elif warnings[user_id] >= 3:
                try:
                    await update.message.chat.ban_member(user_id)
                    await update.message.chat.unban_member(user_id)
                except:
                    pass

                await update.message.reply_text(
                    f"🔴 {user.first_name} fue expulsado por acumular 3 advertencias."
                )

            break

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("reglas", reglas))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderar))

app.run_polling()
