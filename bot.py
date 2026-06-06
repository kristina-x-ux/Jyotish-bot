"""
╔══════════════════════════════════════╗
║   ДЖЙОТИШ БОТ — bot.py v5           ║
║   Все диалоги через inline           ║
╚══════════════════════════════════════╝
"""

import logging, os
from datetime import datetime, time as dtime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler,
)
from database import Database
from jyotish import (
    get_detailed_positions, get_transit_context,
    calculate_natal_basics, calculate_full_natal, build_natal_context,
    calculate_varshaphal, calculate_compatibility, calculate_muhurta,
    get_transit_events, build_transit_broadcast,
)

logging.basicConfig(format="%(asctime)s — %(name)s — %(levelname)s — %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

GROUP_ID = -1001310958976

# Состояния
(WAITING_NAME, WAITING_BIRTH_DATE, WAITING_BIRTH_TIME,
 WAITING_BIRTH_PLACE, WAITING_PLACE_CONFIRM, WAITING_SAVE_CONFIRM) = range(6)
WAITING_VARSHA_YEAR   = 10
WAITING_MUHURTA_DATE  = 21
WAITING_MUHURTA_DAYS  = 22
WAITING_COMPAT_C2_NAME  = 30
WAITING_COMPAT_C2_DATE  = 31
WAITING_COMPAT_C2_TIME  = 32
WAITING_COMPAT_C2_PLACE = 33
WAITING_QUESTION = 40

MUHURTA_LABELS = {
    "свадьба":"💒 Свадьба","роспись":"📝 Роспись","бизнес":"💼 Бизнес",
    "путешествие":"✈️ Путешествие","операция":"🏥 Операция",
    "красота":"💅 Красота","покупка":"🛒 Покупка","переезд":"🏠 Переезд","лечение":"💊 Лечение",
}

db = Database("/data/users.db")


def reply_kb():
    return ReplyKeyboardMarkup([
        ["🪐 Транзиты планет", "📊 Прогноз"],
        ["🔱 Натальная карта", "📅 Варшапхала"],
        ["💑 Совместимость", "🗓 Благоприятные даты"],
        ["🗂 Мои карты", "➕ Добавить карту"],
        ["❓ Вопрос астрологу"],
    ], resize_keyboard=True)


def main_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪐 Транзиты планет",        callback_data="transit")],
        [InlineKeyboardButton("📊 Прогноз",                callback_data="forecast")],
        [InlineKeyboardButton("🔱 Натальная карта",        callback_data="natal")],
        [InlineKeyboardButton("📅 Варшапхала",             callback_data="varsha")],
        [InlineKeyboardButton("💑 Совместимость",          callback_data="compat")],
        [InlineKeyboardButton("🗓 Благоприятные даты",     callback_data="muhurta")],
        [InlineKeyboardButton("🗂 Мои карты",              callback_data="my_cards")],
        [InlineKeyboardButton("➕ Добавить карту",         callback_data="add_card")],
        [InlineKeyboardButton("❓ Вопрос астрологу",       callback_data="ask")],
    ])

def back_btn(cb="menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Меню", callback_data=cb)]])


# ── ИИ ────────────────────────────────────────────────────────────────
def build_prompt(card: dict) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    natal_ctx = build_natal_context(card) if card and card.get("birth_date") else ""
    return f"""Ты — профессиональный джйотиш-астролог. Только Джйотиш, никакой западной астрологии.
СЕГОДНЯ: {today}
{natal_ctx}
ПРАВИЛА:
1. Только термины Джйотиш: Граха, Раши, Бхава, Накшатра, Даша, Дришти, Юти
2. Анализируй планеты в домах, аспекты, силу (уччха/нича/сваграха)
3. Соотноси транзиты с натальными домами и Дашей
4. Развёрнутые конкретные интерпретации
5. Эмодзи: ☀️Солнце 🌙Луна 🔴Марс 🟡Меркурий 🟠Юпитер ⚪Венера 🟤Сатурн ☊Раху ☋Кету
6. Русский язык
7. В конце: БЛАГОПРИЯТНО / НЕЙТРАЛЬНО / ТРЕБУЕТ ВНИМАНИЯ
8. После итога — 2-3 уточняющих вопроса"""

async def call_ai(system: str, message: str, uid: int) -> str:
    history = db.get_history(uid, limit=8)
    try:
        import aiohttp
        api_key = os.environ["GROQ_API_KEY"]
        msgs = [{"role":"system","content":system}]
        for m in history:
            msgs.append({"role":"user" if m["role"]=="user" else "assistant","content":m["content"]})
        msgs.append({"role":"user","content":message})
        payload = {"model":"llama-3.3-70b-versatile","messages":msgs,"max_tokens":2048,"temperature":0.7}
        headers = {"Authorization":f"Bearer {api_key}","Content-Type":"application/json"}
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.groq.com/openai/v1/chat/completions",
                              json=payload, headers=headers,
                              timeout=aiohttp.ClientTimeout(total=40)) as r:
                data = await r.json()
        reply = data["choices"][0]["message"]["content"]
        db.save_message(uid,"user",message)
        db.save_message(uid,"assistant",reply)
        return reply
    except Exception as e:
        logger.error(f"Groq: {e}")
        return "❌ Ошибка API. Попробуй ещё раз."


# ── Старт ─────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.ensure_user(update.effective_user.id)
    name = update.effective_user.first_name or "Садхак"
    await update.message.reply_text(
        f"🔱 *Намасте, {name}*\n\nДжйотиш-ассистент.\nWhole Sign Houses, аянамша Лахири.\n\nВыбери раздел:",
        parse_mode="Markdown", reply_markup=reply_kb()
    )


# ── Reply keyboard ────────────────────────────────────────────────────
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid  = update.effective_user.id
    db.ensure_user(uid)

    actions = {
        "🪐 Транзиты планет":    "transit",
        "📊 Прогноз":            "forecast",
        "🔱 Натальная карта":    "natal",
        "📅 Варшапхала":         "varsha",
        "💑 Совместимость":      "compat",
        "🗓 Благоприятные даты": "muhurta",
        "🗂 Мои карты":          "my_cards",
        "➕ Добавить карту":     "add_card",
        "❓ Вопрос астрологу":   "ask",
    }

    cb = actions.get(text)
    if cb:
        # Создаём фейковый callback через отправку inline меню
        await update.message.reply_text(
            "Выбери действие:", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Продолжить", callback_data=cb)]
            ])
        )
    else:
        # Обычный вопрос
        card = db.get_active_card(uid) or {}
        thinking = await update.message.reply_text("⏳ Анализирую...")
        response = await call_ai(build_prompt(card), text, uid)
        await thinking.delete()
        await update.message.reply_text(response, parse_mode="Markdown")


# ── Inline handler ────────────────────────────────────────────────────
async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query
    await q.answer()
    uid  = q.from_user.id
    data = q.data

    # Меню
    if data == "menu":
        await q.edit_message_text("🔱 *Джйотиш Ассистент*\n\nВыбери раздел:",
                                   parse_mode="Markdown", reply_markup=main_inline())
        return

    # Транзиты
    if data == "transit":
        await q.edit_message_text("⏳ Рассчитываю...")
        t = get_detailed_positions()
        ctx = get_transit_context()
        today = datetime.now().strftime("%d.%m.%Y")
        text = f"🪐 *ТРАНЗИТЫ И ПЛАНЕТЫ — {today}*\n_(сидерический зодиак, аянамша Лахири)_\n\n{t}"
        if ctx: text += f"\n\n📌 *Конфигурации:*\n{ctx}"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())
        return

    # Прогноз — выбор карты
    if data == "forecast":
        cards = db.get_all_cards(uid)
        if not cards:
            await q.edit_message_text(
                "⚠️ Нет сохранённых карт.\nДобавь карту через ➕ Добавить карту",
                reply_markup=back_btn())
            return
        active = db.get_active_card(uid)
        active_id = active.get("id") if active else None
        keyboard = []
        for c in cards:
            mark = "✅ " if c["id"]==active_id else ""
            keyboard.append([InlineKeyboardButton(
                f"{mark}👤 {c['person_name']} ({c['birth_date']})",
                callback_data=f"forecast_card:{c['id']}")])
        keyboard.append([InlineKeyboardButton("◀️ Меню", callback_data="menu")])
        await q.edit_message_text("📊 *Прогноз*\n\nВыбери карту:",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("forecast_card:"):
        card_id = int(data.split(":")[1])
        db.set_active_card(uid, card_id)
        card = db.get_card_by_id(card_id)
        await q.edit_message_text(f"⏳ Строю прогноз для *{card['person_name']}*...",
                                   parse_mode="Markdown")
        prompt = "Дай развёрнутый персональный прогноз: транзиты по натальным домам, активная Даша, рекомендации на 2 недели по работе/финансам/здоровью/отношениям."
        r = await call_ai(build_prompt(card), prompt, uid)
        await q.edit_message_text(f"🔮 *ПРОГНОЗ — {card['person_name']}*\n\n{r}",
                                   parse_mode="Markdown", reply_markup=back_btn())
        return

    # Натальная карта — выбор карты
    if data == "natal":
        cards = db.get_all_cards(uid)
        if not cards:
            await q.edit_message_text(
                "⚠️ Нет сохранённых карт.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Добавить карту", callback_data="add_card")],
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")],
                ]))
            return
        keyboard = [[InlineKeyboardButton(f"👤 {c['person_name']} ({c['birth_date']})",
                     callback_data=f"natal_card:{c['id']}")] for c in cards]
        keyboard.append([InlineKeyboardButton("◀️ Меню", callback_data="menu")])
        await q.edit_message_text("🔱 *Натальная карта*\n\nВыбери карту:",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("natal_card:"):
        card = db.get_card_by_id(int(data.split(":")[1]))
        await q.edit_message_text(f"⏳ Строю карту для *{card['person_name']}*...",
                                   parse_mode="Markdown")
        result = calculate_full_natal(card["birth_date"], card.get("birth_time"), card.get("birth_place",""))
        ai = await call_ai(build_prompt(card), f"Интерпретируй натальную карту:\n{result}", uid)
        if len(result) > 3500:
            await q.edit_message_text(result[:3500], parse_mode="Markdown", reply_markup=back_btn())
            await q.message.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai}", parse_mode="Markdown")
        else:
            await q.edit_message_text(f"{result}\n\n*── ИНТЕРПРЕТАЦИЯ ──*\n{ai}",
                                       parse_mode="Markdown", reply_markup=back_btn())
        return

    # Варшапхала — выбор карты
    if data == "varsha":
        cards = db.get_all_cards(uid)
        if not cards:
            await q.edit_message_text("⚠️ Нет карт.", reply_markup=back_btn())
            return
        keyboard = [[InlineKeyboardButton(f"👤 {c['person_name']} ({c['birth_date']})",
                     callback_data=f"varsha_card:{c['id']}")] for c in cards]
        keyboard.append([InlineKeyboardButton("◀️ Меню", callback_data="menu")])
        await q.edit_message_text("📅 *Варшапхала*\n\nВыбери карту:",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("varsha_card:"):
        context.user_data["varsha_card_id"] = int(data.split(":")[1])
        card = db.get_card_by_id(context.user_data["varsha_card_id"])
        await q.edit_message_text(
            f"📅 Варшапхала для *{card['person_name']}*\n\nВведи год (например `{datetime.now().year}`):",
            parse_mode="Markdown")
        return WAITING_VARSHA_YEAR

    # Совместимость
    if data == "compat":
        cards = db.get_all_cards(uid)
        if not cards:
            await q.edit_message_text("⚠️ Нет карт.", reply_markup=back_btn())
            return
        keyboard = [[InlineKeyboardButton(f"👤 {c['person_name']} ({c['birth_date']})",
                     callback_data=f"compat_c1:{c['id']}")] for c in cards]
        keyboard.append([InlineKeyboardButton("◀️ Меню", callback_data="menu")])
        await q.edit_message_text("💑 *Совместимость*\n\nВыбери первого человека:",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("compat_c1:"):
        context.user_data["compat_c1"] = int(data.split(":")[1])
        cards = db.get_all_cards(uid)
        c1id = context.user_data["compat_c1"]
        keyboard = [[InlineKeyboardButton(f"👤 {c['person_name']} ({c['birth_date']})",
                     callback_data=f"compat_c2:{c['id']}")] for c in cards if c["id"]!=c1id]
        keyboard.append([InlineKeyboardButton("➕ Ввести данные нового человека",
                         callback_data="compat_new")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="compat")])
        await q.edit_message_text("💑 Выбери второго человека:",
                                   reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("compat_c2:"):
        c1 = db.get_card_by_id(context.user_data["compat_c1"])
        c2 = db.get_card_by_id(int(data.split(":")[1]))
        await q.edit_message_text("⏳ Рассчитываю совместимость...")
        result = calculate_compatibility(c1, c2)
        ai = await call_ai(build_prompt({}), f"Интерпретируй Кута-анализ:\n{result}", uid)
        text = f"{result}\n\n*── ИНТЕРПРЕТАЦИЯ ──*\n{ai}"
        if len(text) > 3500:
            await q.edit_message_text(result, parse_mode="Markdown", reply_markup=back_btn())
            await q.message.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai}", parse_mode="Markdown")
        else:
            await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())
        return

    if data == "compat_new":
        await q.edit_message_text("👤 Введи имя второго человека:")
        return WAITING_COMPAT_C2_NAME

    # Мухурта
    if data == "muhurta":
        items = list(MUHURTA_LABELS.items())
        keyboard = []
        for i in range(0, len(items), 2):
            row = [InlineKeyboardButton(items[i][1], callback_data=f"mtype:{items[i][0]}")]
            if i+1 < len(items):
                row.append(InlineKeyboardButton(items[i+1][1], callback_data=f"mtype:{items[i+1][0]}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("◀️ Меню", callback_data="menu")])
        await q.edit_message_text("🗓 *Подбор благоприятных дат*\n\nВыбери тип события:",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("mtype:"):
        context.user_data["mtype"] = data.split(":")[1]
        await q.edit_message_text("📅 С какой даты искать?\nФормат: `ДД.ММ.ГГГГ`",
                                   parse_mode="Markdown")
        return WAITING_MUHURTA_DATE

    # Мои карты
    if data == "my_cards":
        cards = db.get_all_cards(uid)
        active = db.get_active_card(uid)
        active_id = active.get("id") if active else None
        if not cards:
            await q.edit_message_text("🗂 Карт пока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Добавить карту", callback_data="add_card")],
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")],
                ]))
            return
        keyboard = []
        for c in cards:
            mark = "✅ " if c["id"]==active_id else ""
            keyboard.append([InlineKeyboardButton(
                f"{mark}👤 {c['person_name']} — {c['birth_date']}",
                callback_data=f"load_card:{c['id']}")])
            keyboard.append([InlineKeyboardButton(
                f"🗑 Удалить {c['person_name']}",
                callback_data=f"del_card:{c['id']}")])
        keyboard.append([InlineKeyboardButton("➕ Добавить карту", callback_data="add_card")])
        keyboard.append([InlineKeyboardButton("◀️ Меню", callback_data="menu")])
        await q.edit_message_text("🗂 *Мои карты*\n\nВыбери активную:",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("load_card:"):
        cid = int(data.split(":")[1])
        db.set_active_card(uid, cid)
        c = db.get_card_by_id(cid)
        await q.edit_message_text(
            f"✅ Активна карта: *{c['person_name']}*\n📅 {c['birth_date']}  📍 {c.get('birth_place','—')}",
            parse_mode="Markdown", reply_markup=back_btn("my_cards"))
        return

    if data.startswith("del_card:"):
        db.delete_card(int(data.split(":")[1]), uid)
        await q.answer("Карта удалена")
        # Обновляем список
        cards = db.get_all_cards(uid)
        active = db.get_active_card(uid)
        active_id = active.get("id") if active else None
        if not cards:
            await q.edit_message_text("🗂 Карт больше нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Добавить карту", callback_data="add_card")],
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")],
                ]))
            return
        keyboard = []
        for c in cards:
            mark = "✅ " if c["id"]==active_id else ""
            keyboard.append([InlineKeyboardButton(
                f"{mark}👤 {c['person_name']} — {c['birth_date']}",
                callback_data=f"load_card:{c['id']}")])
            keyboard.append([InlineKeyboardButton(
                f"🗑 Удалить {c['person_name']}",
                callback_data=f"del_card:{c['id']}")])
        keyboard.append([InlineKeyboardButton("➕ Добавить карту", callback_data="add_card")])
        keyboard.append([InlineKeyboardButton("◀️ Меню", callback_data="menu")])
        await q.edit_message_text("🗂 *Мои карты*", parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Добавить карту
    if data == "add_card":
        await q.edit_message_text(
            "👤 *Добавление карты*\n\nВведи имя и фамилию:",
            parse_mode="Markdown")
        return WAITING_NAME

    # Вопрос астрологу
    if data == "ask":
        await q.edit_message_text(
            "✍️ *Вопрос астрологу*\n\nНапиши свой вопрос по Джйотиш:",
            parse_mode="Markdown")
        return WAITING_QUESTION

    # Сохранение карты
    if data == "save_yes":
        card_data = context.user_data.get("pending_card", {})
        card_id = db.save_card(uid, card_data)
        db.set_active_card(uid, card_id)
        await q.edit_message_text(
            f"✅ *Карта сохранена!*\n\n"
            f"👤 {card_data.get('person_name')}\n"
            f"📅 {card_data.get('birth_date')}  "
            f"⏰ {card_data.get('birth_time') or 'не указано'}\n"
            f"📍 {card_data.get('birth_place','—')}\n"
            f"🌍 Часовой пояс: {card_data.get('timezone','—')}\n\n"
            f"☀️ Солнце: {card_data.get('sun_sign','—')}\n"
            f"🌙 Луна: {card_data.get('moon_sign','—')} / {card_data.get('moon_nakshatra','—')}\n"
            f"🔱 Лагна: {card_data.get('lagna','—')}\n"
            f"⏳ Маха-Даша: {card_data.get('mahadasha','—')}\n"
            f"⏳ Антар-Даша: {card_data.get('antardasha','—')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔱 Натальная карта", callback_data=f"natal_card:{card_id}")],
                [InlineKeyboardButton("📊 Прогноз", callback_data="forecast")],
                [InlineKeyboardButton("◀️ Меню", callback_data="menu")],
            ])
        )
        context.user_data.pop("pending_card", None)
        return ConversationHandler.END

    if data == "save_no":
        await q.edit_message_text("Карта не сохранена.", reply_markup=back_btn())
        context.user_data.pop("pending_card", None)
        return ConversationHandler.END

    if data.startswith("geo_pick:"):
        idx = int(data.split(":")[1])
        variants = context.user_data.get("geo_variants", [])
        if idx < len(variants):
            context.user_data["birth_place"] = variants[idx]["name"]
        await q.edit_message_text(f"📍 Выбрано: _{context.user_data['birth_place']}_\n\n⏳ Рассчитываю...",
                                   parse_mode="Markdown")
        await _do_natal_calc(q.message, context, uid)
        return WAITING_SAVE_CONFIRM

    if data == "geo_retry":
        await q.edit_message_text("📍 Введи место рождения (город, страна):")
        return WAITING_BIRTH_PLACE

    if data == "post_now":
        await _post_to_group(context.application, manual=True)
        await q.answer("✅ Отправлено в группу", show_alert=True)
        return


# ── Диалог добавления карты ────────────────────────────────────────────
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "👤 *Добавление карты*\n\nВведи имя и фамилию:", parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "👤 *Добавление карты*\n\nВведи имя и фамилию:", parse_mode="Markdown")
    return WAITING_NAME

async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["person_name"] = update.message.text.strip()
    await update.message.reply_text(
        "📅 Дата рождения `ДД.ММ.ГГГГ`\n\nНапример: `15.03.1990`",
        parse_mode="Markdown")
    return WAITING_BIRTH_DATE

async def got_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
        context.user_data["birth_date"] = text
        await update.message.reply_text(
            "⏰ Время рождения `ЧЧ:ММ`\n\nЕсли не знаешь — напиши `0`",
            parse_mode="Markdown")
        return WAITING_BIRTH_TIME
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введи `ДД.ММ.ГГГГ`", parse_mode="Markdown")
        return WAITING_BIRTH_DATE

async def got_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "0":
        context.user_data["birth_time"] = None
    else:
        try:
            datetime.strptime(text, "%H:%M")
            context.user_data["birth_time"] = text
        except ValueError:
            await update.message.reply_text("❌ Формат `ЧЧ:ММ` или `0`", parse_mode="Markdown")
            return WAITING_BIRTH_TIME
    await update.message.reply_text("📍 Место рождения (город, страна):\n\nНапример: `Киев, Украина`")
    return WAITING_BIRTH_PLACE

async def got_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    place = update.message.text.strip()
    from geopy.geocoders import Nominatim
    geo = Nominatim(user_agent="jyotish_bot_v5", timeout=10)
    try:
        results = geo.geocode(place, exactly_one=False, limit=5, language="ru", addressdetails=True)
    except Exception:
        results = None

    if results and len(results) > 1:
        context.user_data["geo_variants"] = [{"name": r.address} for r in results]
        keyboard = []
        for i, r in enumerate(results):
            parts = r.address.split(",")
            short = ", ".join(p.strip() for p in parts[:3])
            keyboard.append([InlineKeyboardButton(short, callback_data=f"geo_pick:{i}")])
        keyboard.append([InlineKeyboardButton("✏️ Другое место", callback_data="geo_retry")])
        await update.message.reply_text(
            f"📍 Уточни место для *{place}*:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_PLACE_CONFIRM
    elif results:
        context.user_data["birth_place"] = results[0].address
    else:
        context.user_data["birth_place"] = place

    uid = update.effective_user.id
    await _do_natal_calc(update.message, context, uid)
    return WAITING_SAVE_CONFIRM

async def _do_natal_calc(msg, context, uid: int):
    birth_date  = context.user_data["birth_date"]
    birth_time  = context.user_data.get("birth_time")
    person_name = context.user_data.get("person_name", "Без имени")
    place       = context.user_data.get("birth_place", "")

    await msg.reply_text("⏳ Рассчитываю натальные позиции...")
    natal = calculate_natal_basics(birth_date, birth_time, place)

    if natal.get("error"):
        await msg.reply_text(f"❌ Ошибка: {natal['error']}\nПопробуй ввести место ещё раз.")
        return

    card_data = {
        "person_name": person_name,
        "birth_date":  birth_date,
        "birth_time":  birth_time,
        "birth_place": natal.get("birth_place_full", place),
        **natal,
    }
    context.user_data["pending_card"] = card_data

    await msg.reply_text(
        f"🔱 *Карта рассчитана*\n\n"
        f"👤 {person_name}\n"
        f"📅 {birth_date}  ⏰ {birth_time or 'не указано'}\n"
        f"📍 {natal.get('birth_place_full', place)}\n"
        f"🌍 Часовой пояс: {natal.get('timezone','—')}\n\n"
        f"☀️ Солнце: {natal.get('sun_sign','—')}\n"
        f"🌙 Луна: {natal.get('moon_sign','—')} / {natal.get('moon_nakshatra','—')}\n"
        f"🔱 Лагна: {natal.get('lagna','—')}\n\n"
        f"⏳ Маха-Даша: {natal.get('mahadasha','—')}\n"
        f"⏳ Антар-Даша: {natal.get('antardasha','—')}\n\n"
        f"Сохранить в *Мои карты*?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Сохранить", callback_data="save_yes"),
             InlineKeyboardButton("❌ Не сохранять", callback_data="save_no")],
        ])
    )


# ── Диалог вопроса астрологу ──────────────────────────────────────────
async def got_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    text = update.message.text.strip()
    card = db.get_active_card(uid) or {}
    thinking = await update.message.reply_text("⏳ Анализирую...")
    response = await call_ai(build_prompt(card), text, uid)
    await thinking.delete()
    await update.message.reply_text(response, parse_mode="Markdown")
    await update.message.reply_text(
        "Задать ещё вопрос или вернуться в меню?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Ещё вопрос", callback_data="ask")],
            [InlineKeyboardButton("◀️ Меню", callback_data="menu")],
        ])
    )
    return ConversationHandler.END


# ── Диалог Варшапхалы ─────────────────────────────────────────────────
async def got_varsha_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        year = int(update.message.text.strip())
        if not 1900 <= year <= 2100: raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи корректный год, например `2026`", parse_mode="Markdown")
        return WAITING_VARSHA_YEAR
    uid  = update.effective_user.id
    card_id = context.user_data.get("varsha_card_id")
    card = db.get_card_by_id(card_id) if card_id else db.get_active_card(uid)
    await update.message.reply_text("⏳ Рассчитываю Варшапхалу...")
    result = calculate_varshaphal(card["birth_date"], card.get("birth_time"), card.get("birth_place",""), year)
    ai = await call_ai(build_prompt(card), f"Интерпретируй Варшапхалу:\n{result}", uid)
    await update.message.reply_text(result, parse_mode="Markdown")
    await update.message.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai}", parse_mode="Markdown")
    return ConversationHandler.END


# ── Диалог Мухурты ────────────────────────────────────────────────────
async def got_muhurta_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
        context.user_data["mstart"] = text
        await update.message.reply_text("📆 На сколько дней вперёд? (7–90)\nНапример: `30`")
        return WAITING_MUHURTA_DAYS
    except ValueError:
        await update.message.reply_text("❌ Формат: `ДД.ММ.ГГГГ`", parse_mode="Markdown")
        return WAITING_MUHURTA_DATE

async def got_muhurta_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text.strip())
        if not 1 <= days <= 90: raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи число от 7 до 90")
        return WAITING_MUHURTA_DAYS
    et = context.user_data.get("mtype", "бизнес")
    sd = context.user_data.get("mstart")
    await update.message.reply_text("⏳ Ищу благоприятные даты...")
    result = calculate_muhurta(et, sd, days)
    await update.message.reply_text(result, parse_mode="Markdown")
    return ConversationHandler.END


# ── Диалог совместимости (новый человек) ─────────────────────────────
async def got_c2_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["c2_name"] = update.message.text.strip()
    await update.message.reply_text("📅 Дата рождения `ДД.ММ.ГГГГ`", parse_mode="Markdown")
    return WAITING_COMPAT_C2_DATE

async def got_c2_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
        context.user_data["c2_date"] = text
        await update.message.reply_text("⏰ Время рождения `ЧЧ:ММ` или `0`", parse_mode="Markdown")
        return WAITING_COMPAT_C2_TIME
    except ValueError:
        await update.message.reply_text("❌ Формат: `ДД.ММ.ГГГГ`", parse_mode="Markdown")
        return WAITING_COMPAT_C2_DATE

async def got_c2_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["c2_time"] = None if text=="0" else text
    await update.message.reply_text("📍 Место рождения (город, страна):")
    return WAITING_COMPAT_C2_PLACE

async def got_c2_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    result = calculate_compatibility(c1, c2)
    ai = await call_ai(build_prompt({}), f"Интерпретируй Кута-анализ:\n{result}", uid)
    await update.message.reply_text(result, parse_mode="Markdown")
    await update.message.reply_text(f"*── ИНТЕРПРЕТАЦИЯ ──*\n{ai}", parse_mode="Markdown")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=reply_kb())
    return ConversationHandler.END


# ── Рассылка ──────────────────────────────────────────────────────────
async def _post_to_group(app, manual=False):
    events = get_transit_events()
    if not events and not manual:
        return
    if not events and manual:
        t = get_detailed_positions()
        ctx = get_transit_context()
        today = datetime.now().strftime("%d.%m.%Y")
        text = f"🪐 *ТРАНЗИТЫ И ПЛАНЕТЫ — {today}*\n\n{t}"
        if ctx: text += f"\n\n📌 {ctx}"
        try:
            await app.bot.send_message(GROUP_ID, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Рассылка: {e}")
        return
    for ev in events:
        text = build_transit_broadcast(ev)
        try:
            await app.bot.send_message(GROUP_ID, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Рассылка: {e}")

async def cmd_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _post_to_group(context.application, manual=True)
    await update.message.reply_text("✅ Прогноз отправлен в группу")


# ── Запуск ────────────────────────────────────────────────────────────
def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token: raise ValueError("Укажи TELEGRAM_BOT_TOKEN")
    if not os.environ.get("GROQ_API_KEY"): raise ValueError("Укажи GROQ_API_KEY")

    app = Application.builder().token(token).build()

    # APScheduler 12:00 МСК
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    async def broadcast_job():
        await _post_to_group(app)
    scheduler.add_job(broadcast_job, "cron", hour=12, minute=0)
    scheduler.start()

    txt = filters.TEXT & ~filters.COMMAND

    card_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_handler, pattern="^add_card$")],
        states={
            WAITING_NAME:         [MessageHandler(txt, got_name)],
            WAITING_BIRTH_DATE:   [MessageHandler(txt, got_date)],
            WAITING_BIRTH_TIME:   [MessageHandler(txt, got_time)],
            WAITING_BIRTH_PLACE:  [MessageHandler(txt, got_place)],
            WAITING_PLACE_CONFIRM:[CallbackQueryHandler(cb_handler, pattern="^geo_")],
            WAITING_SAVE_CONFIRM: [CallbackQueryHandler(cb_handler, pattern="^save_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    ask_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_handler, pattern="^ask$")],
        states={
            WAITING_QUESTION: [MessageHandler(txt, got_question)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    varsha_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_handler, pattern="^varsha_card:")],
        states={
            WAITING_VARSHA_YEAR: [MessageHandler(txt, got_varsha_year)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    muhurta_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_handler, pattern="^mtype:")],
        states={
            WAITING_MUHURTA_DATE: [MessageHandler(txt, got_muhurta_date)],
            WAITING_MUHURTA_DAYS: [MessageHandler(txt, got_muhurta_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    compat_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_handler, pattern="^compat_new$")],
        states={
            WAITING_COMPAT_C2_NAME:  [MessageHandler(txt, got_c2_name)],
            WAITING_COMPAT_C2_DATE:  [MessageHandler(txt, got_c2_date)],
            WAITING_COMPAT_C2_TIME:  [MessageHandler(txt, got_c2_time)],
            WAITING_COMPAT_C2_PLACE: [MessageHandler(txt, got_c2_place)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post",  cmd_post))
    app.add_handler(card_conv)
    app.add_handler(ask_conv)
    app.add_handler(varsha_conv)
    app.add_handler(muhurta_conv)
    app.add_handler(compat_conv)
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(txt, text_handler))

    logger.info("🔱 Джйотиш бот v5 запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
