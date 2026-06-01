"""
╔══════════════════════════════════════╗
║   ДЖЙОТИШ РАСЧЁТЫ — jyotish.py      ║
╚══════════════════════════════════════╝
Swiss Ephemeris (pyswisseph), аянамша Лахири.
"""

import swisseph as swe
from datetime import datetime, timezone, timedelta
import math

swe.set_ephe_path("")
AYANAMSHA = swe.SIDM_LAHIRI

# ── Русские названия ───────────────────────────────────────────────────
GRAHAS = {
    "Солнце":   (swe.SUN,      "☀️"),
    "Луна":     (swe.MOON,     "🌙"),
    "Марс":     (swe.MARS,     "🔴"),
    "Меркурий": (swe.MERCURY,  "🟡"),
    "Юпитер":  (swe.JUPITER,  "🟠"),
    "Венера":  (swe.VENUS,    "⚪"),
    "Сатурн":  (swe.SATURN,   "🟤"),
    "Раху":    (swe.MEAN_NODE,"☊"),
    "Кету":    (None,          "☋"),
}

RASHI = [
    "Овен", "Телец", "Близнецы", "Рак",
    "Лев", "Дева", "Весы", "Скорпион",
    "Стрелец", "Козерог", "Водолей", "Рыбы",
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

# Уччха (экзальтация) по раши-индексу
UCHCHA = {
    swe.SUN:0, swe.MOON:1, swe.MARS:9, swe.MERCURY:5,
    swe.JUPITER:3, swe.VENUS:11, swe.SATURN:6,
}
NICHA = {p:(d+6)%12 for p,d in UCHCHA.items()}

# Домицили планет
DOMICILE = {
    swe.SUN:[4], swe.MOON:[3], swe.MARS:[0,7],
    swe.MERCURY:[2,5], swe.JUPITER:[8,11],
    swe.VENUS:[1,6], swe.SATURN:[9,10],
}

# Парашара аспекты (дришти): планета -> список раши-смещений
PARASHARA_ASPECTS = {
    "все": [6],           # все планеты аспектируют 7й дом
    swe.MARS:    [3,6,7], # Марс: 4,7,8
    swe.JUPITER: [4,6,8], # Юпитер: 5,7,9
    swe.SATURN:  [2,6,9], # Сатурн: 3,7,10
}

# Кута-анализ совместимости
KUTA_NAMES = [
    "Варна","Васья","Тара","Йони","Грахамайтри",
    "Гана","Бхакута","Нади",
]
KUTA_MAX = [1, 2, 3, 4, 5, 6, 7, 8]

# Гана накшатр (0=Дева, 1=Человек, 2=Ракшаса)
GANA = [
    0,2,0,0,0,2,0,0,2,2,
    1,0,0,2,0,1,1,2,2,2,
    0,1,2,1,1,0,0,
]

# Йони накшатр (символ животного)
YONI = [
    "Конь","Слон","Овца","Змея","Змея","Собака","Кошка","Баран",
    "Кошка","Крыса","Лев","Бык","Буйвол","Тигр","Буйвол","Тигр",
    "Заяц","Олень","Собака","Обезьяна","Мангуст","Обезьяна","Лев",
    "Лошадь","Лев","Корова","Слон",
]

# Нади (0=Ади, 1=Мадхья, 2=Антья)
NADI = [
    0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,
]

# Владыки раши для Грахамайтри
RASHI_LORD = {
    0:swe.MARS, 1:swe.VENUS, 2:swe.MERCURY, 3:swe.MOON,
    4:swe.SUN, 5:swe.MERCURY, 6:swe.VENUS, 7:swe.MARS,
    8:swe.JUPITER, 9:swe.SATURN, 10:swe.SATURN, 11:swe.JUPITER,
}

PLANET_FRIENDS = {
    swe.SUN:     [swe.MOON, swe.MARS, swe.JUPITER],
    swe.MOON:    [swe.SUN, swe.MERCURY],
    swe.MARS:    [swe.SUN, swe.MOON, swe.JUPITER],
    swe.MERCURY: [swe.SUN, swe.VENUS],
    swe.JUPITER: [swe.SUN, swe.MOON, swe.MARS],
    swe.VENUS:   [swe.MERCURY, swe.SATURN],
    swe.SATURN:  [swe.MERCURY, swe.VENUS],
}

# Благоприятные накшатры для Мухурты по типу события
MUHURTA_NAKSHATRAS = {
    "свадьба":     [2,3,6,7,11,12,13,20,21,22,25,26],
    "роспись":     [2,3,6,7,11,12,13,20,21,22,25,26],
    "бизнес":      [0,2,3,6,7,10,11,12,20,21,22,25],
    "путешествие": [0,2,5,6,7,11,12,20,21,22,23,25],
    "операция":    [2,7,10,11,12,20,21,22,25,26],
    "красота":     [1,2,3,6,7,11,12,13,14,25,26],
    "покупка":     [0,2,3,6,7,10,11,12,20,21,22,25],
    "переезд":     [0,2,3,6,7,11,12,20,21,22,25],
    "лечение":     [2,7,10,11,12,20,21,22,25,26],
}

# Благоприятные дни недели для событий (0=пн ... 6=вс)
MUHURTA_WEEKDAYS = {
    "свадьба":     [0,2,3,4],
    "роспись":     [0,2,3,4],
    "бизнес":      [0,2,3,4,5],
    "путешествие": [0,1,2,3,4],
    "операция":    [0,2,3],
    "красота":     [0,2,3,4,5],
    "покупка":     [0,2,3,4,5],
    "переезд":     [0,2,3,4],
    "лечение":     [0,2,3,5],
}

WEEKDAY_RU = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
MONTH_RU = ["","января","февраля","марта","апреля","мая","июня",
            "июля","августа","сентября","октября","ноября","декабря"]


# ── Базовые функции ────────────────────────────────────────────────────
def now_jd() -> float:
    now = datetime.now(timezone.utc)
    return swe.julday(now.year, now.month, now.day,
                      now.hour + now.minute/60.0 + now.second/3600.0)


def dt_to_jd(dt: datetime) -> float:
    return swe.julday(dt.year, dt.month, dt.day,
                      dt.hour + dt.minute/60.0 + dt.second/3600.0)


def sidereal_longitude(planet_id: int, jd: float) -> float:
    swe.set_sid_mode(AYANAMSHA)
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, planet_id, flags)
    return result[0] % 360


def longitude_to_rashi_deg(lon: float) -> tuple:
    return int(lon // 30), lon % 30


def longitude_to_nakshatra(lon: float) -> tuple:
    span = 360/27
    idx = int(lon / span) % 27
    frac = (lon % span) / span
    return idx, frac


def planet_strength(planet_id: int, rashi_idx: int) -> str:
    if UCHCHA.get(planet_id) == rashi_idx:
        return " ⬆️ уччха"
    if NICHA.get(planet_id) == rashi_idx:
        return " ⬇️ нича"
    if rashi_idx in DOMICILE.get(planet_id, []):
        return " 🏠 сваграха"
    return ""


def get_all_positions(jd: float) -> dict:
    """Возвращает словарь {название: (lon, rashi_idx, deg, nak_idx, nak_frac, speed)}"""
    swe.set_sid_mode(AYANAMSHA)
    positions = {}
    rahu_lon = sidereal_longitude(swe.MEAN_NODE, jd)

    for name, (pid, emoji) in GRAHAS.items():
        if name == "Кету":
            lon = (rahu_lon + 180) % 360
            speed = 0
        else:
            flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
            result, _ = swe.calc_ut(jd, pid, flags)
            lon = result[0] % 360
            speed = result[3]
        r, d = longitude_to_rashi_deg(lon)
        ni, nf = longitude_to_nakshatra(lon)
        positions[name] = {"lon":lon,"rashi":r,"deg":d,"nak":ni,"nak_frac":nf,"speed":speed,"pid":pid if name!="Кету" else -1}
    return positions


# ── Текущие транзиты ───────────────────────────────────────────────────
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

    # Юти (соединения)
    rashi_groups = {}
    for name, p in pos.items():
        rashi_groups.setdefault(p['rashi'], []).append(name)
    for ri, planets in rashi_groups.items():
        if len(planets) >= 2:
            notes.append(f"🔗 Юти в {RASHI[ri]}: {' + '.join(planets)}")

    # Оппозиции и трины
    pl = list(pos.items())
    for i in range(len(pl)):
        for j in range(i+1, len(pl)):
            n1, p1 = pl[i]
            n2, p2 = pl[j]
            diff = abs(p1['lon']-p2['lon']) % 360
            if diff > 180: diff = 360 - diff
            if 170 <= diff <= 190:
                notes.append(f"⟺ Оппозиция: {n1} — {n2}")
            elif 115 <= diff <= 125:
                notes.append(f"△ Трин: {n1} — {n2}")

    return "\n".join(notes[:6]) if notes else ""


# ── Натальная карта ────────────────────────────────────────────────────
def calculate_natal_basics(birth_date: str, birth_time, place: str) -> dict:
    try:
        if birth_time:
            dt = datetime.strptime(f"{birth_date} {birth_time}", "%d.%m.%Y %H:%M")
        else:
            dt = datetime.strptime(birth_date, "%d.%m.%Y").replace(hour=12)

        jd = dt_to_jd(dt)
        pos = get_all_positions(jd)

        sun_rashi = pos["Солнце"]["rashi"]
        moon_rashi = pos["Луна"]["rashi"]
        moon_nak = pos["Луна"]["nak"]
        moon_nak_frac = pos["Луна"]["nak_frac"]

        mahadasha, antardasha = calculate_vimshottari(pos["Луна"]["lon"], dt)

        return {
            "sun_sign": RASHI[sun_rashi],
            "moon_sign": RASHI[moon_rashi],
            "moon_nakshatra": NAKSHATRAS[moon_nak],
            "lagna": "Требует точного времени" if not birth_time else RASHI[sun_rashi],
            "mahadasha": mahadasha,
            "antardasha": antardasha,
        }
    except Exception as e:
        return {"error": str(e)}


def calculate_full_natal(birth_date: str, birth_time, place: str) -> str:
    """Полный разбор натальной карты."""
    try:
        if birth_time:
            dt = datetime.strptime(f"{birth_date} {birth_time}", "%d.%m.%Y %H:%M")
        else:
            dt = datetime.strptime(birth_date, "%d.%m.%Y").replace(hour=12)

        jd = dt_to_jd(dt)
        swe.set_sid_mode(AYANAMSHA)
        pos = get_all_positions(jd)

        lines = [f"🔱 *НАТАЛЬНАЯ КАРТА*\n📅 {birth_date}  ⏰ {birth_time or 'не указано'}  📍 {place}\n"]

        # Планеты по знакам
        lines.append("*── ПЛАНЕТЫ ──*")
        for name, (pid, emoji) in GRAHAS.items():
            p = pos[name]
            deg_str = f"{int(p['deg'])}°{int((p['deg']%1)*60):02d}'"
            strength = planet_strength(pid, p['rashi']) if pid and name != "Кету" else ""
            retro = " ℞" if p['speed'] < 0 else ""
            pada = int(p['nak_frac']*4)+1
            lines.append(
                f"{emoji} *{name}*: {RASHI[p['rashi']]} {deg_str}{retro}{strength}\n"
                f"   {NAKSHATRAS[p['nak']]}, пада {pada}"
            )

        # Парашара аспекты
        lines.append("\n*── АСПЕКТЫ (ДРИШТИ) ──*")
        aspects = calculate_parashara_aspects(pos)
        for asp in aspects[:8]:
            lines.append(f"  {asp}")

        # Йоги
        lines.append("\n*── ЙОГИ ──*")
        yogas = calculate_yogas(pos)
        if yogas:
            for y in yogas[:6]:
                lines.append(f"  ✨ {y}")
        else:
            lines.append("  Выраженных йог не обнаружено")

        # Даша
        mahadasha, antardasha = calculate_vimshottari(pos["Луна"]["lon"], dt)
        moon_nak = NAKSHATRAS[pos["Луна"]["nak"]]
        lines.append(f"\n*── ДАША ВИМШОТТАРИ ──*")
        lines.append(f"📿 Накшатра Луны: {moon_nak}")
        lines.append(f"⏳ Маха-Даша: *{mahadasha}*")
        lines.append(f"⏳ Антар-Даша: *{antardasha}*")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ Ошибка расчёта: {e}"


def calculate_parashara_aspects(pos: dict) -> list:
    """Рассчитывает Парашара аспекты."""
    aspects = []
    planet_list = [(n, p) for n, p in pos.items()]

    for name, p in planet_list:
        pid = p.get("pid", -1)
        source_rashi = p["rashi"]

        # Все планеты аспектируют 7й дом
        aspect_rashis = [(source_rashi + 6) % 12]

        # Специальные аспекты
        if pid == swe.MARS:
            aspect_rashis += [(source_rashi + 3) % 12, (source_rashi + 7) % 12]
        elif pid == swe.JUPITER:
            aspect_rashis += [(source_rashi + 4) % 12, (source_rashi + 8) % 12]
        elif pid == swe.SATURN:
            aspect_rashis += [(source_rashi + 2) % 12, (source_rashi + 9) % 12]

        for target_name, tp in planet_list:
            if target_name == name:
                continue
            if tp["rashi"] in aspect_rashis:
                emoji1 = GRAHAS[name][1]
                emoji2 = GRAHAS[target_name][1]
                aspects.append(f"{emoji1} {name} аспектирует {emoji2} {target_name} ({RASHI[tp['rashi']]})")

    return aspects


def calculate_yogas(pos: dict) -> list:
    """Определяет основные йоги."""
    yogas = []
    sun_r = pos["Солнце"]["rashi"]
    moon_r = pos["Луна"]["rashi"]
    jup_r = pos["Юпитер"]["rashi"]
    mar_r = pos["Марс"]["rashi"]
    sat_r = pos["Сатурн"]["rashi"]
    ven_r = pos["Венера"]["rashi"]
    mer_r = pos["Меркурий"]["rashi"]
    rahu_r = pos["Раху"]["rashi"]
    ketu_r = pos["Кету"]["rashi"]

    # Гаджа-Кесари йога — Луна и Юпитер в кендре (1,4,7,10)
    diff = abs(moon_r - jup_r) % 12
    if diff in [0, 3, 6, 9]:
        yogas.append("Гаджа-Кесари — Луна и Юпитер в кендре (мудрость, слава)")

    # Буддха-Адитья йога — Солнце и Меркурий в одном знаке
    if sun_r == mer_r:
        yogas.append("Буддха-Адитья — Солнце + Меркурий (интеллект, красноречие)")

    # Чандра-Мангала йога — Луна и Марс вместе
    if moon_r == mar_r:
        yogas.append("Чандра-Мангала — Луна + Марс (финансовый успех)")

    # Шаша йога — Сатурн в уччха или в своём знаке в кендре
    if sat_r in [9, 10] or UCHCHA.get(swe.SATURN) == sat_r:
        yogas.append("Шаша — Сатурн силён в кендре (власть, долголетие)")

    # Малавья йога — Венера в уччха или своём знаке в кендре
    if ven_r in [1, 6] or UCHCHA.get(swe.VENUS) == ven_r:
        yogas.append("Малавья — Венера сильна (красота, искусство, богатство)")

    # Хамса йога — Юпитер в уччха или своём знаке в кендре
    if jup_r in [8, 11] or UCHCHA.get(swe.JUPITER) == jup_r:
        yogas.append("Хамса — Юпитер силён (духовность, мудрость, процветание)")

    # Раху-Кету ось в 1-7 или 4-10
    rk_diff = abs(rahu_r - ketu_r) % 12
    if rk_diff == 6:
        if rahu_r in [0, 6]:
            yogas.append("Раху в Овне/Весах — сильное желание самовыражения")
        elif rahu_r in [2, 8]:
            yogas.append("Раху в Близнецах/Стрельце — жажда знаний и путешествий")

    # Кала-Сарпа йога — все планеты между Раху и Кету
    lons = {n: p["lon"] for n, p in pos.items() if n not in ["Раху", "Кету"]}
    rahu_lon = pos["Раху"]["lon"]
    ketu_lon = pos["Кету"]["lon"]
    if rahu_lon > ketu_lon:
        all_between = all(ketu_lon <= l <= rahu_lon for l in lons.values())
    else:
        all_between = all(l >= rahu_lon or l <= ketu_lon for l in lons.values())
    if all_between:
        yogas.append("Кала-Сарпа — все планеты между Раху и Кету (карма, испытания)")

    return yogas


# ── Даша Вимшоттари ───────────────────────────────────────────────────
def calculate_vimshottari(moon_lon: float, birth_dt: datetime) -> tuple:
    try:
        nak_idx, nak_frac = longitude_to_nakshatra(moon_lon)
        lord = NAKSHATRA_LORDS[nak_idx]
        dasha_years = DASHA_YEARS[lord]

        elapsed_years = nak_frac * dasha_years
        remaining_years = dasha_years - elapsed_years

        lord_idx = DASHA_ORDER.index(lord)
        if birth_dt.tzinfo is None:
            birth_dt = birth_dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        years_since_birth = (now - birth_dt).days / 365.25

        total = remaining_years
        current_idx = lord_idx

        while total < years_since_birth:
            current_idx = (current_idx + 1) % 9
            total += DASHA_YEARS[DASHA_ORDER[current_idx]]

        mahadasha_lord = DASHA_ORDER[current_idx]
        years_into = years_since_birth - (total - DASHA_YEARS[mahadasha_lord])
        antardasha = _get_antardasha(mahadasha_lord, years_into)

        return mahadasha_lord, antardasha
    except Exception:
        return "не рассчитана", "не рассчитана"


def _get_antardasha(mahadasha_lord: str, years_elapsed: float) -> str:
    total = DASHA_YEARS[mahadasha_lord]
    lord_idx = DASHA_ORDER.index(mahadasha_lord)
    accumulated = 0.0
    for i in range(9):
        sub_lord = DASHA_ORDER[(lord_idx+i) % 9]
        sub_dur = (DASHA_YEARS[sub_lord] / 120) * total
        accumulated += sub_dur
        if accumulated > years_elapsed:
            return sub_lord
    return DASHA_ORDER[lord_idx]


# ── Варшапхала (годовой гороскоп) ─────────────────────────────────────
def calculate_varshaphal(birth_date: str, birth_time, place: str, year: int) -> str:
    """Полный расчёт Варшапхалы."""
    try:
        if birth_time:
            birth_dt = datetime.strptime(f"{birth_date} {birth_time}", "%d.%m.%Y %H:%M")
        else:
            birth_dt = datetime.strptime(birth_date, "%d.%m.%Y").replace(hour=12)

        natal_jd = dt_to_jd(birth_dt)
        swe.set_sid_mode(AYANAMSHA)

        # Натальное положение Солнца
        natal_sun = sidereal_longitude(swe.SUN, natal_jd)

        # Ищем момент когда Солнце возвращается на натальную позицию в указанном году
        # Начинаем поиск с 1 января указанного года
        search_dt = datetime(year, 1, 1, 12, 0)
        search_jd = dt_to_jd(search_dt)

        # Итерируем по дням пока не найдём солнечный возврат
        varsha_jd = None
        for day in range(370):
            jd_try = search_jd + day
            sun_lon = sidereal_longitude(swe.SUN, jd_try)
            sun_lon_next = sidereal_longitude(swe.SUN, jd_try + 1)

            # Проверяем пересечение натальной позиции Солнца
            diff = (sun_lon - natal_sun) % 360
            diff_next = (sun_lon_next - natal_sun) % 360

            if diff_next < diff and diff > 350:
                # Нашли примерный день — уточняем до часа
                for hour in range(24):
                    jd_h = jd_try + hour/24.0
                    s1 = sidereal_longitude(swe.SUN, jd_h)
                    s2 = sidereal_longitude(swe.SUN, jd_h + 1/24.0)
                    d1 = (s1 - natal_sun) % 360
                    d2 = (s2 - natal_sun) % 360
                    if d2 < d1 and d1 > 355:
                        varsha_jd = jd_h
                        break
                if varsha_jd:
                    break

        if not varsha_jd:
            varsha_jd = search_jd + 180  # fallback

        # Дата Варшапхалы
        varsha_year, varsha_month, varsha_day, varsha_hour = swe.revjul(varsha_jd)
        h = int(varsha_hour)
        m = int((varsha_hour - h) * 60)
        varsha_date_str = f"{int(varsha_day)} {MONTH_RU[int(varsha_month)]} {int(varsha_year)}, {h:02d}:{m:02d}"

        # Позиции планет на момент Варшапхалы
        varsha_pos = get_all_positions(varsha_jd)

        # Варшеша — планета года (владыка дня недели солнечного возврата)
        weekday = int(varsha_jd + 1.5) % 7  # 0=вс, 1=пн...
        weekday_lords = ["Солнце","Луна","Марс","Меркурий","Юпитер","Венера","Сатурн"]
        varsha_lord = weekday_lords[weekday]

        # Мунтха — продвигается на 1 знак в год от Лагны натальной
        birth_year = birth_dt.year
        years_elapsed = year - birth_year
        # Упрощённо: Мунтха начинается с Лагны и движется по 1 знаку в год
        natal_pos = get_all_positions(natal_jd)
        sun_natal_rashi = natal_pos["Солнце"]["rashi"]
        muntha_rashi = (sun_natal_rashi + years_elapsed - 1) % 12

        lines = [
            f"📅 *ВАРШАПХАЛА {year} ГОДА*\n",
            f"🌅 Солнечный возврат: {varsha_date_str}\n",
            f"*── ПЛАНЕТЫ ГОДА ──*",
        ]

        for name, (pid, emoji) in GRAHAS.items():
            p = varsha_pos[name]
            deg_str = f"{int(p['deg'])}°{int((p['deg']%1)*60):02d}'"
            strength = planet_strength(pid, p['rashi']) if pid and name != "Кету" else ""
            retro = " ℞" if p['speed'] < 0 else ""
            lines.append(f"{emoji} *{name}*: {RASHI[p['rashi']]} {deg_str}{retro}{strength}")

        lines.append(f"\n*── КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ ──*")
        lines.append(f"👑 *Варшеша (планета года)*: {varsha_lord}")
        lines.append(f"🌀 *Мунтха*: {RASHI[muntha_rashi]}")

        # Три-раши (три знака года)
        tri_rashi = [
            RASHI[varsha_pos["Солнце"]["rashi"]],
            RASHI[varsha_pos["Луна"]["rashi"]],
            RASHI[muntha_rashi]
        ]
        lines.append(f"🔺 *Три-раши*: {', '.join(tri_rashi)}")

        # Аспекты года
        lines.append(f"\n*── АСПЕКТЫ ГОДА ──*")
        aspects = calculate_parashara_aspects(varsha_pos)
        for asp in aspects[:5]:
            lines.append(f"  {asp}")

        # Йоги года
        yogas = calculate_yogas(varsha_pos)
        if yogas:
            lines.append(f"\n*── ЙОГИ ГОДА ──*")
            for y in yogas[:4]:
                lines.append(f"  ✨ {y}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Ошибка расчёта Варшапхалы: {e}"


# ── Совместимость (Кута-анализ) ────────────────────────────────────────
def calculate_compatibility(card1: dict, card2: dict) -> str:
    """Кута-анализ совместимости двух натальных карт."""
    try:
        # Получаем позиции Луны обоих
        def get_moon_data(card):
            if card.get("birth_time"):
                dt = datetime.strptime(f"{card['birth_date']} {card['birth_time']}", "%d.%m.%Y %H:%M")
            else:
                dt = datetime.strptime(card["birth_date"], "%d.%m.%Y").replace(hour=12)
            jd = dt_to_jd(dt)
            moon_lon = sidereal_longitude(swe.MOON, jd)
            nak_idx, _ = longitude_to_nakshatra(moon_lon)
            rashi_idx = int(moon_lon // 30)
            return moon_lon, nak_idx, rashi_idx

        lon1, nak1, rashi1 = get_moon_data(card1)
        lon2, nak2, rashi2 = get_moon_data(card2)

        name1 = card1.get("person_name", "Человек 1")
        name2 = card2.get("person_name", "Человек 2")

        total_score = 0
        max_score = 36
        lines = [f"💑 *СОВМЕСТИМОСТЬ*\n👤 {name1}\n👤 {name2}\n"]

        # 1. Варна (1 очко)
        varna_score = 1 if nak1 % 4 >= nak2 % 4 else 0
        total_score += varna_score
        lines.append(f"1️⃣ *Варна*: {varna_score}/1")

        # 2. Васья (2 очка)
        vasya_pairs = [(3,0),(1,9),(1,10),(5,8),(6,9),(4,3)]
        vasya_score = 2 if (rashi1,rashi2) in vasya_pairs or (rashi2,rashi1) in vasya_pairs else (1 if rashi1==rashi2 else 0)
        total_score += vasya_score
        lines.append(f"2️⃣ *Васья*: {vasya_score}/2")

        # 3. Тара (3 очка)
        tara_diff = (nak2 - nak1) % 27
        tara_score = 3 if tara_diff % 3 == 0 else (1 if tara_diff % 3 == 1 else 0)
        total_score += tara_score
        lines.append(f"3️⃣ *Тара*: {tara_score}/3")

        # 4. Йони (4 очка)
        y1, y2 = YONI[nak1], YONI[nak2]
        yoni_score = 4 if y1 == y2 else (2 if y1 != y2 else 0)
        total_score += yoni_score
        lines.append(f"4️⃣ *Йони* ({y1}/{y2}): {yoni_score}/4")

        # 5. Грахамайтри (5 очков)
        lord1 = RASHI_LORD.get(rashi1, swe.MOON)
        lord2 = RASHI_LORD.get(rashi2, swe.MOON)
        friends1 = PLANET_FRIENDS.get(lord1, [])
        friends2 = PLANET_FRIENDS.get(lord2, [])
        mutual = lord1 in friends2 and lord2 in friends1
        one_way = lord1 in friends2 or lord2 in friends1
        graha_score = 5 if mutual else (3 if one_way else 1)
        total_score += graha_score
        lines.append(f"5️⃣ *Грахамайтри*: {graha_score}/5")

        # 6. Гана (6 очков)
        g1, g2 = GANA[nak1], GANA[nak2]
        gana_names = ["Дева","Человек","Ракшаса"]
        gana_score = 6 if g1 == g2 else (3 if abs(g1-g2) == 1 else 0)
        total_score += gana_score
        lines.append(f"6️⃣ *Гана* ({gana_names[g1]}/{gana_names[g2]}): {gana_score}/6")

        # 7. Бхакута (7 очков)
        bhakuta_diff = (rashi2 - rashi1) % 12
        bad_bhakuta = [6, 8, 5, 9]
        bhakuta_score = 0 if bhakuta_diff in bad_bhakuta else 7
        total_score += bhakuta_score
        lines.append(f"7️⃣ *Бхакута*: {bhakuta_score}/7")

        # 8. Нади (8 очков) — самая важная
        n1, n2 = NADI[nak1], NADI[nak2]
        nadi_names = ["Ади","Мадхья","Антья"]
        nadi_score = 0 if n1 == n2 else 8
        total_score += nadi_score
        lines.append(f"8️⃣ *Нади* ({nadi_names[n1]}/{nadi_names[n2]}): {nadi_score}/8")

        # Итог
        percent = int(total_score / max_score * 100)
        if percent >= 75:
            verdict = "🟢 Отличная совместимость"
        elif percent >= 60:
            verdict = "🟡 Хорошая совместимость"
        elif percent >= 40:
            verdict = "🟠 Средняя совместимость"
        else:
            verdict = "🔴 Низкая совместимость"

        lines.append(f"\n*── ИТОГ ──*")
        lines.append(f"🏆 *Сумма: {total_score}/{max_score} ({percent}%)*")
        lines.append(verdict)

        if nadi_score == 0:
            lines.append("⚠️ *Нади-доша* — совпадение Нади требует внимания")
        if bhakuta_score == 0:
            lines.append("⚠️ *Бхакута-доша* — неблагоприятное соотношение знаков")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Ошибка расчёта совместимости: {e}"


# ── Мухурта ───────────────────────────────────────────────────────────
def calculate_muhurta(event_type: str, start_date: str, days_ahead: int = 30) -> str:
    """Поиск благоприятных дат для события."""
    try:
        event_key = event_type.lower()
        good_naks = MUHURTA_NAKSHATRAS.get(event_key, MUHURTA_NAKSHATRAS["бизнес"])
        good_days = MUHURTA_WEEKDAYS.get(event_key, MUHURTA_WEEKDAYS["бизнес"])

        start_dt = datetime.strptime(start_date, "%d.%m.%Y")
        results = []

        for d in range(days_ahead):
            check_dt = start_dt + timedelta(days=d)
            jd = dt_to_jd(check_dt.replace(hour=12))

            moon_lon = sidereal_longitude(swe.MOON, jd)
            nak_idx, _ = longitude_to_nakshatra(moon_lon)
            moon_rashi = int(moon_lon // 30)
            weekday = check_dt.weekday()  # 0=пн

            if nak_idx in good_naks and weekday in good_days:
                # Проверяем что Луна не в сложных знаках
                bad_rashis = [7, 9]  # Скорпион, Козерог — не лучшие для большинства событий
                if moon_rashi not in bad_rashis:
                    results.append({
                        "date": check_dt,
                        "nak": nak_idx,
                        "rashi": moon_rashi,
                        "weekday": weekday,
                    })

        event_names = {
            "свадьба": "Свадьба", "роспись": "Роспись", "бизнес": "Бизнес",
            "путешествие": "Путешествие", "операция": "Операция",
            "красота": "Операция красоты", "покупка": "Крупная покупка",
            "переезд": "Переезд", "лечение": "Лечение",
        }
        ev_name = event_names.get(event_key, event_type)

        lines = [f"🗓 *МУХУРТА — {ev_name.upper()}*\n"]

        if not results:
            lines.append("Благоприятных дат в указанный период не найдено.\nПопробуй расширить период.")
            return "\n".join(lines)

        lines.append(f"✅ Найдено {len(results)} благоприятных дат:\n")
        for r in results[:10]:
            dt = r["date"]
            date_str = f"{dt.day} {MONTH_RU[dt.month]} {dt.year}"
            wd = WEEKDAY_RU[r["weekday"]]
            lines.append(
                f"⭐ *{date_str}* ({wd})\n"
                f"   🌙 Луна: {RASHI[r['rashi']]} / {NAKSHATRAS[r['nak']]}"
            )

        if len(results) > 10:
            lines.append(f"\n...и ещё {len(results)-10} дат")

        lines.append(f"\n💡 _Для точного времени Мухурты уточни у астролога_")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Ошибка расчёта Мухурты: {e}"
