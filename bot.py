from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import os
from collections import defaultdict
from datetime import time as dt_time
from zoneinfo import ZoneInfo
import time
from telegram.constants import ChatMemberStatus

warnings = {}
user_messages = defaultdict(list)
last_sender = None
consecutive_count = 0

TOKEN = os.getenv("TOKEN")
GROUP_ID = -1002651241737
LOG_GROUP_ID = -1003709178512

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
    "zangano", "asqueroso",
    "porqueria", "mierda", "jodio", "mamabicho", "moron",
    "stupid", "idiot", "dumb", "trash", "loser",
    "fuck", "shit", "bitch", "asshole", "bastard", "pulpo", "moco", "estupida", "estúpido", "estúpida"
]

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

    result = await anti_spam(update, context)
    if result:
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

                await enviar_log(
                    context,
                    f"📋 LOG MODERACIÓN\n"
                    f"Usuario: {user.first_name}\n"
                    f"Acción: EXPULSIÓN AUTOMÁTICA\n"
                    f"Motivo: 3 advertencias acumuladas"
                )

            await enviar_log(
                context,
                f"📋 LOG MODERACIÓN\n"
                f"Usuario: {user.first_name}\n"
                f"Acción: WARNING AUTOMÁTICO\n"
                f"Palabra detectada: {palabra}\n"
                f"Total warnings: {warnings[user_id]}"
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

    await enviar_log(
        context,
        f"📋 LOG REPORTE\n"
        f"Reportó: {usuario_reporta.first_name}\n"
        f"Usuario reportado: {usuario_reportado.first_name}\n"
        f"Mensaje: {texto_reportado}"
    )

async def mis_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await update.effective_chat.get_member(update.effective_user.id)

    # Si responde a alguien y es admin, ve los warnings de esa persona
    if update.message.reply_to_message:
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return

        user = update.message.reply_to_message.from_user
        user_id = user.id
        cantidad = warnings.get(user_id, 0)

        await update.effective_chat.send_message(
            f"📊 {user.first_name} tiene {cantidad} advertencia(s)."
        )
        return

    # Si no responde a nadie, ve sus propios warnings
    user = update.message.from_user
    user_id = user.id
    cantidad = warnings.get(user_id, 0)

    await update.message.reply_text(
        f"📊 {user.first_name}, tienes {cantidad} advertencia(s)."
    )

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_sender, consecutive_count

    if not update.message or not update.message.from_user:
        return False

    user = update.message.from_user
    user_id = user.id
    now = time.time()

    # ---------------------------
    # 🔹 CONTROL POR TIEMPO (5 seg)
    # ---------------------------
    user_messages[user_id] = [t for t in user_messages[user_id] if now - t < 5]
    user_messages[user_id].append(now)

    flood = len(user_messages[user_id]) > 10

    # ---------------------------
    # 🔹 CONTROL CONSECUTIVO
    # ---------------------------
    if last_sender == user_id:
        consecutive_count += 1
    else:
        consecutive_count = 1
        last_sender = user_id

    consecutivo = consecutive_count >= 10

    # ---------------------------
    # 🔥 SI SE ACTIVA ALGUNO
    # ---------------------------
    if flood or consecutivo:
        try:
            await update.message.delete()
        except:
            pass

        try:
            await update.message.chat.restrict_member(
                user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=int(time.time()) + 180
            )

            motivo = "SPAM (ráfaga de más de 10 mensajes en 5 segundos)" if flood else "MONOPOLIZANDO EL CHAT (10 mensajes consecutivos)"

            await update.effective_chat.send_message(
                f"⏸️ {user.first_name}, necesitas un break de 3 minutos.\nTómate un café ☕\nMotivo: {motivo}"
            )

            await enviar_log(
                context,
                f"📋 LOG MODERACIÓN\n"
                f"Usuario: {user.first_name}\n"
                f"Acción: AUTO MUTE\n"
                f"Duración: 3 minutos\n"
                f"Motivo: {motivo}"
            )

        except Exception as e:
            await update.effective_chat.send_message(
                f"No pude aplicar mute automático a {user.first_name}. Error: {e}"
            )

        # Resetear contadores
        user_messages[user_id] = []
        consecutive_count = 0
        last_sender = None

        return True

    return False

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await update.effective_chat.get_member(update.effective_user.id)

    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return

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

    admin_name = update.effective_user.first_name
    user_name = user.first_name
    cantidad = warnings[user_id]

    await enviar_log(
        context,
        f"📋 LOG MODERACIÓN\n"
        f"Admin: {admin_name}\n"
        f"Usuario: {user_name}\n"
        f"Acción: WARN\n"
        f"Total warnings: {cantidad}"
    )

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await update.effective_chat.get_member(update.effective_user.id)

    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
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

        admin_name = update.effective_user.first_name
        user_name = user.first_name

        await enviar_log(
            context,
            f"📋 LOG MODERACIÓN\n"
            f"Admin: {admin_name}\n"
            f"Usuario: {user_name}\n"
            f"Acción: MUTE\n"
            f"Duración: 10 minutos"
        )
    except Exception as e:
        await update.effective_chat.send_message(
            f"No pude silenciar a {user.first_name}. Error: {e}"
        )

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await update.effective_chat.get_member(update.effective_user.id)

    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
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

        admin_name = update.effective_user.first_name
        user_name = user.first_name

        await enviar_log(
            context,
            f"📋 LOG MODERACIÓN\n"
            f"Admin: {admin_name}\n"
            f"Usuario: {user_name}\n"
            f"Acción: UNMUTE"
        )
    except Exception as e:
        await update.effective_chat.send_message(
            f"No pude quitar el mute a {user.first_name}. Error: {e}"
        )

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await update.effective_chat.get_member(update.effective_user.id)

    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
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

        admin_name = update.effective_user.first_name
        user_name = user.first_name

        await enviar_log(
            context,
            f"📋 LOG MODERACIÓN\n"
            f"Admin: {admin_name}\n"
            f"Usuario: {user_name}\n"
            f"Acción: BAN"
        )
    except Exception as e:
        await update.effective_chat.send_message(
            f"No pude expulsar a {user.first_name}. Error: {e}"
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
            text="🌙 Chat cerrado. Nos vemos en la mañana. Descansen."
        )

        await enviar_log(
            context,
            "📋 LOG SISTEMA\nAcción: CIERRE AUTOMÁTICO DEL CHAT"
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
            text="☀️ Buenos días. Chat abierto."
        )

        await enviar_log(
            context,
            "📋 LOG SISTEMA\nAcción: APERTURA AUTOMÁTICA DEL CHAT"
        )
    except Exception as e:
        print(f"Error abriendo chat: {e}")

async def adminhelp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await update.effective_chat.get_member(update.effective_user.id)

    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return

    try:
        await update.message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🔧 *Panel de Administrador*\n\n"
            "⚠️ Moderación:\n"
            "/warn (reply) - Dar advertencia\n"
            "/unwarn (reply) - Quitar un warning\n"
            "/reset (reply) - Reset warnings\n"
            "/mute (reply) - Silenciar usuario\n"
            "/unmute (reply) - Quitar mute\n"
            "/ban (reply) - Expulsar usuario\n\n"
            "📊 Información:\n"
            "/warnings - Ver tus warnings\n"
            "/warnings (reply) - Ver warnings de otro usuario\n"
            "/chatid - Ver ID del grupo\n\n"
            "⚙️ Sistema:\n"
            "Auto cierre: 12:00 AM\n"
            "Auto apertura: 7:00 AM\n"
        ),
        parse_mode="Markdown"
    )

async def enviar_log(context: ContextTypes.DEFAULT_TYPE, mensaje: str):
    try:
        await context.bot.send_message(
            chat_id=LOG_GROUP_ID,
            text=mensaje
        )
    except Exception as e:
        print(f"Error enviando log: {e}")

async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await update.effective_chat.get_member(update.effective_user.id)

    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al mensaje del usuario para quitarle un warning.")
        return

    user = update.message.reply_to_message.from_user
    user_id = user.id

    warnings[user_id] = max(warnings.get(user_id, 0) - 1, 0)

    await update.effective_chat.send_message(
        f"✅ Se removió un warning a {user.first_name}.\nWarnings actuales: {warnings[user_id]}"
    )

    admin_name = update.effective_user.first_name
    user_name = user.first_name

    await enviar_log(
        context,
        f"📋 LOG MODERACIÓN\n"
        f"Admin: {admin_name}\n"
        f"Usuario: {user_name}\n"
        f"Acción: UNWARN\n"
        f"Total warnings: {warnings[user_id]}"
    )

async def reset_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await update.effective_chat.get_member(update.effective_user.id)

    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al usuario para resetear warnings.")
        return

    user = update.message.reply_to_message.from_user
    user_id = user.id

    warnings[user_id] = 0

    await update.effective_chat.send_message(
        f"♻️ Warnings de {user.first_name} han sido reiniciados."
    )

    await enviar_log(
        context,
        f"📋 LOG MODERACIÓN\n"
        f"Admin: {update.effective_user.first_name}\n"
        f"Usuario: {user.first_name}\n"
        f"Acción: RESET WARNINGS"
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
app.add_handler(CommandHandler("unwarn", unwarn))
app.add_handler(CommandHandler("mute", mute))
app.add_handler(CommandHandler("unmute", unmute))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("adminhelp", adminhelp))
app.add_handler(CommandHandler("chatid", chatid))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderar))

app.run_polling()
