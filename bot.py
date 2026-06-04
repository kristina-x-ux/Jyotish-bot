"""
╔══════════════════════════════════════╗
║   ДЖЙОТИШ БОТ — bot.py v4           ║
║   Groq + Whole Sign + Рассылка       ║
╚══════════════════════════════════════╝
"""

import logging, os
from datetime import datetime, time as dtime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler,
)
from database import Database
from jyotish import (
    get_current_transits, get_transit_context, get_detailed_positions,
    calculate_natal_basics, calculate_full_natal, build_natal_context,
    calculate_varshaphal, calculate_compatibility, calculate_muhurta,
    get_transit_events, build_transit_broadcast,
)

logging.basicConfig(format="%(asctime)s — %(name)s — %(levelname)s — %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

GROUP_ID = -1001310958976

WAITING_NAME          = 0
WAITING_BIRTH_DATE    = 1
WAITING_BIRTH_TIME    = 2
WAITING_BIRTH_PLACE   = 3
WAITING_SAVE_CONFIRM  = 4
WAITING_VARSHA_YEAR   = 10
WAITING_MUHURTA_DATE  = 21
WAITING_MUHURTA_DAYS  = 22
WAITING_COMPAT_C2_NAME  = 30
WAITING_COMPAT_C2_DATE  = 31
WAITING_COMPAT_C2_TIME  = 32
WAITING_COMPAT_C2_PLACE = 33

MUHURTA_LABELS = {
    "свадьба":"💒 Свадьба","роспись":"📝 Роспись","бизнес":"💼 Бизнес",
    "путешествие":"✈️ Путешествие","операция":"🏥 Операция",
    "красота":"💅 Красота","покупка":"🛒 Покупка","переезд":"🏠 Переезд","лечение":"💊 Лечение",
}

db = Database("/data/users.db")


# ── Reply Keyboard (закреплённое меню) ────────────────────────────────
def reply_keyboard():
    return ReplyKeyboardMarkup([
        ["🌟 Транзиты", "🪐 Планеты"],
        ["📊 Прогноз", "🔱 Натальная карта"],
        ["📅 Варшапхала", "💑 Совместимость"],
        ["🗓 Мухурта", "🗂 Мои карты"],
        ["➕ Добавить карту", "❓ Вопрос астрологу"],
    ], resize_keyboard=True, persistent=True)


def main_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌟 Транзиты сегодня",    callback_data="transit_today")],
        [InlineKeyboardButton("🪐 Положение планет",    callback_data="planet_positions")],
        [InlineKeyboardButton("📊 Персональный прогноз",callback_data="personal_forecast")],
        [InlineKeyboardButton("🔱 Натальная карта",     callback_data="natal_full")],
        [InlineKeyboardButton("📅 Варшапхала (год)",    callback_data="varshaphal")],
        [InlineKeyboardButton("💑 Совместимость",       callback_data="compatibility")],
        [InlineKeyboardButton("🗓 Мухурта",             callback_data="muhurta")],
        [InlineKeyboardButton("🗂 Мои карты",           callback_data="my_cards")],
        [InlineKeyboardButton("➕ Добавить карту",      callback_data="setup_natal")],
        [InlineKeyboardButton("❓ Задать вопрос",       callback_data="ask_question")],
    ])

def back_btn(target="back_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=target)]])


# ── Системный промпт ──────────────────────────────────────────────────
def build_system_prompt(card: dict) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    natal_ctx = build_natal_context(card) if card and card.get("birth_date") else ""
    transits  = get_current_transits()
    return f"""Ты — профессиональный джйотиш-астролог с глубокими знаниями ведической астрологии.
Используешь ТОЛЬКО систему Джйотиш. Западная астрология исключена.

СЕГОДНЯ: {today}

ТЕКУЩИЕ ТРАНЗИТЫ:
{transits}

{natal_ctx}

ПРАВИЛА:
1. Только терминология Джйотиш: Граха, Раши, Бхава, Накшатра, Даша, Дришти, Юти
2. Анализируй планеты в домах, аспекты, силу планет (уччха/нича/сваграха)
3. Соотноси транзиты с натальными домами и активной Дашей
4. Давай конкретные, развёрнутые интерпретации — не общие фразы
5. Указывай периоды влияния транзитов
6. Эмодзи: ☀️Солнце 🌙Луна 🔴Марс 🟡Меркурий 🟠Юпитер ⚪Венера 🟤Сатурн ☊Раху ☋Кету
7. Русский язык
8. В конце: БЛАГОПРИЯТНО / НЕЙТРАЛЬНО / ТРЕБУЕТ ВНИМАНИЯ
9. После итога — предложи 2-3 конкретных уточняющих вопроса

Если натальных данных нет — работай только с общими транзитами.
Никогда не используй западную астрологию."""


async def call_ai(system_prompt: str, user_message: str, user_id: int) -> str:
    history = db.get_history(user_id, limit=8)
    try:
        import aiohttp
        api_key = os.environ["GROQ_API_KEY"]
        messages = [{"role":"system","content":system_prompt}]
        for m in history:
            messages.append({"role":"user" if m["role"]=="user" else "assistant","content":m["content"]})
        messages.append({"role":"user","content":user_message})
        payload = {"model":"llama-3.3-70b-versatile","messages":messages,"max_tokens":2048,"temperature":0.7}
        headers = {"Authorization":f"Bearer {api_key}","Content-Type":"application/json"}
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.groq.com/openai/v1/chat/completions",
                              json=payload,headers=headers,
                              timeout=aiohttp.ClientTimeout(total=40)) as r:
                data = await r.json()
        reply = data["choices"][0]["message"]["content"]
        db.save_message(user_id,"user",user_message)
        db.save_message(user_id,"assistant",reply)
        return reply
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return "❌ Ошибка API. Попробуй ещё раз."


# ── Старт ─────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.ensure_user(update.effective_user.id)
    name = update.effective_user.first_name or "Садхак"
    await update.message.reply_text(
        f"🔱 *Намасте, {name}*\n\nДжйотиш-ассистент.\nРасчёты: сидерический зодиак, аянамша Лахири, Whole Sign Houses.\n\nВыбери раздел:",
        parse_mode="Markdown",
        reply_markup=reply_keyboard()
    )


# ── Reply keyboard handler ─────────────────────────────────────────────
async def text_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid  = update.effective_user.id
    db.ensure_user(uid)

    if text == "🌟 Транзиты":
        await send_transit_today(update.message)
    elif text == "🪐 Планеты":
        await send_planet_positions(update.message)
    elif text == "📊 Прогноз":
        await send_personal_forecast(update.message, uid)
    elif text == "🔱 Натальная карта":
        await send_natal_full(update.message, uid)
    elif text == "📅 Варшапхала":
        await update.message.reply_text(
            "📅 Введи год для расчёта Варшапхалы:\nНапример: `2026`",
            parse_mode="Markdown")
        return WAITING_VARSHA_YEAR
    elif text == "💑 Совместимость":
        await send_compatibility_menu(update.message, uid, context)
    elif text == "🗓 Мухурта":
        await send_muhurta_menu(update.message)
    elif text == "🗂 Мои карты":
        await send_my_cards(update.message, uid)
    elif text == "➕ Добавить карту":
        await update.message.reply_text(
            "👤 *Добавление карты*\n\nВведи имя и фамилию:",
            parse_mode="Markdown")
        return WAITING_NAME
    elif text == "❓ Вопрос астрологу":
        await update.message.reply_text(
            "✍️ Напиши свой вопрос по Джйотиш:")
    else:
        # Обычный вопрос астрологу
        card = db.get_active_card(uid) or {}
        thinking = await update.message.reply_text("⏳ Анализирую...")
        response = await call_ai(build_system_prompt(card), text, uid)
        await thinking.delete()
        await update.message.reply_text(response, parse_mode="Markdown")


# ── Вспомогательные функции отправки ──────────────────────────────────
async def send_transit_today(msg):
    await msg.reply_text("⏳ Рассчитываю транзиты...")
    t = get_current_transits()
    ctx = get_transit_context()
    today = datetime.now().strftime("%d.%m.%Y")
    text = f"🪐 *ТРАНЗИТЫ НА {today}*\n_(сидерический зодиак, аянамша Лахири)_\n\n{t}"
    if ctx: text += f"\n\n📌 *Конфигурации:*\n{ctx}"
    await msg.reply_text(text, parse_mode="Markdown")


async def send_planet_positions(msg):
    await msg.reply_text("⏳ Загружаю эфемериды...")
    p = get_detailed_positions()
    await msg.reply_text(f"🌌 *ПЛАНЕТЫ — {datetime.now().strftime('%d.%m.%Y')}*\n\n{p}", parse_mode="Markdown")


async def send_personal_forecast(msg, uid):
    card = db.get_active_card(uid)
    if not card or not card.get("birth_date"):
        await msg.reply_text("⚠️ Сначала добавь карту рождения (кнопка ➕ Добавить карту)")
        return
    await msg.reply_text("⏳ Анализирую транзиты по твоей карте...")
    prompt = "Дай развёрнутый персональный прогноз: транзиты по натальным домам, активная Даша, рекомендации на 2 недели по работе/финансам/здоровью/отношениям."
    r = await call_ai(build_system_prompt(card), prompt, uid)
    await msg.reply_text(f"🔮 *ПЕРСОНАЛЬНЫЙ ПРОГНОЗ*\n\n{r}", parse_mode="Markdown")


async def send_natal_full(msg, uid):
    card = db.get_active_card(uid)
    if not card or not card.get("birth_date"):
        await msg.reply_text("⚠️ Сначала добавь карту (кнопка ➕ Добавить карту)")
        return
    await msg.reply_text("⏳ Строю натальную карту...")
    result = calculate_full_natal(card["birth_date"], card.get("birth_time"), card.get("birth_place",""))
    prompt = f"Дай подробную интерпретацию натальной карты:\n{result}"
    ai = await call_ai(build_system_prompt(card), prompt, uid)
    if len(result) > 3800:
        await msg.reply_text(result[:3800], parse_mode="Markdown")
        await msg.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai}", parse_mode="Markdown")
    else:
        await msg.reply_text(f"{result}\n\n*── ИНТЕРПРЕТАЦИЯ ──*\n{ai}", parse_mode="Markdown")


async def send_my_cards(msg, uid):
    cards = db.get_all_cards(uid)
    active = db.get_active_card(uid)
    active_id = active.get("id") if active else None
    if not cards:
        await msg.reply_text("🗂 Карт пока нет.\nНажми ➕ Добавить карту")
        return
    keyboard = []
    for c in cards:
        mark = "✅ " if c["id"]==active_id else ""
        keyboard.append([InlineKeyboardButton(f"{mark}👤 {c['person_name']} ({c['birth_date']})", callback_data=f"load_card:{c['id']}")])
        keyboard.append([InlineKeyboardButton(f"🗑 Удалить {c['person_name']}", callback_data=f"delete_card:{c['id']}")])
    keyboard.append([InlineKeyboardButton("➕ Добавить карту", callback_data="setup_natal")])
    await msg.reply_text("🗂 *Мои карты*\n\nВыбери активную карту:", parse_mode="Markdown",
                         reply_markup=InlineKeyboardMarkup(keyboard))


async def send_compatibility_menu(msg, uid, context):
    cards = db.get_all_cards(uid)
    if not cards:
        await msg.reply_text("⚠️ Добавь хотя бы одну карту для расчёта совместимости.")
        return
    keyboard = [[InlineKeyboardButton(f"👤 {c['person_name']} ({c['birth_date']})", callback_data=f"compat_c1:{c['id']}")] for c in cards]
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    await msg.reply_text("💑 *Совместимость*\n\nВыбери первого человека:", parse_mode="Markdown",
                         reply_markup=InlineKeyboardMarkup(keyboard))


async def send_muhurta_menu(msg):
    items = list(MUHURTA_LABELS.items())
    keyboard = []
    for i in range(0,len(items),2):
        row = [InlineKeyboardButton(items[i][1], callback_data=f"muhurta_type:{items[i][0]}")]
        if i+1 < len(items):
            row.append(InlineKeyboardButton(items[i+1][1], callback_data=f"muhurta_type:{items[i+1][0]}"))
        keyboard.append(row)
    await msg.reply_text("🗓 *Мухурта*\nВыбери тип события:", parse_mode="Markdown",
                         reply_markup=InlineKeyboardMarkup(keyboard))


# ── Inline button handler ──────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid  = q.from_user.id
    data = q.data

    if data == "transit_today":
        await q.edit_message_text("⏳ Рассчитываю...")
        t = get_current_transits(); ctx = get_transit_context()
        today = datetime.now().strftime("%d.%m.%Y")
        text = f"🪐 *ТРАНЗИТЫ НА {today}*\n\n{t}"
        if ctx: text += f"\n\n📌 {ctx}"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    elif data == "planet_positions":
        await q.edit_message_text("⏳ Загружаю...")
        p = get_detailed_positions()
        await q.edit_message_text(f"🌌 *ПЛАНЕТЫ*\n\n{p}", parse_mode="Markdown", reply_markup=back_btn())

    elif data == "personal_forecast":
        card = db.get_active_card(uid)
        if not card or not card.get("birth_date"):
            await q.edit_message_text("⚠️ Добавь карту рождения.", reply_markup=back_btn())
            return
        await q.edit_message_text("⏳ Анализирую...")
        r = await call_ai(build_system_prompt(card),
            "Дай развёрнутый персональный прогноз по натальным домам и активной Даше.", uid)
        await q.edit_message_text(f"🔮 *ПРОГНОЗ*\n\n{r}", parse_mode="Markdown", reply_markup=back_btn())

    elif data == "natal_full":
        card = db.get_active_card(uid)
        if not card or not card.get("birth_date"):
            await q.edit_message_text("⚠️ Добавь карту.", reply_markup=back_btn()); return
        await q.edit_message_text("⏳ Строю карту...")
        result = calculate_full_natal(card["birth_date"],card.get("birth_time"),card.get("birth_place",""))
        ai = await call_ai(build_system_prompt(card), f"Интерпретируй натальную карту:\n{result}", uid)
        await q.edit_message_text(result[:3800] if len(result)>3800 else result, parse_mode="Markdown", reply_markup=back_btn())
        if len(result) > 3800 or ai:
            await q.message.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai}", parse_mode="Markdown")

    elif data == "varshaphal":
        card = db.get_active_card(uid)
        if not card or not card.get("birth_date"):
            await q.edit_message_text("⚠️ Добавь карту.", reply_markup=back_btn()); return
        await q.edit_message_text(f"📅 Введи год (например `{datetime.now().year}`):", parse_mode="Markdown")
        return WAITING_VARSHA_YEAR

    elif data == "compatibility":
        cards = db.get_all_cards(uid)
        if not cards:
            await q.edit_message_text("⚠️ Добавь карту.", reply_markup=back_btn()); return
        keyboard = [[InlineKeyboardButton(f"👤 {c['person_name']}", callback_data=f"compat_c1:{c['id']}")] for c in cards]
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
        await q.edit_message_text("💑 Выбери первого:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "muhurta":
        items = list(MUHURTA_LABELS.items())
        keyboard = []
        for i in range(0,len(items),2):
            row=[InlineKeyboardButton(items[i][1],callback_data=f"muhurta_type:{items[i][0]}")]
            if i+1<len(items): row.append(InlineKeyboardButton(items[i+1][1],callback_data=f"muhurta_type:{items[i+1][0]}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("◀️ Назад",callback_data="back_main")])
        await q.edit_message_text("🗓 *Мухурта*\nВыбери тип:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("muhurta_type:"):
        context.user_data["muhurta_type"] = data.split(":")[1]
        await q.edit_message_text("📅 С какой даты искать? `ДД.ММ.ГГГГ`", parse_mode="Markdown")
        return WAITING_MUHURTA_DATE

    elif data == "my_cards":
        await q.message.reply_text("🗂 Карты:")
        await send_my_cards(q.message, uid)

    elif data == "setup_natal":
        await q.edit_message_text("👤 Введи имя и фамилию:")
        return WAITING_NAME

    elif data.startswith("load_card:"):
        cid = int(data.split(":")[1])
        db.set_active_card(uid, cid)
        c = db.get_card_by_id(cid)
        await q.edit_message_text(
            f"✅ Активна карта: *{c['person_name']}*\n📅 {c['birth_date']}  📍 {c.get('birth_place','—')}",
            parse_mode="Markdown", reply_markup=back_btn("my_cards"))

    elif data.startswith("delete_card:"):
        db.delete_card(int(data.split(":")[1]), uid)
        await send_my_cards(q.message, uid)

    elif data.startswith("compat_c1:"):
        context.user_data["compat_c1"] = int(data.split(":")[1])
        cards = db.get_all_cards(uid)
        c1id = context.user_data["compat_c1"]
        keyboard = [[InlineKeyboardButton(f"👤 {c['person_name']}", callback_data=f"compat_c2:{c['id']}")] for c in cards if c["id"]!=c1id]
        keyboard.append([InlineKeyboardButton("➕ Ввести данные нового человека", callback_data="compat_new")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="compatibility")])
        await q.edit_message_text("💑 Выбери второго:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("compat_c2:"):
        c1 = db.get_card_by_id(context.user_data["compat_c1"])
        c2 = db.get_card_by_id(int(data.split(":")[1]))
        await q.edit_message_text("⏳ Рассчитываю совместимость...")
        result = calculate_compatibility(c1,c2)
        ai = await call_ai(build_system_prompt({}), f"Интерпретируй Кута-анализ:\n{result}", uid)
        await q.edit_message_text(result, parse_mode="Markdown", reply_markup=back_btn())
        await q.message.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai}", parse_mode="Markdown")

    elif data == "compat_new":
        await q.edit_message_text("👤 Введи имя второго человека:")
        return WAITING_COMPAT_C2_NAME

    elif data == "save_card_yes":
        card_data = context.user_data.get("pending_card",{})
        uid2 = q.from_user.id
        card_id = db.save_card(uid2, card_data)
        db.set_active_card(uid2, card_id)
        await q.edit_message_text(
            f"✅ *Карта сохранена в 'Мои карты'*\n\n"
            f"👤 {card_data.get('person_name')}\n"
            f"📅 {card_data.get('birth_date')}  ⏰ {card_data.get('birth_time') or 'не указано'}  📍 {card_data.get('birth_place')}\n\n"
            f"☀️ Солнце: {card_data.get('sun_sign','—')}\n"
            f"🌙 Луна: {card_data.get('moon_sign','—')} / {card_data.get('moon_nakshatra','—')}\n"
            f"🔱 Лагна: {card_data.get('lagna','—')}\n"
            f"⏳ Маха-Даша: {card_data.get('mahadasha','—')}\n"
            f"⏳ Антар-Даша: {card_data.get('antardasha','—')}",
            parse_mode="Markdown"
        )
        context.user_data.pop("pending_card", None)
        return ConversationHandler.END

    elif data == "save_card_no":
        await q.edit_message_text("Карта не сохранена. Используй ➕ Добавить карту чтобы сохранить.")
        context.user_data.pop("pending_card", None)
        return ConversationHandler.END

    elif data == "post_broadcast":
        await post_to_group(context.application, manual=True)
        await q.answer("Отправлено в группу ✅", show_alert=True)

    elif data == "back_main":
        await q.edit_message_text("🔱 *Джйотиш Ассистент*\n\nВыбери раздел:",
                                   parse_mode="Markdown", reply_markup=main_inline())


# ── Диалог ввода данных ────────────────────────────────────────────────
async def start_natal_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("👤 Введи имя и фамилию:")
    else:
        await update.message.reply_text("👤 *Добавление карты*\n\nВведи имя и фамилию:", parse_mode="Markdown")
    return WAITING_NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["person_name"] = update.message.text.strip()
    await update.message.reply_text("📅 Дата рождения `ДД.ММ.ГГГГ`", parse_mode="Markdown")
    return WAITING_COMPAT_C2_DATE

async def receive_compat_c2_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text,"%d.%m.%Y")
        context.user_data["c2_date"] = text
        await update.message.reply_text("⏰ Время рождения `ЧЧ:ММ` или `0`", parse_mode="Markdown")
        return WAITING_COMPAT_C2_TIME
    except ValueError:
        await update.message.reply_text("❌ Формат: `ДД.ММ.ГГГГ`", parse_mode="Markdown")
        return WAITING_COMPAT_C2_DATE

async def receive_compat_c2_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["c2_time"] = None if text=="0" else text
    await update.message.reply_text("📍 Место рождения (город, страна):")
    return WAITING_COMPAT_C2_PLACE

async def receive_compat_c2_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    c2 = {
        "person_name": context.user_data.get("c2_name","Человек 2"),
        "birth_date":  context.user_data["c2_date"],
        "birth_time":  context.user_data.get("c2_time"),
        "birth_place": update.message.text.strip(),
    }
    c1_id = context.user_data.get("compat_c1")
    c1 = db.get_card_by_id(c1_id) if c1_id else db.get_active_card(uid)
    await update.message.reply_text("⏳ Рассчитываю совместимость...")
    result = calculate_compatibility(c1,c2)
    ai = await call_ai(build_system_prompt({}), f"Интерпретируй Кута-анализ:\n{result}", uid)
    await update.message.reply_text(result, parse_mode="Markdown")
    await update.message.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai}", parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено. Используй меню для навигации.")
    return ConversationHandler.END


# ── Рассылка в группу ─────────────────────────────────────────────────
async def post_to_group(app, manual: bool = False):
    events = get_transit_events()
    if not events and not manual:
        return
    if not events and manual:
        # При ручной отправке — текущие транзиты
        t = get_current_transits()
        ctx = get_transit_context()
        today = datetime.now().strftime("%d.%m.%Y")
        text = f"🪐 *ТРАНЗИТЫ НА {today}*\n\n{t}"
        if ctx: text += f"\n\n📌 *Конфигурации:*\n{ctx}"
        try:
            await app.bot.send_message(GROUP_ID, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка отправки в группу: {e}")
        return
    for event in events:
        text = build_transit_broadcast(event)
        try:
            await app.bot.send_message(GROUP_ID, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка отправки в группу: {e}")

async def scheduled_broadcast(context: ContextTypes.DEFAULT_TYPE):
    await post_to_group(context.application)

async def cmd_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /post для ручной отправки."""
    await post_to_group(context.application, manual=True)
    await update.message.reply_text("✅ Прогноз отправлен в группу")


# ── Запуск ────────────────────────────────────────────────────────────
def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token: raise ValueError("Укажи TELEGRAM_BOT_TOKEN")
    if not os.environ.get("GROQ_API_KEY"): raise ValueError("Укажи GROQ_API_KEY")

    app = Application.builder().token(token).build()

    # Расписание 12:00 МСК через APScheduler
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    async def broadcast_job():
        await post_to_group(app)

    scheduler.add_job(broadcast_job, "cron", hour=12, minute=0)
    scheduler.start()


    natal_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_natal_setup, pattern="^setup_natal$"),
            CommandHandler("add", start_natal_setup),
        ],
        states={
            WAITING_NAME:        [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            WAITING_BIRTH_DATE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_birth_date)],
            WAITING_BIRTH_TIME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_birth_time)],
            WAITING_BIRTH_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_birth_place)],
            WAITING_SAVE_CONFIRM:[CallbackQueryHandler(button_handler, pattern="^save_card_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    varsha_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^varshaphal$")],
        states={WAITING_VARSHA_YEAR:[MessageHandler(filters.TEXT & ~filters.COMMAND, receive_varsha_year)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    muhurta_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^muhurta_type:")],
        states={
            WAITING_MUHURTA_DATE:[MessageHandler(filters.TEXT & ~filters.COMMAND, receive_muhurta_date)],
            WAITING_MUHURTA_DAYS:[MessageHandler(filters.TEXT & ~filters.COMMAND, receive_muhurta_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    compat_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^compat_new$")],
        states={
            WAITING_COMPAT_C2_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_compat_c2_name)],
            WAITING_COMPAT_C2_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_compat_c2_date)],
            WAITING_COMPAT_C2_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_compat_c2_time)],
            WAITING_COMPAT_C2_PLACE:[MessageHandler(filters.TEXT & ~filters.COMMAND, receive_compat_c2_place)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post",  cmd_post))
    app.add_handler(natal_conv)
    app.add_handler(varsha_conv)
    app.add_handler(muhurta_conv)
    app.add_handler(compat_conv)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_menu_handler
    ))

    logger.info("🔱 Джйотиш бот v4 запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
