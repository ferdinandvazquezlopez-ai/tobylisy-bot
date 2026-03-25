from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import yt_dlp
import os
from collections import defaultdict
from datetime import time as dt_time
from zoneinfo import ZoneInfo
import time
from telegram.constants import ChatMemberStatus

user_messages = defaultdict(list)

warnings = {}

TOKEN = os.getenv("TOKEN")
GROUP_ID = -1002651241737
ADMIN_IDS = [5342233495, -5342233495]

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
    "fuck", "shit", "bitch", "asshole", "bastard", "pulpo", "moco", "estupida"
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
    await anti_spam(update, context)

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
                await update.effective_chat.send_message(
                    f"🟡 {user.first_name}, primera advertencia.\nRespeta las reglas."
                )

            elif warnings[user_id] == 2:
                await update.effective_chat.send_message(
                    f"🟠 {user.first_name}, segunda advertencia.\nPróxima advertencia = expulsión."
                )

            elif warnings[user_id] >= 3:
                try:
                    await update.message.chat.ban_member(user_id)
                    await update.message.chat.unban_member(user_id)
                except:
                    pass

                await update.effective_chat.send_message(
                    f"🔴 {user.first_name} fue expulsado por acumular 3 advertencias."
                )

            break

async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Para reportar, responde al mensaje de la persona y escribe /reporte"
        )
        return

    mensaje_reportado = update.message.reply_to_message
    usuario_reportado = mensaje_reportado.from_user
    usuario_reporta = update.message.from_user

    texto_reportado = mensaje_reportado.text if mensaje_reportado.text else "[mensaje no textual]"

    await update.message.reply_text(
        f"🚨 Reporte recibido.\n"
        f"Reportado: {usuario_reportado.first_name}\n"
        f"Reportó: {usuario_reporta.first_name}\n"
        f"Mensaje: {texto_reportado}"
    )

async def mis_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    cantidad = warnings.get(user_id, 0)

    await update.message.reply_text(
        f"📊 {user.first_name}, tienes {cantidad} advertencia(s)."
    )

async def reset_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al usuario para resetear warnings.")
        return

    user = update.message.reply_to_message.from_user
    user_id = user.id

    warnings[user_id] = 0

    await update.message.reply_text(
        f"✅ Warnings de {user.first_name} fueron reiniciados."
    )

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.message.from_user
    user_id = user.id
    now = time.time()

    user_messages[user_id] = [t for t in user_messages[user_id] if now - t < 5]
    user_messages[user_id].append(now)

    if len(user_messages[user_id]) > 5:
        try:
            await update.message.delete()
        except:
            pass

        await update.message.reply_text(
            f"⚠️ {user.first_name}, estás enviando muchos mensajes (spam)."
        )

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = await update.effective_chat.get_member(update.effective_user.id)

    # 🔒 Solo admins pueden usarlo
    if admin.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return

    # ⚠️ Debe ser reply
    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al mensaje o foto del usuario para darle warning.")
        return

    user = update.message.reply_to_message.from_user
    user_id = user.id

    warnings[user_id] = warnings.get(user_id, 0) + 1

    if warnings[user_id] == 1:
        await update.effective_chat.send_message(
            f"🟡 {user.first_name} recibe una advertencia por contenido fuera de lugar."
        )

    elif warnings[user_id] == 2:
        await update.effective_chat.send_message(
            f"🟠 {user.first_name} recibe su segunda advertencia. Próxima falta = expulsión."
        )

    elif warnings[user_id] >= 3:
        try:
            await update.message.chat.ban_member(user_id)
            await update.message.chat.unban_member(user_id)
        except:
            pass

        await update.effective_chat.send_message(
            f"🔴 {user.first_name} fue expulsado por acumulación de advertencias."
        )

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = await update.effective_chat.get_member(update.effective_user.id)

    if admin.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al mensaje del usuario para silenciarlo.")
        return

    user = update.message.reply_to_message.from_user

    try:
        await update.message.chat.restrict_member(
            user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=int(time.time()) + 600
        )
        await update.effective_chat.send_message(
            f"🔇 {user.first_name} fue silenciado por 10 minutos."
        )
    except:
        await update.effective_chat.send_message(
            f"No pude silenciar a {user.first_name}."
        )

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = await update.effective_chat.get_member(update.effective_user.id)

    if admin.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al mensaje del usuario para quitarle el mute.")
        return

    user = update.message.reply_to_message.from_user

    try:
        await update.message.chat.restrict_member(
            user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
        )
        await update.effective_chat.send_message(
            f"🔊 {user.first_name} ya puede volver a escribir."
        )
    except:
        await update.effective_chat.send_message(
            f"No pude quitar el mute a {user.first_name}."
        )

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = await update.effective_chat.get_member(update.effective_user.id)

    if admin.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al mensaje del usuario para expulsarlo.")
        return

    user = update.message.reply_to_message.from_user

    try:
        await update.message.chat.ban_member(user.id)
        await update.effective_chat.send_message(
            f"🚫 {user.first_name} fue expulsado por un administrador."
        )
    except:
        await update.effective_chat.send_message(
            f"No pude expulsar a {user.first_name}."
        )

async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Chat ID: {update.effective_chat.id}")

async def cerrar_chat(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text="🌙 Chat cerrado, nos vemos en la mañana. Descansen."
        )
    except Exception as e:
        print(f"Error cerrando chat: {e}")


async def abrir_chat(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=False,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
        )
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text="☀️ Buenos días, chat abierto."
        )
    except Exception as e:
        print(f"Error abriendo chat: {e}")

async def adminhelp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    member = await context.bot.get_chat_member(chat_id, user_id)

    if member.status not in ["administrator", "creator"]:
        return

    try:
        await update.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🔧 *Panel de Administrador*\n\n"
            "⚠️ Moderación:\n"
            "/warn (reply) - Dar advertencia\n"
            "/reset (reply) - Reset warnings\n"
            "/mute (reply) - Silenciar usuario\n"
            "/unmute (reply) - Quitar mute\n"
            "/ban (reply) - Expulsar usuario\n\n"
            "📊 Información:\n"
            "/warnings (reply) - Ver warnings de usuario\n"
            "/chatid - Ver ID del grupo\n\n"
            "⚙️ Sistema:\n"
            "Auto cierre: 12:00 AM\n"
            "Auto apertura: 7:00 AM\n"
        ),
        parse_mode="Markdown"
    )

async def cerrar_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Tu ID detectado es: {update.effective_user.id}"
    )

    if update.effective_user.id not in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No tienes permisos para usar /cerrar."
        )
        return

    try:
        await update.message.delete()
    except Exception:
        pass

    try:
        await context.bot.set_chat_permissions(
            chat_id=update.effective_chat.id,
            permissions=ChatPermissions(can_send_messages=False)
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🌙 Chat cerrado por un administrador."
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Error al cerrar el chat: {e}"
        )

async def abrir_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No tienes permisos para usar /abrir."
        )
        return

    try:
        await update.message.delete()
    except Exception:
        pass

    try:
        await context.bot.set_chat_permissions(
            chat_id=update.effective_chat.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=False,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="☀️ Chat abierto por un administrador."
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Error al abrir el chat: {e}"
        )

app = ApplicationBuilder().token(TOKEN).build()

job_queue = app.job_queue

job_queue.run_daily(
    cerrar_chat,
    time=dt_time(hour=0, minute=0, tzinfo=ZoneInfo("America/Chicago"))
)

job_queue.run_daily(
    abrir_chat,
    time=dt_time(hour=7, minute=0, tzinfo=ZoneInfo("America/Chicago"))
)
app.add_handler(CommandHandler("reglas", reglas))
app.add_handler(CommandHandler("reporte", reporte))
app.add_handler(CommandHandler("reset", reset_warnings))
app.add_handler(CommandHandler("warnings", mis_warnings))
app.add_handler(CommandHandler("warn", warn))
app.add_handler(CommandHandler("mute", mute))
app.add_handler(CommandHandler("unmute", unmute))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("adminhelp", adminhelp))
app.add_handler(CommandHandler("chatid", chatid))
app.add_handler(CommandHandler("cerrar", cerrar_manual))
app.add_handler(CommandHandler("abrir", abrir_manual))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderar))

app.run_polling()
