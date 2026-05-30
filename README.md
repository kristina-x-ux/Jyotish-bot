# 🔱 ДЖЙОТИШ ТРАНЗИТ БОТ

Бесплатный астрологический Telegram-бот на базе Google Gemini + Swiss Ephemeris.

---

## Шаг 1 — Получи токены (оба бесплатно)

### Telegram Bot Token
1. Открой [@BotFather](https://t.me/BotFather)
2. Напиши `/newbot` → придумай имя → скопируй токен

### Google Gemini API Key (БЕСПЛАТНО — 1500 запросов/день)
1. Зайди на https://aistudio.google.com/app/apikey
2. Нажми **Create API Key**
3. Скопируй ключ — выглядит как `AIzaSy...`

---

## Шаг 2 — Запуск

### Локально
```bash
cd jyotish_bot
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN="твой_токен"
export GEMINI_API_KEY="AIzaSy..."

python bot.py
```

### Railway (бесплатный хостинг)
1. railway.app → New Project → загрузи папку
2. Variables:
   ```
   TELEGRAM_BOT_TOKEN = твой_токен
   GEMINI_API_KEY     = твой_ключ
   ```
3. Deploy

### Docker
```bash
docker build -t jyotish-bot .
docker run -d \
  -e TELEGRAM_BOT_TOKEN="токен" \
  -e GEMINI_API_KEY="ключ" \
  jyotish-bot
```

---

## Файлы
```
bot.py        — Telegram бот
jyotish.py    — Расчёты Swiss Ephemeris (сидерический зодиак, аянамша Лахири)
database.py   — SQLite (натальные данные, история чата)
requirements.txt
```

## Возможные проблемы

| Ошибка | Решение |
|--------|---------|
| pyswisseph не ставится | `pip install pyswisseph --no-binary pyswisseph` |
| 429 Too Many Requests | Превышен лимит Gemini (1500/день), подожди до завтра |
| Бот не отвечает | Проверь логи: `python bot.py 2>&1 | tee bot.log` |
