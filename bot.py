from collections import defaultdict
from datetime import time as dt_time
import os
import time as time_module
from zoneinfo import ZoneInfo

from telegram import ChatPermissions, Update
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


warnings_by_user = {}
user_messages = defaultdict(list)
last_sender = None
consecutive_count = 0

TOKEN = os.getenv("TOKEN")
GROUP_ID = -1002651241737
LOG_GROUP_ID = -1003709178512
TIMEZONE = ZoneInfo("America/Chicago")

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
    "idiota",
    "estupido",
    "cabron",
    "pendejo",
    "imbecil",
    "basura",
    "ridiculo",
    "asqueroso",
    "porqueria",
    "mierda",
    "jodio",
    "mamabicho",
    "moron",
    "stupid",
    "idiot",
    "dumb",
    "trash",
    "loser",
    "fuck",
    "shit",
    "bitch",
    "asshole",
    "bastard",
    "pulpo",
    "moco"
    
]


def allowed_chat_permissions() -> ChatPermissions:
    return ChatPermissions(
        can_send_messages=True,
        can_send_audios=False,
        can_send_documents=False,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=False,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False,
    )


def closed_chat_permissions() -> ChatPermissions:
    return ChatPermissions(can_send_messages=False)


def is_chat_open_permissions(permissions: ChatPermissions | None) -> bool:
    return bool(permissions and permissions.can_send_messages)


async def is_admin(update: Update) -> bool:
    if not update.effective_chat or not update.effective_user:
        return False

    member = await update.effective_chat.get_member(update.effective_user.id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]


def warning_count(user_id: int) -> int:
    return warnings_by_user.get(user_id, 0)


def increment_warning(user_id: int) -> int:
    warnings_by_user[user_id] = warning_count(user_id) + 1
    return warnings_by_user[user_id]


async def enviar_log(context: ContextTypes.DEFAULT_TYPE, mensaje: str):
    try:
        await context.bot.send_message(chat_id=LOG_GROUP_ID, text=mensaje)
    except Exception as exc:
        print(f"Error enviando log: {exc}")


async def expulsar_usuario(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    user_name: str,
    motivo: str,
):
    try:
        await update.effective_chat.ban_member(user_id)
        await update.effective_chat.unban_member(user_id)
    except Exception:
        pass

    await update.effective_chat.send_message(
        f"🔴 {user_name} fue expulsado por acumulación de advertencias."
    )
    await enviar_log(
        context,
        f"📋 LOG MODERACIÓN\n"
        f"Usuario: {user_name}\n"
        f"Acción: EXPULSIÓN AUTOMÁTICA\n"
        f"Motivo: {motivo}",
    )


async def reglas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(REGLAS)


async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    for member in update.message.new_chat_members:
        await update.message.reply_text(f"👋 Bienvenido/a {member.first_name}\n\n{REGLAS}")


async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_sender, consecutive_count

    if not update.message or not update.message.from_user:
        return False

    if await is_admin(update):
        return False

    user = update.message.from_user
    user_id = user.id
    now = time_module.time()

    user_messages[user_id] = [t for t in user_messages[user_id] if now - t < 5]
    user_messages[user_id].append(now)
    flood = len(user_messages[user_id]) > 10

    if last_sender == user_id:
        consecutive_count += 1
    else:
        consecutive_count = 1
        last_sender = user_id

    consecutivo = consecutive_count >= 10

    if not flood and not consecutivo:
        return False

    try:
        await update.message.delete()
    except Exception:
        pass

    try:
        await update.message.chat.restrict_member(
            user_id,
            permissions=closed_chat_permissions(),
            until_date=int(time_module.time()) + 180,
        )

        motivo = (
            "SPAM (ráfaga de más de 10 mensajes en 5 segundos)"
            if flood
            else "MONOPOLIZANDO EL CHAT (10 mensajes consecutivos)"
        )

        await update.effective_chat.send_message(
            f"⏸️ {user.first_name}, necesitas un break de 3 minutos.\n"
            f"Tómate un café ☕\n"
            f"Motivo: {motivo}"
        )

        await enviar_log(
            context,
            f"📋 LOG MODERACIÓN\n"
            f"Usuario: {user.first_name}\n"
            f"Acción: AUTO MUTE\n"
            f"Duración: 3 minutos\n"
            f"Motivo: {motivo}",
        )
    except Exception as exc:
        await update.effective_chat.send_message(
            f"No pude aplicar mute automático a {user.first_name}. Error: {exc}"
        )

    user_messages[user_id] = []
    consecutive_count = 0
    last_sender = None
    return True


async def bloquear_contenido_no_permitido(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    if not update.message or not update.message.from_user:
        return False

    if await is_admin(update):
        return False

    message = update.message
    user = message.from_user

    tipo_bloqueado = None
    if message.audio:
        tipo_bloqueado = "audios/música"
    elif message.document:
        tipo_bloqueado = "archivos/documentos"
    elif message.voice:
        tipo_bloqueado = "notas de voz"

    if not tipo_bloqueado:
        return False

    try:
        await message.delete()
    except Exception:
        pass

    await update.effective_chat.send_message(
        f"🚫 {user.first_name}, ese tipo de contenido no está permitido aquí.\n"
        f"Bloqueado: {tipo_bloqueado}"
    )
    await enviar_log(
        context,
        f"📋 LOG MODERACIÓN\n"
        f"Usuario: {user.first_name}\n"
        f"Acción: CONTENIDO ELIMINADO\n"
        f"Tipo bloqueado: {tipo_bloqueado}",
    )
    return True


async def moderar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if await anti_spam(update, context):
        return

    texto = update.message.text.lower()
    user = update.message.from_user
    user_id = user.id

    for palabra in PALABRAS_PROHIBIDAS:
        if palabra not in texto:
            continue

        try:
            await update.message.delete()
        except Exception:
            pass

        total_warnings = increment_warning(user_id)

        if total_warnings == 1:
            await update.effective_chat.send_message(
                f"🟡 {user.first_name}, primera advertencia.\nRespeta las reglas."
            )
        elif total_warnings == 2:
            await update.effective_chat.send_message(
                f"🟠 {user.first_name}, segunda advertencia.\n"
                f"Próxima advertencia = expulsión."
            )
        else:
            await expulsar_usuario(
                update,
                context,
                user_id,
                user.first_name,
                "3 advertencias acumuladas",
            )

        await enviar_log(
            context,
            f"📋 LOG MODERACIÓN\n"
            f"Usuario: {user.first_name}\n"
            f"Acción: WARNING AUTOMÁTICO\n"
            f"Palabra detectada: {palabra}\n"
            f"Total warnings: {total_warnings}",
        )
        break


async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Para reportar, responde al mensaje de la persona y escribe /reporte."
        )
        return

    mensaje_reportado = update.message.reply_to_message
    usuario_reportado = mensaje_reportado.from_user
    usuario_reporta = update.message.from_user
    texto_reportado = mensaje_reportado.text or "[mensaje no textual]"

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
        f"Mensaje: {texto_reportado}",
    )


async def mis_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    if update.message.reply_to_message:
        if not await is_admin(update):
            return

        user = update.message.reply_to_message.from_user
        cantidad = warning_count(user.id)
        await update.effective_chat.send_message(
            f"📊 {user.first_name} tiene {cantidad} advertencia(s)."
        )
        return

    cantidad = warning_count(update.effective_user.id)
    await update.message.reply_text(
        f"📊 {update.effective_user.first_name}, tienes {cantidad} advertencia(s)."
    )


async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Responde al mensaje o foto del usuario para darle warning."
        )
        return

    user = update.message.reply_to_message.from_user
    total_warnings = increment_warning(user.id)

    if total_warnings == 1:
        await update.effective_chat.send_message(
            f"🟡 {user.first_name} recibe una advertencia por contenido fuera de lugar."
        )
    elif total_warnings == 2:
        await update.effective_chat.send_message(
            f"🟠 {user.first_name} recibe su segunda advertencia. "
            f"Próxima falta = expulsión."
        )
    else:
        await expulsar_usuario(
            update,
            context,
            user.id,
            user.first_name,
            "3 advertencias acumuladas (manuales)",
        )

    await enviar_log(
        context,
        f"📋 LOG MODERACIÓN\n"
        f"Admin: {update.effective_user.first_name}\n"
        f"Usuario: {user.first_name}\n"
        f"Acción: WARN\n"
        f"Total warnings: {total_warnings}",
    )


async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Responde al mensaje del usuario para quitarle un warning."
        )
        return

    user = update.message.reply_to_message.from_user
    warnings_by_user[user.id] = max(warning_count(user.id) - 1, 0)

    await update.effective_chat.send_message(
        f"✅ Se removió un warning a {user.first_name}.\n"
        f"Warnings actuales: {warnings_by_user[user.id]}"
    )

    await enviar_log(
        context,
        f"📋 LOG MODERACIÓN\n"
        f"Admin: {update.effective_user.first_name}\n"
        f"Usuario: {user.first_name}\n"
        f"Acción: UNWARN\n"
        f"Total warnings: {warnings_by_user[user.id]}",
    )


async def reset_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al usuario para resetear warnings.")
        return

    user = update.message.reply_to_message.from_user
    warnings_by_user[user.id] = 0

    await update.effective_chat.send_message(
        f"♻️ Warnings de {user.first_name} han sido reiniciados."
    )

    await enviar_log(
        context,
        f"📋 LOG MODERACIÓN\n"
        f"Admin: {update.effective_user.first_name}\n"
        f"Usuario: {user.first_name}\n"
        f"Acción: RESET WARNINGS",
    )


async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al mensaje del usuario para silenciarlo.")
        return

    user = update.message.reply_to_message.from_user

    try:
        await update.message.chat.restrict_member(
            user.id,
            permissions=closed_chat_permissions(),
            until_date=int(time_module.time()) + 600,
        )
        await update.effective_chat.send_message(
            f"🔇 {user.first_name} fue silenciado por 10 minutos."
        )
        await enviar_log(
            context,
            f"📋 LOG MODERACIÓN\n"
            f"Admin: {update.effective_user.first_name}\n"
            f"Usuario: {user.first_name}\n"
            f"Acción: MUTE\n"
            f"Duración: 10 minutos",
        )
    except Exception as exc:
        await update.effective_chat.send_message(
            f"No pude silenciar a {user.first_name}. Error: {exc}"
        )


async def moderar_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await bloquear_contenido_no_permitido(update, context)


async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Responde al mensaje del usuario para quitarle el mute.")
        return

    user = update.message.reply_to_message.from_user

    try:
        await update.message.chat.restrict_member(
            user.id,
            permissions=allowed_chat_permissions(),
        )
        await update.effective_chat.send_message(
            f"🔊 {user.first_name} ya puede volver a escribir."
        )
        await enviar_log(
            context,
            f"📋 LOG MODERACIÓN\n"
            f"Admin: {update.effective_user.first_name}\n"
            f"Usuario: {user.first_name}\n"
            f"Acción: UNMUTE",
        )
    except Exception as exc:
        await update.effective_chat.send_message(
            f"No pude quitar el mute a {user.first_name}. Error: {exc}"
        )


async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not await is_admin(update):
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
        await enviar_log(
            context,
            f"📋 LOG MODERACIÓN\n"
            f"Admin: {update.effective_user.first_name}\n"
            f"Usuario: {user.first_name}\n"
            f"Acción: BAN",
        )
    except Exception as exc:
        await update.effective_chat.send_message(
            f"No pude expulsar a {user.first_name}. Error: {exc}"
        )


async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.effective_chat:
        await update.message.reply_text(f"Chat ID: {update.effective_chat.id}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return

    if not await is_admin(update):
        return

    bot_member = await update.effective_chat.get_member(context.bot.id)
    bot_permissions = getattr(bot_member, "can_delete_messages", None)
    chat = update.effective_chat
    permisos = chat.permissions

    estado_chat = "abierto" if is_chat_open_permissions(permisos) else "cerrado"
    estado_job_queue = "activo" if context.job_queue else "no disponible"
    token_status = "configurado" if TOKEN else "faltante"

    await update.message.reply_text(
        "📊 Estado del bot\n\n"
        f"Chat: {estado_chat}\n"
        f"Token: {token_status}\n"
        f"Job queue: {estado_job_queue}\n"
        f"Bot es admin: {'sí' if bot_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] else 'no'}\n"
        f"Puede borrar mensajes: {'sí' if bot_permissions else 'no'}\n\n"
        "Permisos activos del grupo:\n"
        f"Mensajes: {'sí' if permisos and permisos.can_send_messages else 'no'}\n"
        f"Fotos: {'sí' if permisos and permisos.can_send_photos else 'no'}\n"
        f"Videos: {'sí' if permisos and permisos.can_send_videos else 'no'}\n"
        f"Video messages: {'sí' if permisos and permisos.can_send_video_notes else 'no'}\n"
        f"Stickers/GIFs/links: {'sí' if permisos and permisos.can_send_other_messages else 'no'}\n"
        f"Polls: {'sí' if permisos and permisos.can_send_polls else 'no'}\n"
        f"Audios: {'sí' if permisos and permisos.can_send_audios else 'no'}\n"
        f"Documentos: {'sí' if permisos and permisos.can_send_documents else 'no'}\n"
        f"Voice notes: {'sí' if permisos and permisos.can_send_voice_notes else 'no'}\n"
        f"Add members: {'sí' if permisos and permisos.can_invite_users else 'no'}\n"
        f"Cambiar info: {'sí' if permisos and permisos.can_change_info else 'no'}\n"
        f"Pin messages: {'sí' if permisos and permisos.can_pin_messages else 'no'}"
    )


async def adminhelp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not await is_admin(update):
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
            "/status - Ver estado del bot y permisos\n"
            "/openchat - Abrir el chat manualmente\n"
            "/closechat - Cerrar el chat manualmente\n"
            "Auto cierre: 12:00 AM\n"
            "Auto apertura: 7:00 AM\n"
        ),
        parse_mode="Markdown",
    )


async def cerrar_chat(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=closed_chat_permissions(),
        )
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text="🌙 Chat cerrado. Nos vemos en la mañana. Descansen.",
        )
        await enviar_log(context, "📋 LOG SISTEMA\nAcción: CIERRE AUTOMÁTICO DEL CHAT")
    except Exception as exc:
        print(f"Error cerrando chat: {exc}")


async def abrir_chat(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=allowed_chat_permissions(),
        )
        await context.bot.send_message(chat_id=GROUP_ID, text="☀️ Buenos días. Chat abierto.")
        await enviar_log(context, "📋 LOG SISTEMA\nAcción: APERTURA AUTOMÁTICA DEL CHAT")
    except Exception as exc:
        print(f"Error abriendo chat: {exc}")


async def openchat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not await is_admin(update):
        return

    try:
        await context.bot.set_chat_permissions(
            chat_id=update.effective_chat.id,
            permissions=allowed_chat_permissions(),
        )
        await update.effective_chat.send_message("☀️ Chat abierto manualmente.")
        await enviar_log(
            context,
            f"📋 LOG SISTEMA\n"
            f"Admin: {update.effective_user.first_name}\n"
            f"Acción: APERTURA MANUAL DEL CHAT",
        )
    except Exception as exc:
        await update.effective_chat.send_message(f"No pude abrir el chat. Error: {exc}")


async def closechat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not await is_admin(update):
        return

    try:
        await context.bot.set_chat_permissions(
            chat_id=update.effective_chat.id,
            permissions=closed_chat_permissions(),
        )
        await update.effective_chat.send_message("🌙 Chat cerrado manualmente.")
        await enviar_log(
            context,
            f"📋 LOG SISTEMA\n"
            f"Admin: {update.effective_user.first_name}\n"
            f"Acción: CIERRE MANUAL DEL CHAT",
        )
    except Exception as exc:
        await update.effective_chat.send_message(f"No pude cerrar el chat. Error: {exc}")


def main():
    if not TOKEN:
        raise RuntimeError("No encontré la variable de entorno TOKEN.")

    app = ApplicationBuilder().token(TOKEN).build()

    if not app.job_queue:
        raise RuntimeError(
            "JobQueue no está disponible. Instala python-telegram-bot con extras de job-queue."
        )

    app.job_queue.run_daily(cerrar_chat, time=dt_time(hour=0, minute=0, tzinfo=TIMEZONE))
    app.job_queue.run_daily(abrir_chat, time=dt_time(hour=7, minute=0, tzinfo=TIMEZONE))

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
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("openchat", openchat))
    app.add_handler(CommandHandler("closechat", closechat))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderar))
    app.add_handler(
        MessageHandler(filters.AUDIO | filters.Document.ALL | filters.VOICE, moderar_media)
    )

    app.run_polling()


if __name__ == "__main__":
    main()
