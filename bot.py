"""
╔══════════════════════════════════════╗
║   ДЖЙОТИШ ТРАНЗИТ БОТ — bot.py v3   ║
║   Powered by Groq (FREE)             ║
╚══════════════════════════════════════╝
"""

import logging
import os
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from database import Database
from jyotish import (
    get_current_transits, get_transit_context, get_detailed_positions,
    calculate_natal_basics, calculate_full_natal,
    calculate_varshaphal, calculate_compatibility, calculate_muhurta
)

logging.basicConfig(format="%(asctime)s — %(name)s — %(levelname)s — %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния диалогов
WAITING_NAME = 0
WAITING_BIRTH_DATE = 1
WAITING_BIRTH_TIME = 2
WAITING_BIRTH_PLACE = 3
WAITING_VARSHA_YEAR = 10
WAITING_MUHURTA_TYPE = 20
WAITING_MUHURTA_DATE = 21
WAITING_MUHURTA_DAYS = 22
WAITING_COMPAT_CARD2_NAME = 30
WAITING_COMPAT_CARD2_DATE = 31
WAITING_COMPAT_CARD2_TIME = 32
WAITING_COMPAT_CARD2_PLACE = 33

db = Database("/data/users.db")

MUHURTA_TYPES = [
    "свадьба", "роспись", "бизнес", "путешествие",
    "операция", "красота", "покупка", "переезд", "лечение"
]
MUHURTA_LABELS = {
    "свадьба":"💒 Свадьба", "роспись":"📝 Роспись",
    "бизнес":"💼 Бизнес", "путешествие":"✈️ Путешествие",
    "операция":"🏥 Операция", "красота":"💅 Операция красоты",
    "покупка":"🛒 Крупная покупка", "переезд":"🏠 Переезд",
    "лечение":"💊 Лечение"
}


def build_system_prompt(user_data: dict) -> str:
    from jyotish import get_current_transits
    transits = get_current_transits()
    today = datetime.now().strftime("%d.%m.%Y")
    natal_info = ""
    if user_data and user_data.get("birth_date"):
        natal_info = f"""
НАТАЛЬНЫЕ ДАННЫЕ:
• Имя: {user_data.get('person_name', '—')}
• Дата: {user_data['birth_date']}
• Время: {user_data.get('birth_time', 'не указано')}
• Место: {user_data.get('birth_place', 'не указано')}
• Лагна: {user_data.get('lagna', '—')}
• Луна накшатра: {user_data.get('moon_nakshatra', '—')}
• Маха-Даша: {user_data.get('mahadasha', '—')}
• Антар-Даша: {user_data.get('antardasha', '—')}
"""
    return f"""Ты — опытный джйотиш-астролог. Используешь ТОЛЬКО систему Джйотиш (ведическая астрология). Западная астрология не используется никогда.

СЕГОДНЯ: {today}
ТРАНЗИТЫ: {transits}
{natal_info}

ПРАВИЛА:
1. Только терминология Джйотиш: Граха, Раши, Бхава, Накшатры, Даша
2. Обширные детальные интерпретации
3. Практичные рекомендации — что делать, чего избегать
4. Конкретные периоды влияния транзитов
5. Аспекты (дришти) и соединения (юти)
6. Сила планет: уччха, нича, сваграха
7. Если есть натальные данные — соотноси с натальными домами и Дашей
8. Эмодзи: ☀️ Солнце 🌙 Луна 🔴 Марс 🟡 Меркурий 🟠 Юпитер ⚪ Венера 🟤 Сатурн ☊ Раху ☋ Кету
9. Русский язык
10. В конце: БЛАГОПРИЯТНО / НЕЙТРАЛЬНО / ТРЕБУЕТ ВНИМАНИЯ
11. После итога — предложи 2-3 уточняющих вопроса для углубления анализа

Никогда не используй западную астрологию. Только Джйотиш."""


async def call_ai(system_prompt: str, user_message: str, user_id: int) -> str:
    history = db.get_history(user_id, limit=6)
    chat_history = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        chat_history.append({"role": role, "parts": [msg["content"]]})
    try:
        import aiohttp
        api_key = os.environ["GROQ_API_KEY"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["parts"][0]})
        messages.append({"role": "user", "content": user_message})
        payload = {"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 2048, "temperature": 0.7}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=40)) as resp:
                data = await resp.json()
        reply = data["choices"][0]["message"]["content"]
        db.save_message(user_id, "user", user_message)
        db.save_message(user_id, "assistant", reply)
        return reply
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return "❌ Ошибка API. Попробуй ещё раз."


def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌟 Транзиты сегодня", callback_data="transit_today")],
        [InlineKeyboardButton("🪐 Положение планет", callback_data="planet_positions")],
        [InlineKeyboardButton("📊 Персональный прогноз", callback_data="personal_forecast")],
        [InlineKeyboardButton("🔱 Натальная карта", callback_data="natal_full")],
        [InlineKeyboardButton("📅 Варшапхала (год)", callback_data="varshaphal")],
        [InlineKeyboardButton("💑 Совместимость", callback_data="compatibility")],
        [InlineKeyboardButton("🗓 Мухурта", callback_data="muhurta")],
        [InlineKeyboardButton("🗂 Мои карты", callback_data="my_cards")],
        [InlineKeyboardButton("➕ Ввести данные рождения", callback_data="setup_natal")],
        [InlineKeyboardButton("❓ Задать вопрос астрологу", callback_data="ask_question")],
    ])


def back_btn(target="back_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=target)]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name or "Садхак"
    db.ensure_user(user_id)
    await update.message.reply_text(
        f"🔱 *Намасте, {name}*\n\nДжйотиш-ассистент для анализа планетарных транзитов.\nРасчёты в сидерическом зодиаке, аянамша Лахири.\n\nВыбери раздел:",
        parse_mode="Markdown", reply_markup=main_keyboard()
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
    elif data == "natal_full":
        await show_natal_full(query, user_id)
    elif data == "varshaphal":
        await ask_varsha_year(query, context)
    elif data == "compatibility":
        await show_compatibility_menu(query, user_id, context)
    elif data == "muhurta":
        await show_muhurta_menu(query, context)
    elif data.startswith("muhurta_type:"):
        context.user_data["muhurta_type"] = data.split(":")[1]
        await query.edit_message_text(
            "📅 С какой даты искать?\nФормат: `ДД.ММ.ГГГГ`\n\nНапример: `01.06.2026`",
            parse_mode="Markdown", reply_markup=back_btn("muhurta")
        )
        return WAITING_MUHURTA_DATE
    elif data == "my_cards":
        await show_my_cards(query, user_id)
    elif data.startswith("load_card:"):
        await load_card(query, user_id, int(data.split(":")[1]))
    elif data.startswith("delete_card:"):
        await delete_card(query, user_id, int(data.split(":")[1]))
    elif data.startswith("compat_card1:"):
        context.user_data["compat_card1_id"] = int(data.split(":")[1])
        await show_compat_card2_select(query, user_id, context)
    elif data.startswith("compat_card2:"):
        card1_id = context.user_data.get("compat_card1_id")
        card2_id = int(data.split(":")[1])
        await run_compatibility(query, user_id, card1_id, card2_id)
    elif data == "compat_new_person":
        await query.edit_message_text(
            "👤 Введи имя второго человека:",
            reply_markup=back_btn("compatibility")
        )
        return WAITING_COMPAT_CARD2_NAME
    elif data == "ask_question":
        await query.edit_message_text(
            "✍️ Напиши свой вопрос.\n\nНапример:\n• _Как Сатурн в Водолее влияет на карьеру?_\n• _Благоприятный период для бизнеса?_",
            parse_mode="Markdown", reply_markup=back_btn()
        )
    elif data == "back_main":
        await query.edit_message_text("🔱 *Джйотиш Ассистент*\n\nВыбери раздел:", parse_mode="Markdown", reply_markup=main_keyboard())


async def show_transit_today(query):
    await query.edit_message_text("⏳ Рассчитываю транзиты...")
    transits = get_current_transits()
    context_str = get_transit_context()
    today = datetime.now().strftime("%d.%m.%Y")
    text = f"🪐 *ТРАНЗИТЫ НА {today}*\n_(сидерический зодиак, аянамша Лахири)_\n\n{transits}"
    if context_str:
        text += f"\n\n📌 *Ключевые конфигурации:*\n{context_str}"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())


async def show_planet_positions(query):
    await query.edit_message_text("⏳ Загружаю эфемериды...")
    positions = get_detailed_positions()
    today = datetime.now().strftime("%d.%m.%Y")
    await query.edit_message_text(f"🌌 *ПОЛОЖЕНИЕ ПЛАНЕТ — {today}*\n\n{positions}", parse_mode="Markdown", reply_markup=back_btn())


async def show_personal_forecast(query, user_id):
    user_data = db.get_active_card(user_id)
    if not user_data or not user_data.get("birth_date"):
        await query.edit_message_text(
            "⚠️ Для персонального прогноза нужны натальные данные.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ввести данные рождения", callback_data="setup_natal")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
            ])
        )
        return
    await query.edit_message_text("⏳ Анализирую транзиты относительно твоей карты...")
    system_prompt = build_system_prompt(user_data)
    prompt = "Дай персональный прогноз на текущий период: влияние транзитов на натальные дома, текущую Дашу, рекомендации на ближайшие 2 недели по работе, финансам, здоровью, отношениям."
    response = await call_ai(system_prompt, prompt, user_id)
    await query.edit_message_text(f"🔮 *ПЕРСОНАЛЬНЫЙ ПРОГНОЗ*\n\n{response}", parse_mode="Markdown", reply_markup=back_btn())


async def show_natal_full(query, user_id):
    user_data = db.get_active_card(user_id)
    if not user_data or not user_data.get("birth_date"):
        await query.edit_message_text(
            "⚠️ Сначала введи данные рождения.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ввести данные", callback_data="setup_natal")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
            ])
        )
        return
    await query.edit_message_text("⏳ Рассчитываю натальную карту...")
    result = calculate_full_natal(user_data["birth_date"], user_data.get("birth_time"), user_data.get("birth_place",""))
    system_prompt = build_system_prompt(user_data)
    ai_response = await call_ai(system_prompt, f"Дай подробную интерпретацию этой натальной карты:\n{result}", user_id)
    full_text = f"{result}\n\n*── ИНТЕРПРЕТАЦИЯ ──*\n{ai_response}"
    # Telegram лимит 4096 символов
    if len(full_text) > 4000:
        await query.edit_message_text(result[:4000], parse_mode="Markdown", reply_markup=back_btn())
        await query.message.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai_response}", parse_mode="Markdown")
    else:
        await query.edit_message_text(full_text, parse_mode="Markdown", reply_markup=back_btn())


async def ask_varsha_year(query, context):
    current_year = datetime.now().year
    user_data = db.get_active_card(query.from_user.id)
    if not user_data or not user_data.get("birth_date"):
        await query.edit_message_text(
            "⚠️ Сначала введи данные рождения.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ввести данные", callback_data="setup_natal")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
            ])
        )
        return
    await query.edit_message_text(
        f"📅 *Варшапхала — годовой гороскоп*\n\nВведи год для расчёта:\nНапример: `{current_year}` или `{current_year+1}`",
        parse_mode="Markdown", reply_markup=back_btn()
    )
    return WAITING_VARSHA_YEAR


async def show_muhurta_menu(query, context):
    keyboard = []
    items = list(MUHURTA_LABELS.items())
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(items[i][1], callback_data=f"muhurta_type:{items[i][0]}")]
        if i+1 < len(items):
            row.append(InlineKeyboardButton(items[i+1][1], callback_data=f"muhurta_type:{items[i+1][0]}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    await query.edit_message_text("🗓 *МУХУРТА*\nВыбери тип события:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_compatibility_menu(query, user_id, context):
    cards = db.get_all_cards(user_id)
    if len(cards) < 1:
        await query.edit_message_text(
            "⚠️ Для расчёта совместимости нужна хотя бы одна карта.\nДобавь данные рождения.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Добавить карту", callback_data="setup_natal")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
            ])
        )
        return
    keyboard = []
    for card in cards:
        keyboard.append([InlineKeyboardButton(f"👤 {card['person_name']} ({card['birth_date']})", callback_data=f"compat_card1:{card['id']}")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    await query.edit_message_text("💑 *СОВМЕСТИМОСТЬ*\n\nВыбери первого человека:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_compat_card2_select(query, user_id, context):
    cards = db.get_all_cards(user_id)
    card1_id = context.user_data.get("compat_card1_id")
    keyboard = []
    for card in cards:
        if card["id"] != card1_id:
            keyboard.append([InlineKeyboardButton(f"👤 {card['person_name']} ({card['birth_date']})", callback_data=f"compat_card2:{card['id']}")])
    keyboard.append([InlineKeyboardButton("➕ Ввести данные нового человека", callback_data="compat_new_person")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="compatibility")])
    await query.edit_message_text("💑 Выбери второго человека:", reply_markup=InlineKeyboardMarkup(keyboard))


async def run_compatibility(query, user_id, card1_id, card2_id):
    await query.edit_message_text("⏳ Рассчитываю совместимость...")
    card1 = db.get_card_by_id(card1_id)
    card2 = db.get_card_by_id(card2_id)
    result = calculate_compatibility(card1, card2)
    system_prompt = build_system_prompt({})
    ai_response = await call_ai(system_prompt, f"Дай интерпретацию этого Кута-анализа совместимости:\n{result}", user_id)
    full_text = f"{result}\n\n*── ИНТЕРПРЕТАЦИЯ ──*\n{ai_response}"
    if len(full_text) > 4000:
        await query.edit_message_text(result, parse_mode="Markdown", reply_markup=back_btn())
        await query.message.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai_response}", parse_mode="Markdown")
    else:
        await query.edit_message_text(full_text, parse_mode="Markdown", reply_markup=back_btn())


async def show_my_cards(query, user_id):
    cards = db.get_all_cards(user_id)
    if not cards:
        await query.edit_message_text(
            "🗂 *Мои карты*\n\nПока нет сохранённых карт.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Добавить карту", callback_data="setup_natal")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
            ])
        )
        return
    keyboard = []
    for card in cards:
        keyboard.append([InlineKeyboardButton(f"👤 {card['person_name']} — {card['birth_date']}", callback_data=f"load_card:{card['id']}")])
        keyboard.append([InlineKeyboardButton(f"🗑 Удалить {card['person_name']}", callback_data=f"delete_card:{card['id']}")])
    keyboard.append([InlineKeyboardButton("➕ Добавить карту", callback_data="setup_natal")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    await query.edit_message_text("🗂 *Мои карты*\n\nВыбери карту:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def load_card(query, user_id, card_id):
    db.set_active_card(user_id, card_id)
    card = db.get_card_by_id(card_id)
    await query.edit_message_text(
        f"✅ Активна карта: *{card['person_name']}*\n📅 {card['birth_date']}  📍 {card.get('birth_place','—')}",
        parse_mode="Markdown", reply_markup=back_btn("my_cards")
    )


async def delete_card(query, user_id, card_id):
    db.delete_card(card_id, user_id)
    await show_my_cards(query, user_id)


# ── Диалоги ввода данных ──────────────────────────────────────────────
async def start_natal_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        send = update.callback_query.edit_message_text
    else:
        send = update.message.reply_text
    await send("👤 *Ввод данных рождения*\n\nВведи имя и фамилию:", parse_mode="Markdown")
    return WAITING_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["person_name"] = update.message.text.strip()
    await update.message.reply_text("📅 Дата рождения `ДД.ММ.ГГГГ`\n\nНапример: `15.03.1990`", parse_mode="Markdown")
    return WAITING_BIRTH_DATE


async def receive_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
        context.user_data["birth_date"] = text
        await update.message.reply_text("⏰ Время рождения `ЧЧ:ММ`\nЕсли не знаешь — напиши `0`", parse_mode="Markdown")
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
    user_id = update.effective_user.id
    place = update.message.text.strip()
    birth_date = context.user_data["birth_date"]
    birth_time = context.user_data.get("birth_time")
    person_name = context.user_data.get("person_name", "Без имени")

    await update.message.reply_text("⏳ Рассчитываю натальные позиции...")
    natal = calculate_natal_basics(birth_date, birth_time, place)
    card_data = {"person_name": person_name, "birth_date": birth_date, "birth_time": birth_time, "birth_place": place, **natal}
    card_id = db.save_card(user_id, card_data)
    db.set_active_card(user_id, card_id)

    await update.message.reply_text(
        f"✅ *Карта сохранена*\n\n👤 {person_name}\n📅 {birth_date}  ⏰ {birth_time or 'не указано'}  📍 {place}\n\n"
        f"☀️ *Солнце:* {natal.get('sun_sign','—')}\n🌙 *Луна:* {natal.get('moon_sign','—')} / {natal.get('moon_nakshatra','—')}\n\n"
        f"⏳ *Маха-Даша:* {natal.get('mahadasha','—')}\n⏳ *Антар-Даша:* {natal.get('antardasha','—')}\n\nИспользуй /start для меню.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# Варшапхала — ввод года
async def receive_varsha_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        year = int(text)
        if year < 1900 or year > 2100:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи корректный год, например `2026`", parse_mode="Markdown")
        return WAITING_VARSHA_YEAR

    user_id = update.effective_user.id
    user_data = db.get_active_card(user_id)
    await update.message.reply_text("⏳ Рассчитываю Варшапхалу...")
    result = calculate_varshaphal(user_data["birth_date"], user_data.get("birth_time"), user_data.get("birth_place",""), year)
    system_prompt = build_system_prompt(user_data)
    ai_response = await call_ai(system_prompt, f"Дай интерпретацию этой Варшапхалы:\n{result}", user_id)

    await update.message.reply_text(result, parse_mode="Markdown")
    await update.message.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai_response}", parse_mode="Markdown")
    return ConversationHandler.END


# Мухурта — ввод даты
async def receive_muhurta_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
        context.user_data["muhurta_start"] = text
        await update.message.reply_text("📆 На сколько дней вперёд искать? (от 7 до 90)\n\nНапример: `30`")
        return WAITING_MUHURTA_DAYS
    except ValueError:
        await update.message.reply_text("❌ Формат: `ДД.ММ.ГГГГ`", parse_mode="Markdown")
        return WAITING_MUHURTA_DATE


async def receive_muhurta_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        days = int(text)
        if days < 1 or days > 90:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи число от 7 до 90")
        return WAITING_MUHURTA_DAYS

    event_type = context.user_data.get("muhurta_type", "бизнес")
    start_date = context.user_data.get("muhurta_start")
    await update.message.reply_text("⏳ Ищу благоприятные даты...")
    result = calculate_muhurta(event_type, start_date, days)
    await update.message.reply_text(result, parse_mode="Markdown")
    return ConversationHandler.END


# Совместимость — ввод данных второго человека
async def receive_compat_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["compat2_name"] = update.message.text.strip()
    await update.message.reply_text("📅 Дата рождения `ДД.ММ.ГГГГ`", parse_mode="Markdown")
    return WAITING_COMPAT_CARD2_DATE


async def receive_compat_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
        context.user_data["compat2_date"] = text
        await update.message.reply_text("⏰ Время рождения `ЧЧ:ММ` или `0`", parse_mode="Markdown")
        return WAITING_COMPAT_CARD2_TIME
    except ValueError:
        await update.message.reply_text("❌ Формат: `ДД.ММ.ГГГГ`", parse_mode="Markdown")
        return WAITING_COMPAT_CARD2_DATE


async def receive_compat_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["compat2_time"] = None if text == "0" else text
    await update.message.reply_text("📍 Место рождения:")
    return WAITING_COMPAT_CARD2_PLACE


async def receive_compat_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    place = update.message.text.strip()
    card2 = {
        "person_name": context.user_data.get("compat2_name","Человек 2"),
        "birth_date": context.user_data["compat2_date"],
        "birth_time": context.user_data.get("compat2_time"),
        "birth_place": place,
    }
    card1_id = context.user_data.get("compat_card1_id")
    card1 = db.get_card_by_id(card1_id) if card1_id else db.get_active_card(user_id)

    await update.message.reply_text("⏳ Рассчитываю совместимость...")
    result = calculate_compatibility(card1, card2)
    system_prompt = build_system_prompt({})
    ai_response = await call_ai(system_prompt, f"Дай интерпретацию Кута-анализа:\n{result}", user_id)
    await update.message.reply_text(result, parse_mode="Markdown")
    await update.message.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai_response}", parse_mode="Markdown")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено. /start — вернуться в меню.")
    return ConversationHandler.END


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    db.ensure_user(user_id)
    user_data = db.get_active_card(user_id) or {}
    thinking = await update.message.reply_text("⏳ Анализирую...")
    system_prompt = build_system_prompt(user_data)
    response = await call_ai(system_prompt, user_text, user_id)
    await thinking.delete()
    await update.message.reply_text(response, parse_mode="Markdown")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Укажи TELEGRAM_BOT_TOKEN")
    if not os.environ.get("GROQ_API_KEY"):
        raise ValueError("Укажи GROQ_API_KEY")

    app = Application.builder().token(token).build()

    natal_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_natal_setup, pattern="^setup_natal$"),
            CommandHandler("add", start_natal_setup),
        ],
        states={
            WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            WAITING_BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_birth_date)],
            WAITING_BIRTH_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_birth_time)],
            WAITING_BIRTH_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_birth_place)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    varsha_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_varsha_year, pattern="^varshaphal$")],
        states={WAITING_VARSHA_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_varsha_year)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    muhurta_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_muhurta_menu, pattern="^muhurta$")],
        states={
            WAITING_MUHURTA_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_muhurta_date)],
            WAITING_MUHURTA_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_muhurta_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    compat_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_compatibility_menu, pattern="^compatibility$")],
        states={
            WAITING_COMPAT_CARD2_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_compat_name)],
            WAITING_COMPAT_CARD2_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_compat_date)],
            WAITING_COMPAT_CARD2_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_compat_time)],
            WAITING_COMPAT_CARD2_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_compat_place)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(natal_conv)
    app.add_handler(varsha_conv)
    app.add_handler(muhurta_conv)
    app.add_handler(compat_conv)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🔱 Джйотиш бот v3 запущен (Groq)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
