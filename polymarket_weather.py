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
    For each day, find the single best value bet:
    - 'Value' = outcome where the market odds underestimate the real probability
    - SIM on outcomes the forecast strongly supports (dist == 0, or dist -1 with rain)
    - NÃO on outcomes the forecast contradicts AND the payout is good (price < 0.40)
    - Best NÃO = market is pricing something likely wrong at decent odds
    - Best SIM = market underpricing what forecast says will happen
    - Pick whichever has better expected value
    """
    sections = []

    for label, date, max_t, min_t, precip, markets in [
        ("HOJE",   today_date, today_max, today_min, today_precip, today_markets),
        ("AMANHÃ", tmrw_date,  tmrw_max,  tmrw_min,  tmrw_precip,  tmrw_markets),
    ]:
        header = f"<b>{label} — {date.strftime('%d/%m')}</b>"

        if not markets:
            sections.append(f"{header}<br>Nenhum mercado ativo encontrado.")
            continue

        m = markets[0]
        outcomes, prices = m["outcomes"], m["prices"]
        if not outcomes or not prices:
            sections.append(f"{header}<br>Dados indisponíveis.")
            continue

        # Effective forecast after rain adjustment
        eff_max = max_t - 1.0 if precip >= 50 else max_t
        forecast_rounded = round(eff_max)

        # Build candidates with value score
        # Value = how much the market is mispriced vs what forecast says
        # SIM candidates: outcomes forecast supports → value if price < 0.65 (market underpricing)
        # NÃO candidates: outcomes forecast contradicts → value if price > 0.20 (market overpricing)
        best_sim = None
        best_nao = None

        for outcome, price in zip(outcomes, prices):
            nums = re.findall(r'\d+', outcome)
            if not nums:
                continue
            mkt_temp = int(nums[0])
            pct      = price * 100
            dist     = mkt_temp - forecast_rounded  # signed

            # SIM candidate: forecast matches this outcome
            if dist == 0:
                # Best SIM: exact match. More value if market is underpricing (low odds)
                ev = (1 - price) / price  # payout per $ risked if correct
                if best_sim is None or ev > best_sim["ev"]:
                    best_sim = {"outcome": outcome, "mkt_temp": mkt_temp, "pct": pct, "ev": ev, "dist": dist}

            elif dist == -1 and precip >= 50:
                # Forecast 1° above but rain may pull it down → SIM on lower temp
                ev = (1 - price) / price
                if best_sim is None or ev > best_sim["ev"]:
                    best_sim = {"outcome": outcome, "mkt_temp": mkt_temp, "pct": pct, "ev": ev, "dist": dist}

            # NÃO candidate: forecast clearly contradicts this outcome AND market is overpricing it
            if abs(dist) >= 2 and price >= 0.15:
                # Good NÃO: market thinks this has 15%+ chance but forecast says no
                ev = (1 - price) / price  # payout if NÃO wins = price/(1-price) per $ risked
                nao_ev = price / (1 - price) if price < 1 else 0
                if best_nao is None or nao_ev > best_nao["ev"]:
                    best_nao = {"outcome": outcome, "mkt_temp": mkt_temp, "pct": pct, "ev": nao_ev, "dist": dist}

        # Decide which to show: pick the one with clearer edge
        lines = [header]
        rain_ctx = f"⚠️ {precip:.0f}% de chuva — previsão ajustada para {eff_max:.0f}°C. " if precip >= 50 else ""

        if best_sim and best_nao:
            # Compare: SIM has higher confidence (forecast directly supports it)
            # NÃO has value only if market is clearly overpricing a wrong outcome
            if best_sim["pct"] < 55:
                # Market underpricing the forecast outcome → SIM is the value play
                pick = best_sim
                rec  = "SIM"
                badge = "sim-badge"
                explanation = (
                    f"{rain_ctx}A previsão aponta {eff_max:.1f}°C de máxima e o mercado está precificando "
                    f"{pick['mkt_temp']}°C em apenas {pick['pct']:.0f}% — abaixo do que a previsão sugere. "
                    f"Entrar em <b>SIM</b> em {pick['mkt_temp']}°C tem bom valor esperado."
                )
            else:
                # SIM já está bem precificado, NÃO pode ter mais valor
                pick = best_nao
                rec  = "NÃO"
                badge = "nao-badge"
                explanation = (
                    f"{rain_ctx}A previsão aponta {eff_max:.1f}°C de máxima. O mercado ainda dá {pick['pct']:.0f}% "
                    f"para {pick['mkt_temp']}°C, mas isso está {abs(pick['dist'])}°C longe da previsão. "
                    f"Entrar em <b>NÃO</b> em {pick['mkt_temp']}°C aproveita essa discrepância."
                )
        elif best_sim:
            pick = best_sim
            rec  = "SIM"
            badge = "sim-badge"
            explanation = (
                f"{rain_ctx}A previsão aponta {eff_max:.1f}°C de máxima. "
                f"O mercado precifica {pick['mkt_temp']}°C em {pick['pct']:.0f}% — "
                f"{'abaixo do esperado, bom valor em ' if pick['pct'] < 55 else 'bem alinhado, entrada conservadora em '}"
                f"<b>SIM</b>."
            )
        elif best_nao:
            pick = best_nao
            rec  = "NÃO"
            badge = "nao-badge"
            explanation = (
                f"{rain_ctx}A previsão aponta {eff_max:.1f}°C de máxima. "
                f"O mercado dá {pick['pct']:.0f}% para {pick['mkt_temp']}°C, "
                f"que está {abs(pick['dist'])}°C longe — <b>NÃO</b> tem valor aqui."
            )
        else:
            sections.append(f"{header}<br>{rain_ctx}Nenhuma entrada com valor claro identificada para este dia.")
            continue

        lines.append(
            f"<div style='margin:.5rem 0'>"
            f"<span style='font-size:1rem;font-weight:700;color:#f0f0f0'>{pick['mkt_temp']}°C</span>"
            f"&nbsp;&nbsp;<span class='{badge}'>{rec}</span>"
            f"&nbsp;&nbsp;<span style='color:#8b8fa8;font-size:.82rem'>odds {pick['pct']:.0f}%</span>"
            f"</div>"
        )
        lines.append(f"<span style='font-size:.84rem;color:#a0a4c8'>{explanation}</span>")

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
