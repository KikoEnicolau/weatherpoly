import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import json
import re

st.set_page_config(page_title="Polymarket Weather Tracker", page_icon="🌡️", layout="wide")

st.markdown("""
<style>
    body { background:#0f1117; }
    .city-card  { background:#1a1d27; border:1px solid #2d3147; border-radius:14px; padding:1.3rem; margin-bottom:1rem; }
    .temp-big   { font-size:2.8rem; font-weight:700; color:#f0f0f0; line-height:1; }
    .temp-feel  { font-size:.85rem; color:#8b8fa8; margin-top:2px; }
    .label      { font-size:.72rem; color:#8b8fa8; text-transform:uppercase; letter-spacing:.08em; margin-bottom:2px; }
    .value      { font-size:1rem; font-weight:600; color:#e0e0e0; }
    .now-badge  { background:#1e3a1e; color:#4ade80; border-radius:6px; padding:2px 8px; font-size:.72rem; font-weight:700; letter-spacing:.05em; }
    .ai-box     { background:#12151f; border-left:3px solid #6366f1; border-radius:0 8px 8px 0; padding:.9rem 1.1rem; margin-top:.8rem; font-size:.88rem; color:#c0c4d8; line-height:1.7; }
    .sim-badge  { background:#1a3a2a; color:#4ade80; border-radius:6px; padding:3px 12px; font-size:.85rem; font-weight:700; }
    .nao-badge  { background:#3a1a1a; color:#f87171; border-radius:6px; padding:3px 12px; font-size:.85rem; font-weight:700; }
    .neu-badge  { background:#2a2a3a; color:#a0a0c0; border-radius:6px; padding:3px 12px; font-size:.85rem; font-weight:700; }
    .odds-row   { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
    .odds-bar-bg{ flex:1; height:7px; background:#2d3147; border-radius:4px; overflow:hidden; }
    .odds-bar   { height:100%; border-radius:4px; }
    .hourly-row { display:flex; gap:8px; overflow-x:auto; padding-bottom:4px; margin-bottom:.5rem; }
    .hour-box   { background:#12151f; border:1px solid #2d3147; border-radius:10px; padding:8px 10px; text-align:center; min-width:58px; flex-shrink:0; }
    .hour-time  { font-size:.7rem; color:#8b8fa8; margin-bottom:3px; }
    .hour-temp  { font-size:1rem; font-weight:600; color:#f0f0f0; }
    .hour-icon  { font-size:.9rem; margin-bottom:2px; }
    .hour-rain  { font-size:.68rem; color:#60a5fa; margin-top:2px; }
    .section-lbl{ font-size:.78rem; color:#8b8fa8; text-transform:uppercase; letter-spacing:.07em; margin:.8rem 0 .4rem; font-weight:600; }
    div[data-testid="stHorizontalBlock"] { gap: 1rem; }
</style>
""", unsafe_allow_html=True)

# ── Config ─────────────────────────────────────────────────────────────────────
WEATHER_API_KEY = st.secrets.get("WEATHER_API_KEY", "309038af8627473d88d130403261403")

CITIES = {
    "São Paulo":    {"lat":-23.55,"lon":-46.63,"poly":"sao-paulo"},
    "Ankara":       {"lat":39.93, "lon":32.86, "poly":"ankara"},
    "London":       {"lat":51.51, "lon":-0.13, "poly":"london"},
    "Paris":        {"lat":48.85, "lon":2.35,  "poly":"paris"},
    "Seoul":        {"lat":37.57, "lon":126.98,"poly":"seoul"},
    "New York":     {"lat":40.71, "lon":-74.01,"poly":"nyc"},
    "Chicago":      {"lat":41.88, "lon":-87.63,"poly":"chicago"},
    "Dallas":       {"lat":32.78, "lon":-96.80,"poly":"dallas"},
    "Miami":        {"lat":25.77, "lon":-80.19,"poly":"miami"},
    "Atlanta":      {"lat":33.75, "lon":-84.39,"poly":"atlanta"},
    "Seattle":      {"lat":47.61, "lon":-122.33,"poly":"seattle"},
    "Toronto":      {"lat":43.65, "lon":-79.38,"poly":"toronto"},
    "Buenos Aires": {"lat":-34.60,"lon":-58.38,"poly":"buenos-aires"},
    "Wellington":   {"lat":-41.29,"lon":174.78,"poly":"wellington"},
}

# ── API calls ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # 5 min cache for current conditions
def get_weather_realtime(lat, lon):
    """Current conditions + hourly forecast for today & tomorrow."""
    url    = "http://api.weatherapi.com/v1/forecast.json"
    params = {
        "key":    WEATHER_API_KEY,
        "q":      f"{lat},{lon}",
        "days":   2,
        "aqi":    "no",
        "alerts": "no",
        "hour":   24,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=600)
def get_weather_forecast(lat, lon):
    """5-day forecast."""
    url    = "http://api.weatherapi.com/v1/forecast.json"
    params = {"key": WEATHER_API_KEY, "q": f"{lat},{lon}", "days": 5, "aqi": "no", "alerts": "no"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=300)
def get_polymarket(city_poly, date):
    """Fetch Polymarket market via direct slug construction."""
    month = date.strftime("%B").lower()
    slug  = f"highest-temperature-in-{city_poly}-on-{month}-{date.day}-{date.year}"
    url   = f"https://gamma-api.polymarket.com/events?slug={slug}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        events = r.json()
        if not events:
            return None, slug
        markets = events[0].get("markets", [])
        results = []
        for m in markets:
            outcomes = m.get("outcomes", "[]")
            prices   = m.get("outcomePrices", "[]")
            if isinstance(outcomes, str):
                try: outcomes = json.loads(outcomes)
                except: outcomes = []
            if isinstance(prices, str):
                try: prices = [float(x) for x in json.loads(prices)]
                except: prices = []
            results.append({
                "question": m.get("question",""),
                "volume":   float(m.get("volume") or 0),
                "outcomes": outcomes,
                "prices":   prices,
            })
        return (results if results else None), slug
    except Exception:
        return None, slug

# ── Helpers ────────────────────────────────────────────────────────────────────
def weather_icon(code):
    if code == 1000: return "☀️"
    if code in (1003,1006,1009): return "⛅"
    if code in (1030,1135,1147): return "🌫️"
    if 1150 <= code < 1210: return "🌧️"
    if 1210 <= code < 1260: return "❄️"
    if code in (1273,1276,1279,1282): return "⛈️"
    return "🌤️"

def trend_arrow(current, forecast_max):
    if forecast_max > current + 2:  return "↗️"
    if forecast_max < current - 2:  return "↘️"
    return "→"

def build_hourly_html(hours, current_hour):
    """Build the horizontal hourly scroll strip."""
    boxes = []
    for h in hours:
        t    = datetime.strptime(h["time"], "%Y-%m-%d %H:%M")
        hr   = t.hour
        temp = h["temp_c"]
        rain = h["chance_of_rain"]
        icon = weather_icon(h["condition"]["code"])
        is_now = (hr == current_hour)
        border = "border:1.5px solid #6366f1;" if is_now else ""
        now_lbl= '<div style="font-size:.6rem;color:#6366f1;font-weight:700">AGORA</div>' if is_now else ""
        boxes.append(f"""
        <div class="hour-box" style="{border}">
            {now_lbl}
            <div class="hour-time">{t.strftime('%H:%M')}</div>
            <div class="hour-icon">{icon}</div>
            <div class="hour-temp">{temp:.0f}°</div>
            <div class="hour-rain">💧{rain:.0f}%</div>
        </div>""")
    return f'<div class="hourly-row">{"".join(boxes)}</div>'

def ai_analysis(city, today_max, today_min, today_precip,
                tmrw_max, tmrw_min, tmrw_precip,
                today_markets, tmrw_markets,
                today_date, tmrw_date):
    """
    Core analysis: for each day, look at each Polymarket outcome (temperature),
    compare with forecast max, and give a SIM/NÃO/PULAR recommendation.
    """
    sections = []

    for label, date, max_t, min_t, precip, markets in [
        ("HOJE",   today_date, today_max, today_min, today_precip, today_markets),
        ("AMANHÃ", tmrw_date,  tmrw_max,  tmrw_min,  tmrw_precip,  tmrw_markets),
    ]:
        if not markets:
            sections.append(f"<b>{label} ({date.strftime('%d/%m')}):</b> Nenhum mercado ativo encontrado.")
            continue

        m = markets[0]
        outcomes, prices = m["outcomes"], m["prices"]
        if not outcomes or not prices:
            sections.append(f"<b>{label}:</b> Dados indisponíveis.")
            continue

        # Find the outcome closest to forecast max
        best_rec  = None
        best_conf = ""
        best_badge= "neu-badge"

        # Uncertainty band: forecast is +/- 1°C reliable
        forecast_low  = max_t - 1.0
        forecast_high = max_t + 1.0

        for outcome, price in zip(outcomes, prices):
            nums = re.findall(r'\d+', outcome)
            if not nums:
                continue
            mkt_temp = int(nums[0])
            pct      = price * 100

            # Is market temp within forecast band?
            in_band = forecast_low <= mkt_temp <= forecast_high

            # Confidence score: how close is mkt_temp to rounded forecast
            dist = abs(mkt_temp - round(max_t))

            if best_rec is None or dist < abs(int(re.findall(r'\d+', best_rec)[0]) - round(max_t)) if best_rec and re.findall(r'\d+', best_rec) else True:
                if in_band or dist <= 1:
                    best_rec  = outcome
                    best_conf = f"{pct:.0f}%"
                    best_badge = "sim-badge"

        # Build recommendation text
        forecast_rounded = round(max_t)

        # Find what the market says for exactly the forecast temp
        target_outcome = None
        target_price   = None
        for outcome, price in zip(outcomes, prices):
            nums = re.findall(r'\d+', outcome)
            if nums and int(nums[0]) == forecast_rounded:
                target_outcome = outcome
                target_price   = price * 100
                break

        # Also check one above/below
        near_outcomes = []
        for outcome, price in zip(outcomes, prices):
            nums = re.findall(r'\d+', outcome)
            if nums:
                diff = abs(int(nums[0]) - forecast_rounded)
                if diff <= 1:
                    near_outcomes.append((outcome, price * 100, int(nums[0])))

        near_outcomes.sort(key=lambda x: abs(x[2] - forecast_rounded))

        # Rain adjustment
        rain_note = ""
        if precip >= 60:
            rain_note = f"⚠️ {precip:.0f}% de chuva — reduz a máxima, considere 1°C a menos."
            forecast_rounded = max(forecast_rounded - 1, forecast_rounded - 1)
        elif precip >= 35:
            rain_note = f"🌂 {precip:.0f}% de chuva — pode segurar levemente a máxima."

        # Build output
        lines = [f"<b>{label} ({date.strftime('%d/%m')}) — Previsão: {max_t:.1f}°C | Mín: {min_t:.1f}°C</b>"]

        if rain_note:
            lines.append(rain_note)

        if near_outcomes:
            for out, pct, t in near_outcomes[:3]:
                diff = t - round(max_t)
                if diff == 0:
                    rec   = "SIM"
                    badge = "sim-badge"
                    reason = f"Previsão bate exatamente com {t}°C — apostar <span class='{badge}'>{rec}</span> tem valor (odds {pct:.0f}%)"
                elif diff == 1:
                    if precip < 35:
                        rec   = "SIM"
                        badge = "sim-badge"
                        reason = f"{t}°C é 1° acima da previsão — possível se dia esquentar mais, <span class='{badge}'>{rec}</span> com cautela (odds {pct:.0f}%)"
                    else:
                        rec   = "NÃO"
                        badge = "nao-badge"
                        reason = f"{t}°C é 1° acima da previsão e há chuva — <span class='{badge}'>{rec}</span> (odds {pct:.0f}%)"
                elif diff == -1:
                    if precip >= 35:
                        rec   = "SIM"
                        badge = "sim-badge"
                        reason = f"{t}°C é 1° abaixo da previsão — chuva pode segurar a máxima, <span class='{badge}'>{rec}</span> (odds {pct:.0f}%)"
                    else:
                        rec   = "NÃO"
                        badge = "nao-badge"
                        reason = f"{t}°C está abaixo da previsão — <span class='{badge}'>{rec}</span> (odds {pct:.0f}%)"
                else:
                    rec   = "PULAR"
                    badge = "neu-badge"
                    reason = f"{t}°C está longe da previsão — <span class='{badge}'>{rec}</span>"
                lines.append(f"• {reason}")
        else:
            lines.append(f"Nenhum outcome próximo de {forecast_rounded}°C encontrado no mercado.")

        sections.append("<br>".join(lines))

    return "<br><br>".join(sections)

# ── UI ─────────────────────────────────────────────────────────────────────────
st.markdown("## 🌡️ Polymarket Weather Tracker")
st.caption("Temperatura em tempo real · Previsão hora a hora · Análise SIM/NÃO para os mercados Polymarket")
st.divider()

c1, c2, c3 = st.columns([2,3,1])
with c1:
    selected = st.multiselect(
        "Cidades", options=list(CITIES.keys()),
        default=["São Paulo","Ankara","London","New York"],
    )
with c2:
    st.write("")
with c3:
    st.write("")
    if st.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear(); st.rerun()

if not selected:
    st.info("Selecione pelo menos uma cidade."); st.stop()

st.divider()

today    = datetime.today().date()
tomorrow = today + timedelta(days=1)
now_hour = datetime.now().hour

cols = st.columns(2)
for i, city in enumerate(selected):
    cfg = CITIES[city]
    with cols[i % 2]:
        with st.spinner(f"Carregando {city}..."):
            wdata         = get_weather_realtime(cfg["lat"], cfg["lon"])
            forecast_data = get_weather_forecast(cfg["lat"], cfg["lon"])
            today_mkts, today_slug   = get_polymarket(cfg["poly"], today)
            tmrw_mkts,  tmrw_slug    = get_polymarket(cfg["poly"], tomorrow)

        if not wdata:
            st.error(f"Erro ao carregar dados de {city}"); continue

        current  = wdata["current"]
        cur_temp = current["temp_c"]
        cur_feel = current["feelslike_c"]
        cur_cond = current["condition"]["text"]
        cur_icon = weather_icon(current["condition"]["code"])
        cur_wind = current["wind_kph"]
        cur_hum  = current["humidity"]

        # Today forecast day
        today_day  = wdata["forecast"]["forecastday"][0]["day"]
        today_max  = today_day["maxtemp_c"]
        today_min  = today_day["mintemp_c"]
        today_rain = today_day["daily_chance_of_rain"]

        # Tomorrow forecast day
        tmrw_day  = wdata["forecast"]["forecastday"][1]["day"] if len(wdata["forecast"]["forecastday"]) > 1 else today_day
        tmrw_max  = tmrw_day["maxtemp_c"]
        tmrw_min  = tmrw_day["mintemp_c"]
        tmrw_rain = tmrw_day["daily_chance_of_rain"]

        arrow = trend_arrow(cur_temp, today_max)

        # ── CARD: current conditions ──
        st.markdown(f"""
        <div class="city-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem">
                <div>
                    <div style="font-size:1.15rem;font-weight:700;color:#f0f0f0;margin-bottom:4px">
                        {cur_icon} {city} &nbsp;<span class="now-badge">AO VIVO</span>
                    </div>
                    <div class="label">{cur_cond} · {datetime.now().strftime('%H:%M')}</div>
                </div>
                <div style="text-align:right">
                    <div class="temp-big">{cur_temp:.1f}°C {arrow}</div>
                    <div class="temp-feel">Sensação {cur_feel:.0f}°C</div>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem;margin-bottom:.8rem">
                <div><div class="label">Máx hoje</div><div class="value">{today_max:.0f}°C</div></div>
                <div><div class="label">Mín hoje</div><div class="value">{today_min:.0f}°C</div></div>
                <div><div class="label">Umidade</div><div class="value">{cur_hum}%</div></div>
                <div><div class="label">Vento</div><div class="value">{cur_wind:.0f} km/h</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Hourly: today ──
        st.markdown('<div class="section-lbl">⏱ Hoje — hora a hora</div>', unsafe_allow_html=True)
        today_hours = wdata["forecast"]["forecastday"][0]["hour"]
        st.markdown(build_hourly_html(today_hours, now_hour), unsafe_allow_html=True)

        # ── Hourly: tomorrow ──
        if len(wdata["forecast"]["forecastday"]) > 1:
            st.markdown('<div class="section-lbl">📅 Amanhã — hora a hora</div>', unsafe_allow_html=True)
            tmrw_hours = wdata["forecast"]["forecastday"][1]["hour"]
            st.markdown(build_hourly_html(tmrw_hours, -1), unsafe_allow_html=True)

        # ── Polymarket odds (today + tomorrow) ──
        st.markdown('<div class="section-lbl">📊 Polymarket</div>', unsafe_allow_html=True)
        for lbl, mkts, slug, date in [
            ("Hoje",    today_mkts, today_slug, today),
            ("Amanhã",  tmrw_mkts,  tmrw_slug,  tomorrow),
        ]:
            event_url = f"https://polymarket.com/event/{slug}"
            if mkts:
                with st.expander(f"{lbl} — {date.strftime('%d/%m/%Y')} · {len(mkts)} mercado(s) · [abrir]({event_url})", expanded=(lbl=="Amanhã")):
                    m = mkts[0]
                    if m["outcomes"] and m["prices"]:
                        pairs = sorted(zip(m["outcomes"], m["prices"]), key=lambda x: x[1], reverse=True)
                        max_p = max(m["prices"])
                        for outcome, price in pairs[:8]:
                            pct   = price * 100
                            color = "#6366f1" if price == max_p else "#3d4166"
                            st.markdown(f"""
                            <div class="odds-row">
                                <span style="font-size:13px;color:#e0e0e0;width:140px;flex-shrink:0">{outcome}</span>
                                <div class="odds-bar-bg"><div class="odds-bar" style="width:{pct}%;background:{color}"></div></div>
                                <span style="font-size:13px;font-weight:600;color:#a0a4c8;width:38px;text-align:right">{pct:.0f}%</span>
                            </div>""", unsafe_allow_html=True)
                        st.caption(f"Volume: ${m['volume']:,.0f}")
            else:
                st.markdown(f"_{lbl}: mercado não encontrado._ [Verificar no Polymarket]({event_url})")

        # ── AI Analysis ──
        st.markdown('<div class="section-lbl">🤖 Análise — melhor entrada</div>', unsafe_allow_html=True)
        analysis = ai_analysis(
            city,
            today_max, today_min, today_rain,
            tmrw_max,  tmrw_min,  tmrw_rain,
            today_mkts, tmrw_mkts,
            today, tomorrow,
        )
        st.markdown(f'<div class="ai-box">{analysis}</div>', unsafe_allow_html=True)

        # ── 5-day summary ──
        if forecast_data:
            st.markdown('<div class="section-lbl">📆 Próximos 5 dias</div>', unsafe_allow_html=True)
            rows = []
            for d in forecast_data["forecast"]["forecastday"]:
                dt = datetime.strptime(d["date"], "%Y-%m-%d")
                rows.append({
                    "Dia":   dt.strftime("%a %d/%m"),
                    "":      weather_icon(d["day"]["condition"]["code"]),
                    "Máx":   f"{d['day']['maxtemp_c']:.0f}°C",
                    "Mín":   f"{d['day']['mintemp_c']:.0f}°C",
                    "Chuva": f"{d['day']['daily_chance_of_rain']:.0f}%",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.divider()

st.caption("Dados: WeatherAPI.com (tempo real) · Polymarket Gamma API · Atualiza a cada 5 min · Não é conselho financeiro.")
