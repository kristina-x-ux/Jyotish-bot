"""
╔══════════════════════════════════════╗
║   ДЖЙОТИШ РАСЧЁТЫ — jyotish.py      ║
╚══════════════════════════════════════╝
Использует Swiss Ephemeris (pyswisseph) для точных расчётов.
Аянамша Лахири — стандарт для Джйотиш.
"""

import swisseph as swe
from datetime import datetime, timezone
import math

# ── Константы Джйотиш ──────────────────────────────────────────────────
swe.set_ephe_path("")  # Встроенные эфемериды

AYANAMSHA = swe.SIDM_LAHIRI  # Аянамша Лахири

GRAHAS = {
    "Сурья (Солнце)":   (swe.SUN,     "☀️"),
    "Чандра (Луна)":    (swe.MOON,    "🌙"),
    "Мангал (Марс)":    (swe.MARS,    "🔴"),
    "Будха (Меркурий)": (swe.MERCURY, "🟡"),
    "Гуру (Юпитер)":   (swe.JUPITER, "🟠"),
    "Шукра (Венера)":  (swe.VENUS,   "⚪"),
    "Шани (Сатурн)":   (swe.SATURN,  "🟤"),
    "Раху":             (swe.MEAN_NODE, "☊"),
    "Кету":             (None,         "☋"),  # Кету = Раху + 180°
}

RASHI = [
    "Меша (Овен) ♈",
    "Вришабха (Телец) ♉",
    "Митхуна (Близнецы) ♊",
    "Карката (Рак) ♋",
    "Симха (Лев) ♌",
    "Канья (Дева) ♍",
    "Тула (Весы) ♎",
    "Вришчика (Скорпион) ♏",
    "Дхану (Стрелец) ♐",
    "Макара (Козерог) ♑",
    "Кумбха (Водолей) ♒",
    "Мина (Рыбы) ♓",
]

RASHI_SHORT = [
    "Меша", "Вришабха", "Митхуна", "Карката",
    "Симха", "Канья", "Тула", "Вришчика",
    "Дхану", "Макара", "Кумбха", "Мина",
]

NAKSHATRAS = [
    "Ашвини", "Бхарани", "Криттика", "Рохини", "Мригашира",
    "Ардра", "Пунарвасу", "Пушья", "Ашлеша", "Магха",
    "Пурва Пхалгуни", "Уттара Пхалгуни", "Хаста", "Читра", "Свати",
    "Вишакха", "Анурадха", "Джьештха", "Мула", "Пурва Ашадха",
    "Уттара Ашадха", "Шравана", "Дхаништха", "Шатабхиша",
    "Пурва Бхадрапада", "Уттара Бхадрапада", "Ревати",
]

# Владыки накшатр (для Даша-системы Вимшоттари)
NAKSHATRA_LORDS = [
    "Кету", "Шукра", "Сурья", "Чандра", "Мангал",
    "Раху", "Гуру", "Шани", "Будха", "Кету",
    "Шукра", "Сурья", "Чандра", "Мангал", "Раху",
    "Гуру", "Шани", "Будха", "Кету", "Шукра",
    "Сурья", "Чандра", "Мангал", "Раху", "Гуру",
    "Шани", "Будха",
]

DASHA_YEARS = {
    "Кету": 7, "Шукра": 20, "Сурья": 6, "Чандра": 10,
    "Мангал": 7, "Раху": 18, "Гуру": 16, "Шани": 19, "Будха": 17,
}

DASHA_ORDER = ["Кету", "Шукра", "Сурья", "Чандра", "Мангал", "Раху", "Гуру", "Шани", "Будха"]

# Планеты в уччха/нича
UCHCHA = {
    swe.SUN: 0, swe.MOON: 1, swe.MARS: 9, swe.MERCURY: 5,
    swe.JUPITER: 3, swe.VENUS: 11, swe.SATURN: 6,
}
NICHA = {p: (d + 6) % 12 for p, d in UCHCHA.items()}


def now_jd() -> float:
    """Юлианская дата текущего момента (UTC)."""
    now = datetime.now(timezone.utc)
    return swe.julday(now.year, now.month, now.day,
                      now.hour + now.minute / 60.0 + now.second / 3600.0)


def sidereal_longitude(planet_id: int, jd: float) -> float:
    """Сидерическая долгота планеты (аянамша Лахири)."""
    swe.set_sid_mode(AYANAMSHA)
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, planet_id, flags)
    return result[0] % 360


def longitude_to_rashi_deg(lon: float) -> tuple[int, float]:
    """Возвращает (индекс раши, градусы внутри раши)."""
    rashi_idx = int(lon // 30)
    deg_in_rashi = lon % 30
    return rashi_idx, deg_in_rashi


def longitude_to_nakshatra(lon: float) -> tuple[int, float]:
    """Возвращает (индекс накшатры, пройденная доля 0-1)."""
    nakshatra_span = 360 / 27  # 13°20'
    nak_idx = int(lon / nakshatra_span)
    nak_fraction = (lon % nakshatra_span) / nakshatra_span
    return nak_idx % 27, nak_fraction


def planet_strength(planet_id: int, rashi_idx: int) -> str:
    """Краткая оценка силы планеты в раши."""
    if UCHCHA.get(planet_id) == rashi_idx:
        return " ⬆️ *уччха*"
    if NICHA.get(planet_id) == rashi_idx:
        return " ⬇️ *нича*"
    return ""


def get_current_transits() -> str:
    """Строка с текущими транзитами всех планет."""
    jd = now_jd()
    lines = []

    rahu_lon = sidereal_longitude(swe.MEAN_NODE, jd)
    ketu_lon = (rahu_lon + 180) % 360

    planet_data = {}

    for name, (planet_id, emoji) in GRAHAS.items():
        if name == "Кету":
            lon = ketu_lon
        else:
            lon = sidereal_longitude(planet_id, jd)

        rashi_idx, deg = longitude_to_rashi_deg(lon)
        nak_idx, nak_frac = longitude_to_nakshatra(lon)
        rashi_name = RASHI_SHORT[rashi_idx]
        nak_name = NAKSHATRAS[nak_idx]

        strength = ""
        if planet_id is not None and name != "Кету":
            strength = planet_strength(planet_id, rashi_idx)

        deg_str = f"{int(deg)}°{int((deg % 1) * 60):02d}'"
        lines.append(
            f"{emoji} *{name}* — {rashi_name} {deg_str}{strength}\n"
            f"   накшатра: {nak_name}"
        )
        planet_data[name] = (rashi_idx, lon)

    return "\n".join(lines)


def get_detailed_positions() -> str:
    """Подробные позиции с градусами и скоростью."""
    jd = now_jd()
    lines = []
    swe.set_sid_mode(AYANAMSHA)

    rahu_lon = sidereal_longitude(swe.MEAN_NODE, jd)
    ketu_lon = (rahu_lon + 180) % 360

    for name, (planet_id, emoji) in GRAHAS.items():
        if name == "Кету":
            lon = ketu_lon
            speed = None
        else:
            flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
            result, _ = swe.calc_ut(jd, planet_id, flags)
            lon = result[0] % 360
            speed = result[3]  # градусов в день

        rashi_idx, deg = longitude_to_rashi_deg(lon)
        nak_idx, nak_frac = longitude_to_nakshatra(lon)

        retro = ""
        if speed is not None and speed < 0:
            retro = " ℞ *ретроград*"

        strength = ""
        if planet_id is not None and name != "Кету":
            strength = planet_strength(planet_id, rashi_idx)

        deg_str = f"{int(deg)}°{int((deg % 1) * 60):02d}'"
        lines.append(
            f"{emoji} *{name}*: {RASHI_SHORT[rashi_idx]} {deg_str}"
            f"{retro}{strength}\n"
            f"   📿 {NAKSHATRAS[nak_idx]} (пада {int(nak_frac * 4) + 1})"
        )

    return "\n".join(lines)


def get_transit_context() -> str:
    """Ключевые аспекты и соединения текущего момента."""
    jd = now_jd()
    swe.set_sid_mode(AYANAMSHA)

    positions = {}
    rahu_lon = sidereal_longitude(swe.MEAN_NODE, jd)
    positions["Раху"] = rahu_lon
    positions["Кету"] = (rahu_lon + 180) % 360

    for name, (planet_id, _) in GRAHAS.items():
        if planet_id is not None and name not in ("Раху", "Кету"):
            positions[name] = sidereal_longitude(planet_id, jd)

    # Ищем соединения (юти) — планеты в одном раши
    rashi_groups: dict[int, list] = {}
    for name, lon in positions.items():
        r = int(lon // 30)
        rashi_groups.setdefault(r, []).append(name)

    notes = []
    for rashi_idx, planets in rashi_groups.items():
        if len(planets) >= 2:
            rashi_name = RASHI_SHORT[rashi_idx]
            notes.append(f"🔗 Юти в {rashi_name}: {' + '.join(planets)}")

    # Ищем оппозиции (~180°) и трины (~120°)
    planet_list = list(positions.items())
    for i in range(len(planet_list)):
        for j in range(i + 1, len(planet_list)):
            n1, l1 = planet_list[i]
            n2, l2 = planet_list[j]
            diff = abs(l1 - l2) % 360
            if diff > 180:
                diff = 360 - diff
            if 170 <= diff <= 190:
                notes.append(f"⟺ Оппозиция: {n1} — {n2}")
            elif 115 <= diff <= 125:
                notes.append(f"△ Трин: {n1} — {n2}")

    return "\n".join(notes[:5]) if notes else ""


def calculate_natal_basics(birth_date: str, birth_time: str | None, place: str) -> dict:
    """
    Рассчитывает базовые натальные позиции.
    Для точного расчёта Лагны нужны координаты места.
    """
    try:
        dt_str = birth_date
        if birth_time:
            dt = datetime.strptime(f"{birth_date} {birth_time}", "%d.%m.%Y %H:%M")
        else:
            dt = datetime.strptime(birth_date, "%d.%m.%Y")
            dt = dt.replace(hour=12)  # Полдень если нет времени

        jd = swe.julday(dt.year, dt.month, dt.day,
                        dt.hour + dt.minute / 60.0)
        swe.set_sid_mode(AYANAMSHA)

        # Солнце
        sun_lon = sidereal_longitude(swe.SUN, jd)
        sun_rashi = int(sun_lon // 30)

        # Луна
        moon_lon = sidereal_longitude(swe.MOON, jd)
        moon_rashi = int(moon_lon // 30)
        moon_nak_idx, moon_nak_frac = longitude_to_nakshatra(moon_lon)

        # Даша Вимшоттари — считаем от положения Луны
        mahadasha, antardasha = calculate_vimshottari(moon_lon, dt)

        return {
            "sun_sign": RASHI_SHORT[sun_rashi],
            "moon_sign": RASHI_SHORT[moon_rashi],
            "moon_nakshatra": NAKSHATRAS[moon_nak_idx],
            "lagna": "Требует точного времени и координат" if not birth_time else RASHI_SHORT[sun_rashi],
            "mahadasha": mahadasha,
            "antardasha": antardasha,
        }
    except Exception as e:
        return {"error": str(e)}


def calculate_vimshottari(moon_lon: float, birth_dt: datetime) -> tuple[str, str]:
    """Упрощённый расчёт Маха-Даши и Антар-Даши."""
    try:
        nak_idx, nak_frac = longitude_to_nakshatra(moon_lon)
        lord = NAKSHATRA_LORDS[nak_idx]
        dasha_years = DASHA_YEARS[lord]

        # Сколько лет Даши прошло на момент рождения
        elapsed_fraction = nak_frac
        elapsed_years = elapsed_fraction * dasha_years
        remaining_years = dasha_years - elapsed_years

        # Находим текущую Маха-Дашу
        lord_idx = DASHA_ORDER.index(lord)
        now = datetime.now()
        years_since_birth = (now - birth_dt).days / 365.25

        # Суммируем Даши
        total = remaining_years
        current_dasha_idx = lord_idx

        while total < years_since_birth:
            current_dasha_idx = (current_dasha_idx + 1) % 9
            total += DASHA_YEARS[DASHA_ORDER[current_dasha_idx]]

        mahadasha_lord = DASHA_ORDER[current_dasha_idx]

        # Антар-Даша (упрощённо)
        years_into_dasha = years_since_birth - (total - DASHA_YEARS[mahadasha_lord])
        antardasha = _get_antardasha(mahadasha_lord, years_into_dasha)

        return mahadasha_lord, antardasha
    except Exception:
        return "не рассчитана", "не рассчитана"


def _get_antardasha(mahadasha_lord: str, years_elapsed: float) -> str:
    """Определяет Антар-Дашу внутри Маха-Даши."""
    total_years = DASHA_YEARS[mahadasha_lord]
    lord_idx = DASHA_ORDER.index(mahadasha_lord)

    accumulated = 0.0
    for i in range(9):
        sub_lord = DASHA_ORDER[(lord_idx + i) % 9]
        sub_duration = (DASHA_YEARS[sub_lord] / 120) * total_years
        accumulated += sub_duration
        if accumulated > years_elapsed:
            return sub_lord
    return DASHA_ORDER[lord_idx]
