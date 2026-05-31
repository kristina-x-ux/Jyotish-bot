"""
╔══════════════════════════════════════╗
║   ДЖЙОТИШ ТРАНЗИТ БОТ — bot.py      ║
║   Powered by Google Gemini (FREE)    ║
╚══════════════════════════════════════╝
"""

import logging
import os
from datetime import datetime
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from database import Database
from jyotish import get_current_transits, get_transit_context

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Инициализация ──────────────────────────────────────────────────────
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini = genai.GenerativeModel("gemini-2.0-flash")

WAITING_BIRTH_DATE = 1
WAITING_BIRTH_TIME = 2
WAITING_BIRTH_PLACE = 3

db = Database("/data/users.db")


# ── Системный промпт ───────────────────────────────────────────────────
def build_system_prompt(user_data: dict) -> str:
    transits = get_current_transits()
    today = datetime.now().strftime("%d.%m.%Y")

    natal_info = ""
    if user_data.get("birth_date"):
        natal_info = f"""
НАТАЛЬНЫЕ ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:
• Дата рождения: {user_data['birth_date']}
• Время рождения: {user_data.get('birth_time', 'не указано')}
• Место рождения: {user_data.get('birth_place', 'не указано')}
• Лагна (Асцендент): {user_data.get('lagna', 'не рассчитана')}
• Луна в накшатре: {user_data.get('moon_nakshatra', 'не рассчитана')}
• Текущая Маха-Даша: {user_data.get('mahadasha', 'не рассчитана')}
• Текущая Антар-Даша: {user_data.get('antardasha', 'не рассчитана')}
"""

    return f"""Ты — опытный джйотиш-астролог. Даёшь практичные, конкретные интерпретации транзитов планет по системе Джйотиш (ведическая астрология).

СЕГОДНЯ: {today}

ТЕКУЩИЕ ТРАНЗИТЫ ПЛАНЕТ:
{transits}

{natal_info}

ПРАВИЛА РАБОТЫ:
1. Используй ТОЛЬКО терминологию Джйотиш: Граха, Раши, Бхава, Накшатры, Даша-система
2. Давай ПРАКТИЧНЫЕ рекомендации — что делать, чего избегать, в какие сферы направить энергию
3. Указывай КОНКРЕТНЫЕ периоды влияния транзита
4. Упоминай аспекты (дришти) и соединения (юти) планет
5. Учитывай силу планет: уччха, нича, сваграха
6. Если есть натальные данные — соотноси транзиты с натальными домами и Дашей
7. Отвечай кратко и по делу — не более 300 слов, структурированно
8. Используй эмодзи: ☀️ Солнце, 🌙 Луна, 🔴 Марс, 🟡 Меркурий, 🟠 Юпитер, ⚪ Венера, 🟤 Сатурни, ☊ Раху, ☋ Кету
9. Отвечай на русском языке
10. В конце — кратко: БЛАГОПРИЯТНО / НЕЙТРАЛЬНО / ТРЕБУЕТ ВНИМАНИЯ

Не давай общих слов. Только конкретика джйотиш."""


# ── Вызов Gemini API ───────────────────────────────────────────────────
async def call_gemini(system_prompt: str, user_message: str, user_id: int) -> str:
    history = db.get_history(user_id, limit=6)

    # Gemini принимает историю в своём формате
    chat_history = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        chat_history.append({"role": role, "parts": [msg["content"]]})

    try:
        chat = gemini.start_chat(history=chat_history)
        full_message = f"{system_prompt}\n\n---\n\n{user_message}"
        # Системный промпт передаём только в первом сообщении или если история пуста
        if not chat_history:
            response = await chat.send_message_async(full_message)
        else:
            response = await chat.send_message_async(user_message)

        reply = response.text
        db.save_message(user_id, "user", user_message)
        db.save_message(user_id, "assistant", reply)
        return reply
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "❌ Ошибка API. Попробуй ещё раз."


# ── Хендлеры ──────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name or "Садхак"
    db.ensure_user(user_id)

    keyboard = [
        [InlineKeyboardButton("🌟 Транзиты сегодня", callback_data="transit_today")],
        [InlineKeyboardButton("🪐 Положение планет", callback_data="planet_positions")],
        [InlineKeyboardButton("📊 Персональный прогноз", callback_data="personal_forecast")],
        [InlineKeyboardButton("⚙️ Ввести натальные данные", callback_data="setup_natal")],
        [InlineKeyboardButton("❓ Задать вопрос астрологу", callback_data="ask_question")],
    ]

    await update.message.reply_text(
        f"🔱 *Намасте, {name}*\n\n"
        "Джйотиш-ассистент для анализа планетарных транзитов.\n\n"
        "Расчёты в сидерическом зодиаке, аянамша Лахири.\n\n"
        "Выбери раздел:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "transit_today":
        await show_transit_today(query)
    elif data == "planet_positions":
        await show_planet_positions(query)
    elif data == "personal_forecast":
        await show_personal_forecast(query, user_id)
    elif data == "setup_natal":
        await start_natal_setup(query, context)
    elif data == "ask_question":
        await query.edit_message_text(
            "✍️ Напиши свой вопрос.\n\n"
            "Например:\n"
            "• _Как Сатурн в овне влияет на карьеру?_\n"
            "• _Что означает Раху в близнецах?_\n"
            "• _Благоприятный период для бизнеса?_",
            parse_mode="Markdown"
        )
    elif data == "back_main":
        await back_to_main(query)


async def show_transit_today(query):
    await query.edit_message_text("⏳ Рассчитываю транзиты...")
    transits = get_current_transits()
    transit_context = get_transit_context()
    today = datetime.now().strftime("%d.%m.%Y")

    text = (
        f"🪐 *ТРАНЗИТЫ НА {today}*\n"
        f"_(сидерический зодиак, аянамша Лахири)_\n\n"
        f"{transits}"
    )
    if transit_context:
        text += f"\n\n📌 *Ключевые конфигурации:*\n{transit_context}"

    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard))


async def show_planet_positions(query):
    from jyotish import get_detailed_positions
    await query.edit_message_text("⏳ Загружаю эфемериды...")
    positions = get_detailed_positions()
    today = datetime.now().strftime("%d.%m.%Y")

    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]]
    await query.edit_message_text(
        f"🌌 *ПОЛОЖЕНИЕ ПЛАНЕТ — {today}*\n\n{positions}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_personal_forecast(query, user_id):
    user_data = db.get_user(user_id)

    if not user_data.get("birth_date"):
        keyboard = [
            [InlineKeyboardButton("⚙️ Ввести данные", callback_data="setup_natal")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
        ]
        await query.edit_message_text(
            "⚠️ Для персонального прогноза нужны натальные данные.\n\n"
            "Введи дату рождения — рассчитаю влияние транзитов на твои дома и текущую Дашу.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await query.edit_message_text("⏳ Анализирую транзиты относительно твоей карты...")

    system_prompt = build_system_prompt(user_data)
    prompt = (
        "Дай персональный прогноз на текущий период. "
        "Проанализируй: 1) влияние транзитов на натальные дома, "
        "2) текущую Дашу в контексте транзитов, "
        "3) конкретные рекомендации на ближайшие 2 недели: работа, финансы, здоровье, отношения."
    )

    response_text = await call_gemini(system_prompt, prompt, user_id)

    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]]
    await query.edit_message_text(
        f"🔮 *ПЕРСОНАЛЬНЫЙ ПРОГНОЗ*\n\n{response_text}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def back_to_main(query):
    keyboard = [
        [InlineKeyboardButton("🌟 Транзиты сегодня", callback_data="transit_today")],
        [InlineKeyboardButton("🪐 Положение планет", callback_data="planet_positions")],
        [InlineKeyboardButton("📊 Персональный прогноз", callback_data="personal_forecast")],
        [InlineKeyboardButton("⚙️ Ввести натальные данные", callback_data="setup_natal")],
        [InlineKeyboardButton("❓ Задать вопрос астрологу", callback_data="ask_question")],
    ]
    await query.edit_message_text(
        "🔱 *Джйотиш Ассистент*\n\nВыбери раздел:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ── Ввод натальных данных ──────────────────────────────────────────────
async def start_natal_setup(query, context):
    await query.edit_message_text(
        "📅 *Ввод натальных данных*\n\n"
        "Введи дату рождения:\n`ДД.ММ.ГГГГ`\n\nНапример: `15.03.1990`",
        parse_mode="Markdown"
    )
    return WAITING_BIRTH_DATE


async def receive_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
        context.user_data["birth_date"] = text
        await update.message.reply_text(
            "⏰ Время рождения `ЧЧ:ММ`\n\nЕсли не знаешь — напиши `0`",
            parse_mode="Markdown"
        )
        return WAITING_BIRTH_TIME
    except ValueError:
        await update.message.reply_text("❌ Формат: `ДД.ММ.ГГГГ`", parse_mode="Markdown")
        return WAITING_BIRTH_DATE


async def receive_birth_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "0":
        context.user_data["birth_time"] = None
    else:
        try:
            datetime.strptime(text, "%H:%M")
            context.user_data["birth_time"] = text
        except ValueError:
            await update.message.reply_text("❌ Формат: `ЧЧ:ММ` или `0`", parse_mode="Markdown")
            return WAITING_BIRTH_TIME

    await update.message.reply_text("📍 Место рождения:\n\nНапример: `Москва` или `Дели, Индия`")
    return WAITING_BIRTH_PLACE


async def receive_birth_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from jyotish import calculate_natal_basics
    user_id = update.effective_user.id
    place = update.message.text.strip()

    birth_date = context.user_data["birth_date"]
    birth_time = context.user_data.get("birth_time")

    await update.message.reply_text("⏳ Рассчитываю натальные позиции...")
    natal = calculate_natal_basics(birth_date, birth_time, place)

    db.save_user_natal(user_id, {"birth_date": birth_date, "birth_time": birth_time,
                                  "birth_place": place, **natal})

    await update.message.reply_text(
        f"✅ *Натальные данные сохранены*\n\n"
        f"📅 {birth_date}  ⏰ {birth_time or 'время не указано'}  📍 {place}\n\n"
        f"☀️ *Солнце:* {natal.get('sun_sign', '—')}\n"
        f"🌙 *Луна:* {natal.get('moon_sign', '—')} / {natal.get('moon_nakshatra', '—')}\n"
        f"🔱 *Лагна:* {natal.get('lagna', '—')}\n\n"
        f"⏳ *Маха-Даша:* {natal.get('mahadasha', '—')}\n"
        f"⏳ *Антар-Даша:* {natal.get('antardasha', '—')}\n\n"
        "Используй /start для прогноза.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено. /start — вернуться в меню.")
    return ConversationHandler.END


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    db.ensure_user(user_id)
    user_data = db.get_user(user_id)

    thinking_msg = await update.message.reply_text("⏳ Анализирую...")
    system_prompt = build_system_prompt(user_data)
    response = await call_gemini(system_prompt, user_text, user_id)

    await thinking_msg.delete()
    await update.message.reply_text(response, parse_mode="Markdown")


# ── Запуск ─────────────────────────────────────────────────────────────
def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Укажи TELEGRAM_BOT_TOKEN")
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("Укажи GEMINI_API_KEY")

    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_natal_setup, pattern="^setup_natal$")],
        states={
            WAITING_BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_birth_date)],
            WAITING_BIRTH_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_birth_time)],
            WAITING_BIRTH_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_birth_place)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🔱 Джйотиш бот запущен (Gemini)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
