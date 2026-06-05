"""
╔══════════════════════════════════════╗
║   ДЖЙОТИШ РАСЧЁТЫ — jyotish.py v3   ║
║   Whole Sign Houses, реальная Лагна  ║
╚══════════════════════════════════════╝
"""

import swisseph as swe
from datetime import datetime, timezone, timedelta
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pytz
import math

swe.set_ephe_path("")
AYANAMSHA = swe.SIDM_LAHIRI

# ── Русские названия ───────────────────────────────────────────────────
GRAHAS = {
    "Солнце":   (swe.SUN,       "☀️"),
    "Луна":     (swe.MOON,      "🌙"),
    "Марс":     (swe.MARS,      "🔴"),
    "Меркурий": (swe.MERCURY,   "🟡"),
    "Юпитер":   (swe.JUPITER,   "🟠"),
    "Венера":   (swe.VENUS,     "⚪"),
    "Сатурн":   (swe.SATURN,    "🟤"),
    "Раху":     (swe.MEAN_NODE, "☊"),
    "Кету":     (None,          "☋"),
}

RASHI = [
    "Овен","Телец","Близнецы","Рак",
    "Лев","Дева","Весы","Скорпион",
    "Стрелец","Козерог","Водолей","Рыбы",
]
RASHI_EMOJI = ["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"]

NAKSHATRAS = [
    "Ашвини","Бхарани","Криттика","Рохини","Мригашира",
    "Ардра","Пунарвасу","Пушья","Ашлеша","Магха",
    "Пурва Пхалгуни","Уттара Пхалгуни","Хаста","Читра","Свати",
    "Вишакха","Анурадха","Джьештха","Мула","Пурва Ашадха",
    "Уттара Ашадха","Шравана","Дхаништха","Шатабхиша",
    "Пурва Бхадрапада","Уттара Бхадрапада","Ревати",
]
NAKSHATRA_LORDS = [
    "Кету","Венера","Солнце","Луна","Марс",
    "Раху","Юпитер","Сатурн","Меркурий","Кету",
    "Венера","Солнце","Луна","Марс","Раху",
    "Юпитер","Сатурн","Меркурий","Кету","Венера",
    "Солнце","Луна","Марс","Раху","Юпитер",
    "Сатурн","Меркурий",
]

DASHA_YEARS = {
    "Кету":7,"Венера":20,"Солнце":6,"Луна":10,
    "Марс":7,"Раху":18,"Юпитер":16,"Сатурн":19,"Меркурий":17,
}
DASHA_ORDER = ["Кету","Венера","Солнце","Луна","Марс","Раху","Юпитер","Сатурн","Меркурий"]

UCHCHA = {
    swe.SUN:0, swe.MOON:1, swe.MARS:9, swe.MERCURY:5,
    swe.JUPITER:3, swe.VENUS:11, swe.SATURN:6,
}
NICHA = {p:(d+6)%12 for p,d in UCHCHA.items()}
DOMICILE = {
    swe.SUN:[4], swe.MOON:[3], swe.MARS:[0,7],
    swe.MERCURY:[2,5], swe.JUPITER:[8,11],
    swe.VENUS:[1,6], swe.SATURN:[9,10],
}
RASHI_LORD = {
    0:swe.MARS,1:swe.VENUS,2:swe.MERCURY,3:swe.MOON,
    4:swe.SUN,5:swe.MERCURY,6:swe.VENUS,7:swe.MARS,
    8:swe.JUPITER,9:swe.SATURN,10:swe.SATURN,11:swe.JUPITER,
}
PLANET_FRIENDS = {
    swe.SUN:    [swe.MOON,swe.MARS,swe.JUPITER],
    swe.MOON:   [swe.SUN,swe.MERCURY],
    swe.MARS:   [swe.SUN,swe.MOON,swe.JUPITER],
    swe.MERCURY:[swe.SUN,swe.VENUS],
    swe.JUPITER:[swe.SUN,swe.MOON,swe.MARS],
    swe.VENUS:  [swe.MERCURY,swe.SATURN],
    swe.SATURN: [swe.MERCURY,swe.VENUS],
}
GANA  = [0,2,0,0,0,2,0,0,2,2,1,0,0,2,0,1,1,2,2,2,0,1,2,1,1,0,0]
YONI  = ["Конь","Слон","Овца","Змея","Змея","Собака","Кошка","Баран",
         "Кошка","Крыса","Лев","Бык","Буйвол","Тигр","Буйвол","Тигр",
         "Заяц","Олень","Собака","Обезьяна","Мангуст","Обезьяна","Лев",
         "Лошадь","Лев","Корова","Слон"]
NADI  = [0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,0,1,2]

MUHURTA_NAKSHATRAS = {
    "свадьба":    [2,3,6,7,11,12,13,20,21,22,25,26],
    "роспись":    [2,3,6,7,11,12,13,20,21,22,25,26],
    "бизнес":     [0,2,3,6,7,10,11,12,20,21,22,25],
    "путешествие":[0,2,5,6,7,11,12,20,21,22,23,25],
    "операция":   [2,7,10,11,12,20,21,22,25,26],
    "красота":    [1,2,3,6,7,11,12,13,14,25,26],
    "покупка":    [0,2,3,6,7,10,11,12,20,21,22,25],
    "переезд":    [0,2,3,6,7,11,12,20,21,22,25],
    "лечение":    [2,7,10,11,12,20,21,22,25,26],
}
MUHURTA_WEEKDAYS = {
    "свадьба":    [0,2,3,4],
    "роспись":    [0,2,3,4],
    "бизнес":     [0,2,3,4,5],
    "путешествие":[0,1,2,3,4],
    "операция":   [0,2,3],
    "красота":    [0,2,3,4,5],
    "покупка":    [0,2,3,4,5],
    "переезд":    [0,2,3,4],
    "лечение":    [0,2,3,5],
}
WEEKDAY_RU = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
MONTH_RU   = ["","января","февраля","марта","апреля","мая","июня",
               "июля","августа","сентября","октября","ноября","декабря"]

# ── Геокодирование ─────────────────────────────────────────────────────
_geocoder = Nominatim(user_agent="jyotish_bot_v3", timeout=10)
_tf = TimezoneFinder()

def geocode_place(place: str) -> tuple:
    """Возвращает (lat, lon, timezone_str, full_name) или None."""
    try:
        loc = _geocoder.geocode(place, language="ru")
        if not loc:
            loc = _geocoder.geocode(place, language="en")
        if not loc:
            return None
        tz_str = _tf.timezone_at(lat=loc.latitude, lng=loc.longitude)
        return loc.latitude, loc.longitude, tz_str or "UTC", loc.address
    except Exception:
        return None


# ── Базовые функции ────────────────────────────────────────────────────
def now_jd() -> float:
    now = datetime.now(timezone.utc)
    return swe.julday(now.year, now.month, now.day,
                      now.hour + now.minute/60 + now.second/3600)

def dt_to_jd(dt: datetime) -> float:
    if dt.tzinfo:
        dt_utc = dt.astimezone(pytz.utc)
    else:
        dt_utc = dt
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                      dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)

def sidereal_lon(pid: int, jd: float) -> float:
    swe.set_sid_mode(AYANAMSHA)
    r, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL | swe.FLG_SPEED)
    return r[0] % 360

def lon_to_rashi(lon: float) -> int:
    return int(lon // 30)

def lon_to_deg_in_rashi(lon: float) -> float:
    return lon % 30

def lon_to_nakshatra(lon: float) -> tuple:
    span = 360/27
    idx = int(lon / span) % 27
    frac = (lon % span) / span
    return idx, frac

def planet_strength(pid: int, rashi: int) -> str:
    if UCHCHA.get(pid) == rashi:   return " ⬆️уччха"
    if NICHA.get(pid)  == rashi:   return " ⬇️нича"
    if rashi in DOMICILE.get(pid,[]): return " 🏠сваграха"
    return ""

# ── Whole Sign дома ────────────────────────────────────────────────────
def calculate_lagna(jd: float, lat: float, lon: float) -> int:
    """Рассчитывает Лагну (Асцендент) и возвращает индекс раши 0-11."""
    swe.set_sid_mode(AYANAMSHA)
    cusps, ascmc = swe.houses_ex(jd, lat, lon, b'W', swe.FLG_SIDEREAL)
    asc_lon = ascmc[0] % 360
    return lon_to_rashi(asc_lon), asc_lon

def get_whole_sign_houses(lagna_rashi: int) -> dict:
    """Возвращает словарь {номер_дома: раши_индекс} для Whole Sign."""
    return {i+1: (lagna_rashi + i) % 12 for i in range(12)}

def planet_house(planet_rashi: int, lagna_rashi: int) -> int:
    """Возвращает номер дома (1-12) для планеты в системе Whole Sign."""
    return (planet_rashi - lagna_rashi) % 12 + 1

# ── Получение всех позиций ─────────────────────────────────────────────
def get_all_positions(jd: float, lat: float = 0, lon_geo: float = 0) -> dict:
    swe.set_sid_mode(AYANAMSHA)
    positions = {}
    rahu_lon = sidereal_lon(swe.MEAN_NODE, jd)

    # Лагна если есть координаты
    lagna_rashi = None
    lagna_lon = None
    if lat != 0 or lon_geo != 0:
        lagna_rashi, lagna_lon = calculate_lagna(jd, lat, lon_geo)

    for name, (pid, emoji) in GRAHAS.items():
        if name == "Кету":
            plon = (rahu_lon + 180) % 360
            speed = 0
        else:
            r, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL | swe.FLG_SPEED)
            plon = r[0] % 360
            speed = r[3]

        rashi = lon_to_rashi(plon)
        deg   = lon_to_deg_in_rashi(plon)
        ni, nf = lon_to_nakshatra(plon)
        house = planet_house(rashi, lagna_rashi) if lagna_rashi is not None else None

        positions[name] = {
            "lon": plon, "rashi": rashi, "deg": deg,
            "nak": ni, "nak_frac": nf, "speed": speed,
            "pid": pid if name != "Кету" else -1,
            "house": house,
        }

    if lagna_rashi is not None:
        positions["__lagna__"] = {
            "rashi": lagna_rashi, "lon": lagna_lon,
            "deg": lon_to_deg_in_rashi(lagna_lon),
        }

    return positions


# ── Транзиты ──────────────────────────────────────────────────────────
def get_current_transits() -> str:
    jd = now_jd()
    pos = get_all_positions(jd)
    lines = []
    for name, (pid, emoji) in GRAHAS.items():
        p = pos[name]
        deg_str = f"{int(p['deg'])}°{int((p['deg']%1)*60):02d}'"
        strength = planet_strength(pid, p['rashi']) if pid and name != "Кету" else ""
        retro = " ℞" if p['speed'] < 0 else ""
        lines.append(
            f"{emoji} *{name}* — {RASHI[p['rashi']]} {deg_str}{retro}{strength}\n"
            f"   накшатра: {NAKSHATRAS[p['nak']]}"
        )
    return "\n".join(lines)


def get_detailed_positions() -> str:
    jd = now_jd()
    pos = get_all_positions(jd)
    lines = []
    for name, (pid, emoji) in GRAHAS.items():
        p = pos[name]
        deg_str = f"{int(p['deg'])}°{int((p['deg']%1)*60):02d}'"
        retro = " ℞ *ретроград*" if p['speed'] < 0 else ""
        strength = planet_strength(pid, p['rashi']) if pid and name != "Кету" else ""
        pada = int(p['nak_frac']*4)+1
        lines.append(
            f"{emoji} *{name}*: {RASHI[p['rashi']]} {deg_str}{retro}{strength}\n"
            f"   📿 {NAKSHATRAS[p['nak']]} (пада {pada})"
        )
    return "\n".join(lines)


def get_transit_context() -> str:
    jd = now_jd()
    pos = get_all_positions(jd)
    notes = []
    rashi_groups = {}
    for name, p in pos.items():
        if name.startswith("__"): continue
        rashi_groups.setdefault(p['rashi'], []).append(name)
    for ri, planets in rashi_groups.items():
        if len(planets) >= 2:
            notes.append(f"🔗 Юти в {RASHI[ri]}: {' + '.join(planets)}")
    pl = [(n,p) for n,p in pos.items() if not n.startswith("__")]
    for i in range(len(pl)):
        for j in range(i+1, len(pl)):
            n1,p1 = pl[i]; n2,p2 = pl[j]
            diff = abs(p1['lon']-p2['lon']) % 360
            if diff > 180: diff = 360-diff
            if 170 <= diff <= 190:
                notes.append(f"⟺ Оппозиция: {n1} — {n2}")
            elif 115 <= diff <= 125:
                notes.append(f"△ Трин: {n1} — {n2}")
    return "\n".join(notes[:6]) if notes else ""


# ── Структурированные данные для ИИ ───────────────────────────────────
def build_natal_context(card: dict) -> str:
    """Полный контекст натальной карты для передачи ИИ."""
    try:
        geo = geocode_place(card.get("birth_place", ""))
        lat, lon_geo = (geo[0], geo[1]) if geo else (0, 0)
        tz_str = geo[2] if geo else "UTC"

        if card.get("birth_time"):
            tz = pytz.timezone(tz_str)
            dt_local = tz.localize(datetime.strptime(
                f"{card['birth_date']} {card['birth_time']}", "%d.%m.%Y %H:%M"))
            dt_utc = dt_local.astimezone(pytz.utc)
        else:
            dt_utc = datetime.strptime(card["birth_date"], "%d.%m.%Y").replace(
                hour=12, tzinfo=pytz.utc)

        jd = dt_to_jd(dt_utc)
        pos = get_all_positions(jd, lat, lon_geo)
        lagna = pos.get("__lagna__")
        lagna_rashi = lagna["rashi"] if lagna else 0
        houses = get_whole_sign_houses(lagna_rashi)

        # Текущие транзиты
        jd_now = now_jd()
        transit_pos = get_all_positions(jd_now)

        lines = [
            f"=== НАТАЛЬНАЯ КАРТА: {card.get('person_name','—')} ===",
            f"Дата: {card['birth_date']}  Время: {card.get('birth_time','не указано')}  Место: {card.get('birth_place','—')}",
            f"Часовой пояс: {tz_str}",
            f"Лагна (Асцендент): {RASHI[lagna_rashi]}",
            "",
            "НАТАЛЬНЫЕ ПЛАНЕТЫ (Whole Sign Houses):",
        ]

        for name, (pid, emoji) in GRAHAS.items():
            p = pos[name]
            deg_str = f"{int(p['deg'])}°{int((p['deg']%1)*60):02d}'"
            strength = planet_strength(pid, p['rashi']) if pid and name != "Кету" else ""
            retro = " ℞" if p['speed'] < 0 else ""
            pada = int(p['nak_frac']*4)+1
            house = p.get('house') or planet_house(p['rashi'], lagna_rashi)
            lines.append(
                f"{emoji} {name}: {RASHI[p['rashi']]} {deg_str}{retro}{strength} | "
                f"Дом {house} | {NAKSHATRAS[p['nak']]} пада {pada}"
            )

        # Дома
        lines.append("\nДОМА (Whole Sign):")
        for h in range(1,13):
            r = houses[h]
            lord_pid = RASHI_LORD.get(r)
            lord_name = next((n for n,(p,_) in GRAHAS.items() if p==lord_pid), "—")
            lines.append(f"  Дом {h}: {RASHI[r]} (владыка: {lord_name})")

        # Аспекты
        aspects = calculate_parashara_aspects(pos, lagna_rashi)
        if aspects:
            lines.append("\nАСПЕКТЫ (ДРИШТИ):")
            for a in aspects[:10]:
                lines.append(f"  {a}")

        # Йоги
        yogas = calculate_yogas(pos)
        if yogas:
            lines.append("\nЙОГИ:")
            for y in yogas:
                lines.append(f"  ✨ {y}")

        # Даша
        md, ad = calculate_vimshottari(pos["Луна"]["lon"], dt_utc)
        lines.append(f"\nДАША ВИМШОТТАРИ:")
        lines.append(f"  Маха-Даша: {md}")
        lines.append(f"  Антар-Даша: {ad}")
        lines.append(f"  Накшатра Луны: {NAKSHATRAS[pos['Луна']['nak']]}")

        # Транзиты по натальным домам
        lines.append(f"\nТЕКУЩИЕ ТРАНЗИТЫ ПО НАТАЛЬНЫМ ДОМАМ:")
        for name, (pid, emoji) in GRAHAS.items():
            tp = transit_pos[name]
            t_house = planet_house(tp['rashi'], lagna_rashi)
            retro = " ℞" if tp['speed'] < 0 else ""
            lines.append(
                f"  {emoji} {name}: {RASHI[tp['rashi']]}{retro} → Дом {t_house}"
            )

        return "\n".join(lines)

    except Exception as e:
        return f"Ошибка построения контекста: {e}"


# ── Натальная карта ────────────────────────────────────────────────────
def calculate_natal_basics(birth_date: str, birth_time, place: str) -> dict:
    try:
        geo = geocode_place(place)
        lat, lon_geo = (geo[0], geo[1]) if geo else (0, 0)
        tz_str = geo[2] if geo else "UTC"
        full_name = geo[3] if geo else place

        if birth_time and geo:
            tz = pytz.timezone(tz_str)
            dt_local = tz.localize(datetime.strptime(
                f"{birth_date} {birth_time}", "%d.%m.%Y %H:%M"))
            dt_utc = dt_local.astimezone(pytz.utc)
        elif birth_time:
            dt_utc = datetime.strptime(
                f"{birth_date} {birth_time}", "%d.%m.%Y %H:%M").replace(tzinfo=pytz.utc)
        else:
            dt_utc = datetime.strptime(birth_date, "%d.%m.%Y").replace(
                hour=12, tzinfo=pytz.utc)

        jd = dt_to_jd(dt_utc)
        pos = get_all_positions(jd, lat, lon_geo)
        lagna = pos.get("__lagna__")
        lagna_rashi = lagna["rashi"] if lagna else pos["Солнце"]["rashi"]

        md, ad = calculate_vimshottari(pos["Луна"]["lon"], dt_utc)

        return {
            "sun_sign":      RASHI[pos["Солнце"]["rashi"]],
            "moon_sign":     RASHI[pos["Луна"]["rashi"]],
            "moon_nakshatra":NAKSHATRAS[pos["Луна"]["nak"]],
            "lagna":         RASHI[lagna_rashi],
            "lagna_rashi":   lagna_rashi,
            "mahadasha":     md,
            "antardasha":    ad,
            "timezone":      tz_str,
            "birth_place_full": full_name,
            "lat": lat,
            "lon_geo": lon_geo,
        }
    except Exception as e:
        return {"error": str(e)}


def calculate_full_natal(birth_date: str, birth_time, place: str) -> str:
    try:
        geo = geocode_place(place)
        lat, lon_geo = (geo[0], geo[1]) if geo else (0, 0)
        tz_str = geo[2] if geo else "UTC"

        if birth_time and geo:
            tz = pytz.timezone(tz_str)
            dt_local = tz.localize(datetime.strptime(
                f"{birth_date} {birth_time}", "%d.%m.%Y %H:%M"))
            dt_utc = dt_local.astimezone(pytz.utc)
        elif birth_time:
            dt_utc = datetime.strptime(
                f"{birth_date} {birth_time}", "%d.%m.%Y %H:%M").replace(tzinfo=pytz.utc)
        else:
            dt_utc = datetime.strptime(birth_date, "%d.%m.%Y").replace(
                hour=12, tzinfo=pytz.utc)

        jd = dt_to_jd(dt_utc)
        pos = get_all_positions(jd, lat, lon_geo)
        lagna = pos.get("__lagna__")
        lagna_rashi = lagna["rashi"] if lagna else pos["Солнце"]["rashi"]
        houses = get_whole_sign_houses(lagna_rashi)

        lines = [
            f"🔱 *НАТАЛЬНАЯ КАРТА*",
            f"📅 {birth_date}  ⏰ {birth_time or 'не указано'}  📍 {place}",
            f"🌍 Часовой пояс: {tz_str}\n",
            f"*── ЛАГНА ──*",
            f"🔱 Асцендент: *{RASHI[lagna_rashi]}* {RASHI_EMOJI[lagna_rashi]}\n",
            f"*── ПЛАНЕТЫ ──*",
        ]

        for name, (pid, emoji) in GRAHAS.items():
            p = pos[name]
            deg_str = f"{int(p['deg'])}°{int((p['deg']%1)*60):02d}'"
            strength = planet_strength(pid, p['rashi']) if pid and name != "Кету" else ""
            retro = " ℞" if p['speed'] < 0 else ""
            pada = int(p['nak_frac']*4)+1
            house = planet_house(p['rashi'], lagna_rashi)
            lines.append(
                f"{emoji} *{name}*: {RASHI[p['rashi']]} {deg_str}{retro}{strength}\n"
                f"   📿 {NAKSHATRAS[p['nak']]} пада {pada} | 🏠 Дом {house}"
            )

        lines.append(f"\n*── ДОМА (Whole Sign) ──*")
        for h in range(1,13):
            r = houses[h]
            lord_pid = RASHI_LORD.get(r)
            lord_name = next((n for n,(p,_) in GRAHAS.items() if p==lord_pid), "—")
            lines.append(f"  {h}й дом: {RASHI[r]} {RASHI_EMOJI[r]} (владыка: {lord_name})")

        lines.append(f"\n*── АСПЕКТЫ (ДРИШТИ) ──*")
        aspects = calculate_parashara_aspects(pos, lagna_rashi)
        for a in aspects[:8]:
            lines.append(f"  {a}")

        lines.append(f"\n*── ЙОГИ ──*")
        yogas = calculate_yogas(pos)
        if yogas:
            for y in yogas:
                lines.append(f"  ✨ {y}")
        else:
            lines.append("  Выраженных йог не обнаружено")

        md, ad = calculate_vimshottari(pos["Луна"]["lon"], dt_utc)
        lines.append(f"\n*── ДАША ВИМШОТТАРИ ──*")
        lines.append(f"📿 Накшатра Луны: {NAKSHATRAS[pos['Луна']['nak']]}")
        lines.append(f"⏳ Маха-Даша: *{md}*")
        lines.append(f"⏳ Антар-Даша: *{ad}*")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ Ошибка расчёта: {e}"


# ── Парашара аспекты ──────────────────────────────────────────────────
def calculate_parashara_aspects(pos: dict, lagna_rashi: int = 0) -> list:
    aspects = []
    planet_list = [(n,p) for n,p in pos.items() if not n.startswith("__")]
    for name, p in planet_list:
        pid = p.get("pid",-1)
        sr = p["rashi"]
        targets = [(sr+6)%12]
        if pid == swe.MARS:    targets += [(sr+3)%12,(sr+7)%12]
        elif pid == swe.JUPITER: targets += [(sr+4)%12,(sr+8)%12]
        elif pid == swe.SATURN:  targets += [(sr+2)%12,(sr+9)%12]
        for tn, tp in planet_list:
            if tn == name: continue
            if tp["rashi"] in targets:
                e1 = GRAHAS[name][1]; e2 = GRAHAS[tn][1]
                h = planet_house(tp["rashi"], lagna_rashi)
                aspects.append(f"{e1}{name} → {e2}{tn} ({RASHI[tp['rashi']]}, дом {h})")
    return aspects


# ── Йоги ──────────────────────────────────────────────────────────────
def calculate_yogas(pos: dict) -> list:
    yogas = []
    sun_r = pos["Солнце"]["rashi"]; moon_r = pos["Луна"]["rashi"]
    jup_r = pos["Юпитер"]["rashi"]; mar_r = pos["Марс"]["rashi"]
    sat_r = pos["Сатурн"]["rashi"]; ven_r = pos["Венера"]["rashi"]
    mer_r = pos["Меркурий"]["rashi"]; rahu_r = pos["Раху"]["rashi"]
    ketu_r = pos["Кету"]["rashi"]

    if abs(moon_r-jup_r)%12 in [0,3,6,9]:
        yogas.append("Гаджа-Кесари — Луна и Юпитер в кендре (мудрость, слава)")
    if sun_r == mer_r:
        yogas.append("Буддха-Адитья — Солнце + Меркурий (интеллект, красноречие)")
    if moon_r == mar_r:
        yogas.append("Чандра-Мангала — Луна + Марс (финансовый успех)")
    if sat_r in [9,10] or UCHCHA.get(swe.SATURN)==sat_r:
        yogas.append("Шаша — Сатурн силён (власть, долголетие)")
    if ven_r in [1,6] or UCHCHA.get(swe.VENUS)==ven_r:
        yogas.append("Малавья — Венера сильна (красота, искусство, богатство)")
    if jup_r in [8,11] or UCHCHA.get(swe.JUPITER)==jup_r:
        yogas.append("Хамса — Юпитер силён (духовность, мудрость)")
    if rahu_r in [0,6]:
        yogas.append("Раху в Овне/Весах — жажда самовыражения")
    elif rahu_r in [2,8]:
        yogas.append("Раху в Близнецах/Стрельце — жажда знаний")

    lons = {n:p["lon"] for n,p in pos.items() if n not in ["Раху","Кету"] and not n.startswith("__")}
    rahu_lon = pos["Раху"]["lon"]; ketu_lon = pos["Кету"]["lon"]
    if rahu_lon > ketu_lon:
        all_b = all(ketu_lon <= l <= rahu_lon for l in lons.values())
    else:
        all_b = all(l >= rahu_lon or l <= ketu_lon for l in lons.values())
    if all_b:
        yogas.append("Кала-Сарпа — все планеты между Раху и Кету (карма, испытания)")
    return yogas


# ── Даша Вимшоттари ───────────────────────────────────────────────────
def calculate_vimshottari(moon_lon: float, birth_dt: datetime) -> tuple:
    try:
        nak_idx, nak_frac = lon_to_nakshatra(moon_lon)
        lord = NAKSHATRA_LORDS[nak_idx]
        dasha_years = DASHA_YEARS[lord]
        remaining = (1-nak_frac) * dasha_years
        lord_idx = DASHA_ORDER.index(lord)
        if birth_dt.tzinfo is None:
            birth_dt = birth_dt.replace(tzinfo=timezone.utc)
        years_since = (datetime.now(timezone.utc)-birth_dt).days/365.25
        total = remaining; cur = lord_idx
        while total < years_since:
            cur = (cur+1)%9
            total += DASHA_YEARS[DASHA_ORDER[cur]]
        md = DASHA_ORDER[cur]
        years_into = years_since - (total - DASHA_YEARS[md])
        ad = _get_antardasha(md, years_into)
        return md, ad
    except Exception:
        return "не рассчитана","не рассчитана"

def _get_antardasha(md: str, elapsed: float) -> str:
    total = DASHA_YEARS[md]; idx = DASHA_ORDER.index(md)
    acc = 0.0
    for i in range(9):
        sub = DASHA_ORDER[(idx+i)%9]
        acc += (DASHA_YEARS[sub]/120)*total
        if acc > elapsed: return sub
    return DASHA_ORDER[idx]


# ── Варшапхала ────────────────────────────────────────────────────────
def calculate_varshaphal(birth_date: str, birth_time, place: str, year: int) -> str:
    try:
        geo = geocode_place(place)
        lat, lon_geo = (geo[0],geo[1]) if geo else (0,0)
        tz_str = geo[2] if geo else "UTC"

        if birth_time and geo:
            tz = pytz.timezone(tz_str)
            birth_dt = tz.localize(datetime.strptime(f"{birth_date} {birth_time}","%d.%m.%Y %H:%M")).astimezone(pytz.utc)
        else:
            birth_dt = datetime.strptime(birth_date,"%d.%m.%Y").replace(hour=12,tzinfo=pytz.utc)

        natal_jd = dt_to_jd(birth_dt)
        swe.set_sid_mode(AYANAMSHA)
        natal_sun = sidereal_lon(swe.SUN, natal_jd)

        search_jd = swe.julday(year,1,1,12)
        varsha_jd = None
        for day in range(370):
            jt = search_jd+day
            d1 = (sidereal_lon(swe.SUN,jt)-natal_sun)%360
            d2 = (sidereal_lon(swe.SUN,jt+1)-natal_sun)%360
            if d2 < d1 and d1 > 350:
                for h in range(24):
                    jh = jt+h/24
                    e1 = (sidereal_lon(swe.SUN,jh)-natal_sun)%360
                    e2 = (sidereal_lon(swe.SUN,jh+1/24)-natal_sun)%360
                    if e2 < e1 and e1 > 355:
                        varsha_jd = jh; break
                if varsha_jd: break
        if not varsha_jd: varsha_jd = search_jd+180

        vy,vm,vd,vh = swe.revjul(varsha_jd)
        h=int(vh); m=int((vh-h)*60)
        date_str = f"{int(vd)} {MONTH_RU[int(vm)]} {int(vy)}, {h:02d}:{m:02d}"

        vpos = get_all_positions(varsha_jd, lat, lon_geo)
        vlagna = vpos.get("__lagna__")
        vlagna_rashi = vlagna["rashi"] if vlagna else 0

        wday = int(varsha_jd+1.5)%7
        varsha_lord = ["Солнце","Луна","Марс","Меркурий","Юпитер","Венера","Сатурн"][wday]

        natal_pos = get_all_positions(natal_jd, lat, lon_geo)
        nlagna = natal_pos.get("__lagna__")
        nlagna_rashi = nlagna["rashi"] if nlagna else natal_pos["Солнце"]["rashi"]
        years_el = year - birth_dt.year
        muntha_rashi = (nlagna_rashi + years_el - 1) % 12

        lines = [
            f"📅 *ВАРШАПХАЛА {year} ГОДА*\n",
            f"🌅 Солнечный возврат: {date_str}",
            f"🔱 Лагна года: {RASHI[vlagna_rashi]}\n",
            "*── ПЛАНЕТЫ ГОДА ──*",
        ]
        for name,(pid,emoji) in GRAHAS.items():
            p = vpos[name]
            deg_str = f"{int(p['deg'])}°{int((p['deg']%1)*60):02d}'"
            strength = planet_strength(pid,p['rashi']) if pid and name!="Кету" else ""
            retro = " ℞" if p['speed']<0 else ""
            house = planet_house(p['rashi'], vlagna_rashi)
            lines.append(f"{emoji} *{name}*: {RASHI[p['rashi']]} {deg_str}{retro}{strength} | Дом {house}")

        lines += [
            f"\n*── КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ ──*",
            f"👑 *Варшеша*: {varsha_lord}",
            f"🌀 *Мунтха*: {RASHI[muntha_rashi]}",
            f"🔺 *Три-раши*: {RASHI[vpos['Солнце']['rashi']]}, {RASHI[vpos['Луна']['rashi']]}, {RASHI[muntha_rashi]}",
        ]
        aspects = calculate_parashara_aspects(vpos, vlagna_rashi)
        if aspects:
            lines.append("\n*── АСПЕКТЫ ГОДА ──*")
            for a in aspects[:5]: lines.append(f"  {a}")
        yogas = calculate_yogas(vpos)
        if yogas:
            lines.append("\n*── ЙОГИ ГОДА ──*")
            for y in yogas[:4]: lines.append(f"  ✨ {y}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Ошибка Варшапхалы: {e}"


# ── Совместимость ──────────────────────────────────────────────────────
def calculate_compatibility(card1: dict, card2: dict) -> str:
    try:
        def moon_data(card):
            geo = geocode_place(card.get("birth_place",""))
            lat,lg = (geo[0],geo[1]) if geo else (0,0)
            tz_str = geo[2] if geo else "UTC"
            if card.get("birth_time") and geo:
                tz = pytz.timezone(tz_str)
                dt = tz.localize(datetime.strptime(
                    f"{card['birth_date']} {card['birth_time']}","%d.%m.%Y %H:%M")).astimezone(pytz.utc)
            else:
                dt = datetime.strptime(card["birth_date"],"%d.%m.%Y").replace(hour=12,tzinfo=pytz.utc)
            jd = dt_to_jd(dt)
            mlon = sidereal_lon(swe.MOON,jd)
            ni,_ = lon_to_nakshatra(mlon)
            ri = lon_to_rashi(mlon)
            return mlon,ni,ri

        lon1,nak1,r1 = moon_data(card1)
        lon2,nak2,r2 = moon_data(card2)
        n1=card1.get("person_name","Человек 1")
        n2=card2.get("person_name","Человек 2")
        total=0; lines=[f"💑 *СОВМЕСТИМОСТЬ*\n👤 {n1}\n👤 {n2}\n"]

        v=1 if nak1%4>=nak2%4 else 0; total+=v
        lines.append(f"1️⃣ *Варна*: {v}/1")
        vp=[(3,0),(1,9),(1,10),(5,8),(6,9),(4,3)]
        vs=2 if (r1,r2) in vp or (r2,r1) in vp else (1 if r1==r2 else 0); total+=vs
        lines.append(f"2️⃣ *Васья*: {vs}/2")
        td=(nak2-nak1)%27; ts=3 if td%3==0 else (1 if td%3==1 else 0); total+=ts
        lines.append(f"3️⃣ *Тара*: {ts}/3")
        y1,y2=YONI[nak1],YONI[nak2]; ys=4 if y1==y2 else 2; total+=ys
        lines.append(f"4️⃣ *Йони* ({y1}/{y2}): {ys}/4")
        l1=RASHI_LORD.get(r1,swe.MOON); l2=RASHI_LORD.get(r2,swe.MOON)
        f1=PLANET_FRIENDS.get(l1,[]); f2=PLANET_FRIENDS.get(l2,[])
        gs=5 if (l1 in f2 and l2 in f1) else (3 if (l1 in f2 or l2 in f1) else 1); total+=gs
        lines.append(f"5️⃣ *Грахамайтри*: {gs}/5")
        g1,g2=GANA[nak1],GANA[nak2]; gn=["Дева","Человек","Ракшаса"]
        gans=6 if g1==g2 else (3 if abs(g1-g2)==1 else 0); total+=gans
        lines.append(f"6️⃣ *Гана* ({gn[g1]}/{gn[g2]}): {gans}/6")
        bd=(r2-r1)%12; bs=0 if bd in [6,8,5,9] else 7; total+=bs
        lines.append(f"7️⃣ *Бхакута*: {bs}/7")
        na1,na2=NADI[nak1],NADI[nak2]; nn=["Ади","Мадхья","Антья"]
        ns=0 if na1==na2 else 8; total+=ns
        lines.append(f"8️⃣ *Нади* ({nn[na1]}/{nn[na2]}): {ns}/8")

        pct=int(total/36*100)
        verd="🟢 Отличная совместимость" if pct>=75 else ("🟡 Хорошая совместимость" if pct>=60 else ("🟠 Средняя совместимость" if pct>=40 else "🔴 Низкая совместимость"))
        lines += [f"\n*── ИТОГ ──*", f"🏆 *Сумма Кута: {total}/36 ({pct}%)*", verd]

        # Доши
        doshas = []
        if ns==0:  doshas.append("⚠️ *Нади-доша* — совпадение Нади (8 очков). Требует внимания: риски со здоровьем потомства. Можно нейтрализовать специальными пуджами.")
        if bs==0:  doshas.append("⚠️ *Бхакута-доша* — неблагоприятное соотношение Лун. Может влиять на эмоциональную совместимость.")
        if gans==0: doshas.append("⚠️ *Гана-доша* — разные Ганы (Ракшаса/Дева). Возможны различия в темпераменте.")
        if doshas:
            lines.append("\n*── ДОШИ ──*")
            for d in doshas: lines.append(d)

        # Развёрнутый анализ
        lines.append("\n*── ПОДРОБНЫЙ АНАЛИЗ ──*")

        # Анализ накшатр
        lines.append(f"\n🌙 *Накшатры Луны:*")
        lines.append(f"  {n1}: {NAKSHATRAS[nak1]} (пада {int(((lon1%360)%(360/27))/(360/27/4))+1})")
        lines.append(f"  {n2}: {NAKSHATRAS[nak2]} (пада {int(((lon2%360)%(360/27))/(360/27/4))+1})")

        # Владыки накшатр
        lord1_nak = NAKSHATRA_LORDS[nak1]
        lord2_nak = NAKSHATRA_LORDS[nak2]
        lines.append(f"\n🪐 *Владыки накшатр:*")
        lines.append(f"  {n1}: {lord1_nak}")
        lines.append(f"  {n2}: {lord2_nak}")

        # Анализ Рашей Луны
        lines.append(f"\n♈ *Раши Луны:*")
        lines.append(f"  {n1}: {RASHI[r1]}")
        lines.append(f"  {n2}: {RASHI[r2]}")

        # Гана совместимость развёрнуто
        gana_desc = {
            (0,0): "Оба Девы — мягкие, духовные натуры. Глубокая гармония.",
            (1,1): "Оба Человека — земной, практичный союз. Хорошее взаимопонимание.",
            (2,2): "Оба Ракшаса — страстные, интенсивные. Сильная связь при наличии уважения.",
            (0,1): "Дева + Человек — мягкость встречает практичность. Требует уважения различий.",
            (1,0): "Человек + Дева — практик + духовный. Баланс возможен.",
            (0,2): "Дева + Ракшаса — сложная комбинация. Требует работы над отношениями.",
            (2,0): "Ракшаса + Дева — противоположности. Взаимное притяжение, но и напряжение.",
            (1,2): "Человек + Ракшаса — умеренная совместимость. Важно взаимное уважение.",
            (2,1): "Ракшаса + Человек — умеренная совместимость. Важно взаимное уважение.",
        }
        lines.append(f"\n🔮 *Анализ Ганы:*")
        lines.append(f"  {gana_desc.get((g1,g2), 'Смешанная совместимость.')}")

        # Нади развёрнуто
        lines.append(f"\n💫 *Нади — энергетическая совместимость:*")
        if ns == 8:
            lines.append(f"  ✅ Разные Нади ({nn[na1]} и {nn[na2]}) — отличная энергетическая совместимость. Взаимное притяжение и дополнение.")
        else:
            lines.append(f"  ⚠️ Одинаковая Нади ({nn[na1]}) — Нади-доша. По традиции требует особого внимания. Рекомендуется консультация астролога.")

        # Рекомендации
        lines.append(f"\n📌 *Рекомендации:*")
        if pct >= 75:
            lines.append("  Союз благоприятен. Звёзды поддерживают эти отношения. Возможно проведение свадьбы в благоприятную Мухурту.")
        elif pct >= 60:
            lines.append("  Хороший союз с небольшими областями для работы. Рекомендуется Мухурта для свадьбы и при необходимости нейтрализация дош.")
        elif pct >= 40:
            lines.append("  Средняя совместимость. Отношения возможны при осознанной работе обоих партнёров. Важна Мухурта и нейтрализация дош.")
        else:
            lines.append("  Низкая астрологическая совместимость. Рекомендуется детальная консультация астролога и специальные пуджи.")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ Ошибка совместимости: {e}"


# ── Мухурта ───────────────────────────────────────────────────────────
def calculate_muhurta(event_type: str, start_date: str, days_ahead: int=30) -> str:
    try:
        ek = event_type.lower()
        gn = MUHURTA_NAKSHATRAS.get(ek, MUHURTA_NAKSHATRAS["бизнес"])
        gd = MUHURTA_WEEKDAYS.get(ek, MUHURTA_WEEKDAYS["бизнес"])
        start = datetime.strptime(start_date,"%d.%m.%Y")
        results=[]
        for d in range(days_ahead):
            dt = start+timedelta(days=d)
            jd = swe.julday(dt.year,dt.month,dt.day,12)
            swe.set_sid_mode(AYANAMSHA)
            r,_ = swe.calc_ut(jd,swe.MOON,swe.FLG_SIDEREAL)
            mlon = r[0]%360
            ni,_ = lon_to_nakshatra(mlon)
            mr = lon_to_rashi(mlon)
            wd = dt.weekday()
            if ni in gn and wd in gd and mr not in [7,9]:
                results.append({"date":dt,"nak":ni,"rashi":mr,"weekday":wd})

        en={"свадьба":"Свадьба","роспись":"Роспись","бизнес":"Бизнес",
            "путешествие":"Путешествие","операция":"Операция",
            "красота":"Операция красоты","покупка":"Крупная покупка",
            "переезд":"Переезд","лечение":"Лечение"}
        lines=[f"🗓 *МУХУРТА — {en.get(ek,event_type).upper()}*\n"]
        if not results:
            lines.append("Благоприятных дат не найдено. Расширь период.")
            return "\n".join(lines)
        lines.append(f"✅ Найдено {len(results)} дат:\n")
        for r in results[:10]:
            dt=r["date"]
            lines.append(
                f"⭐ *{dt.day} {MONTH_RU[dt.month]} {dt.year}* ({WEEKDAY_RU[r['weekday']]})\n"
                f"   🌙 {RASHI[r['rashi']]} / {NAKSHATRAS[r['nak']]}"
            )
        if len(results)>10: lines.append(f"\n...и ещё {len(results)-10} дат")
        lines.append("\n💡 _Для точного времени уточни у астролога_")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Ошибка Мухурты: {e}"


# ── Отслеживание событий для рассылки ─────────────────────────────────
def get_transit_events() -> list:
    """
    Проверяет текущие транзитные события для рассылки.
    Возвращает список событий: смена знака, ретроград, соединения.
    """
    events = []
    jd_now = now_jd()
    jd_prev = jd_now - 1  # сутки назад

    pos_now  = get_all_positions(jd_now)
    pos_prev = get_all_positions(jd_prev)

    for name, (pid, emoji) in GRAHAS.items():
        if pid is None: continue
        pn = pos_now[name]; pp = pos_prev[name]

        # Смена знака
        if pn["rashi"] != pp["rashi"]:
            events.append({
                "type": "sign_change",
                "planet": name,
                "emoji": emoji,
                "from_sign": RASHI[pp["rashi"]],
                "to_sign":   RASHI[pn["rashi"]],
                "desc": f"{emoji} *{name}* вошёл в *{RASHI[pn['rashi']]}*"
            })

        # Начало ретрограда
        if pn["speed"] < 0 and pp["speed"] >= 0:
            events.append({
                "type": "retrograde_start",
                "planet": name,
                "emoji": emoji,
                "sign": RASHI[pn["rashi"]],
                "desc": f"{emoji} *{name}* стал ретроградным в *{RASHI[pn['rashi']]}* ℞"
            })

        # Конец ретрограда
        if pn["speed"] >= 0 and pp["speed"] < 0:
            events.append({
                "type": "retrograde_end",
                "planet": name,
                "emoji": emoji,
                "sign": RASHI[pn["rashi"]],
                "desc": f"{emoji} *{name}* стал прямым в *{RASHI[pn['rashi']]}*"
            })

    # Соединения (юти) — новые за последние сутки
    def get_conjunctions(pos):
        conj = set()
        names = [n for n in pos if not n.startswith("__")]
        for i in range(len(names)):
            for j in range(i+1,len(names)):
                if pos[names[i]]["rashi"] == pos[names[j]]["rashi"]:
                    conj.add((names[i],names[j]))
        return conj

    conj_now  = get_conjunctions(pos_now)
    conj_prev = get_conjunctions(pos_prev)
    new_conj  = conj_now - conj_prev

    for n1,n2 in new_conj:
        e1 = GRAHAS[n1][1]; e2 = GRAHAS[n2][1]
        rashi = pos_now[n1]["rashi"]
        events.append({
            "type": "conjunction",
            "planets": (n1,n2),
            "sign": RASHI[rashi],
            "desc": f"{e1}{n1} + {e2}{n2} — соединение в *{RASHI[rashi]}*"
        })

    return events


def build_transit_broadcast(event: dict) -> str:
    """
    Строит текст рассылки для группы по транзитному событию.
    Общий прогноз + прогноз для каждого знака.
    """
    planet = event.get("planet","")
    emoji  = event.get("emoji","🪐")
    sign   = event.get("to_sign") or event.get("sign","")
    etype  = event["type"]

    if etype == "sign_change":
        header = f"{emoji} *{planet} в {sign}*\n"
        header += f"_{planet} переходит из {event['from_sign']} в {sign}_\n"
    elif etype == "retrograde_start":
        header = f"{emoji} *{planet} ℞ в {sign}*\n"
        header += f"_{planet} становится ретроградным в {sign}_\n"
    elif etype == "retrograde_end":
        header = f"{emoji} *{planet} прямой в {sign}*\n"
        header += f"_{planet} завершает ретроград в {sign}_\n"
    elif etype == "conjunction":
        n1,n2 = event["planets"]
        e1=GRAHAS[n1][1]; e2=GRAHAS[n2][1]
        header = f"{e1}{e2} *Соединение {n1} и {n2} в {sign}*\n"
        planet = f"{n1} и {n2}"
    else:
        header = event.get("desc","Транзитное событие")

    # Прогноз для каждого знака
    sign_forecasts = []
    for i, rashi_name in enumerate(RASHI):
        rashi_emoji = RASHI_EMOJI[i]
        # Определяем в каком доме происходит транзит для данного лагна-раши
        if sign in RASHI:
            transit_rashi_idx = RASHI.index(sign)
            house = planet_house(transit_rashi_idx, i)
            sign_forecasts.append(
                f"{rashi_emoji} *{rashi_name}*\n"
                f"   {emoji} {planet} активирует *{house}-й дом*"
            )

    result = header + "\n" + "\n".join(sign_forecasts)
    return result
