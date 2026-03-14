import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import json
import re

st.set_page_config(page_title="Polymarket Weather Tracker", page_icon="🌡️", layout="wide")

st.markdown("""
<style>
    .city-card { background:#1a1d27; border:1px solid #2d3147; border-radius:12px; padding:1.2rem; margin-bottom:1rem; }
    .temp-big  { font-size:2.2rem; font-weight:700; color:#f0f0f0; }
    .label     { font-size:0.75rem; color:#8b8fa8; text-transform:uppercase; letter-spacing:.08em; }
    .value     { font-size:1rem; font-weight:600; color:#e0e0e0; }
    .ai-box    { background:#12151f; border-left:3px solid #6366f1; border-radius:0 8px 8px 0; padding:.8rem 1rem; margin-top:.8rem; font-size:.88rem; color:#c0c4d8; line-height:1.6; }
    .odds-row  { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
    .odds-bar-bg { flex:1; height:7px; background:#2d3147; border-radius:4px; overflow:hidden; }
    .odds-bar  { height:100%; border-radius:4px; }
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

# ── Helpers ────────────────────────────────────────────────────────────────────
def poly_slug(city_poly, date):
    """Build Polymarket event slug directly from city + date."""
    month = date.strftime("%B").lower()
    day   = date.day
    return f"highest-temperature-in-{city_poly}-on-{month}-{day}-{date.year}"

@st.cache_data(ttl=300)
def get_polymarket(city_poly, date):
    slug = poly_slug(city_poly, date)
    url  = f"https://gamma-api.polymarket.com/events?slug={slug}"
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
        return results if results else None, slug
    except Exception:
        return None, slug

@st.cache_data(ttl=600)
def get_weather(lat, lon):
    url    = "http://api.weatherapi.com/v1/forecast.json"
    params = {"key": WEATHER_API_KEY, "q": f"{lat},{lon}", "days": 5, "aqi": "no", "alerts": "no"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def weather_icon(code):
    if code == 1000: return "☀️"
    if code in (1003,1006,1009): return "⛅"
    if code in (1030,1135,1147): return "🌫️"
    if 1150 <= code < 1210: return "🌧️"
    if 1210 <= code < 1260: return "❄️"
    if code in (1273,1276,1279,1282): return "⛈️"
    return "🌤️"

def ai_verdict(max_t, precip, markets):
    if not markets:
        return "Nenhum mercado ativo encontrado para esta data."
    m = markets[0]
    outcomes, prices = m["outcomes"], m["prices"]
    if not outcomes or not prices:
        return "Dados do mercado indisponíveis."

    best_i   = prices.index(max(prices))
    best_out = outcomes[best_i]
    best_pct = prices[best_i] * 100

    lines = [f"**Favorito do mercado:** {best_out} ({best_pct:.0f}%)"]

    nums = re.findall(r'\d+', best_out)
    if nums:
        mkt_temp = int(nums[0])
        diff = round(max_t) - mkt_temp
        if diff == 0:
            lines.append(f"✅ Previsão ({max_t:.0f}°C) **alinhada** com o favorito — mercado bem precificado.")
        elif diff > 0:
            lines.append(f"⬆️ Previsão ({max_t:.0f}°C) está **acima** do favorito ({mkt_temp}°C) — NÃO no favorito pode ter valor.")
        else:
            lines.append(f"⬇️ Previsão ({max_t:.0f}°C) está **abaixo** do favorito ({mkt_temp}°C) — NÃO no favorito pode ter valor.")

    if precip >= 60:
        lines.append(f"🌧️ {precip:.0f}% de chuva — forte pressão de baixa na máxima.")
    elif precip >= 30:
        lines.append(f"🌂 {precip:.0f}% de chuva — pode reduzir levemente a máxima.")
    else:
        lines.append(f"☀️ {precip:.0f}% de chuva — condições favoráveis para temperatura alta.")

    return "<br><br>".join(lines)

# ── UI ─────────────────────────────────────────────────────────────────────────
st.markdown("## 🌡️ Polymarket Weather Tracker")
st.caption("Previsão do tempo + odds do Polymarket + análise automática.")
st.divider()

c1, c2, c3 = st.columns([2,3,1])
with c1:
    target_date = st.date_input(
        "Data do mercado",
        value=datetime.today().date() + timedelta(days=1),
        min_value=datetime.today().date(),
        max_value=datetime.today().date() + timedelta(days=4),
    )
with c2:
    selected = st.multiselect(
        "Cidades", options=list(CITIES.keys()),
        default=["São Paulo","Ankara","London","New York"],
    )
with c3:
    st.write(""); st.write("")
    if st.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear(); st.rerun()

if not selected:
    st.info("Selecione pelo menos uma cidade."); st.stop()

st.divider()

cols = st.columns(2)
for i, city in enumerate(selected):
    cfg = CITIES[city]
    with cols[i % 2]:
        with st.spinner(f"Carregando {city}..."):
            weather         = get_weather(cfg["lat"], cfg["lon"])
            markets, slug   = get_polymarket(cfg["poly"], target_date)

        # Weather
        forecast_day = None
        if weather:
            for d in weather["forecast"]["forecastday"]:
                if d["date"] == str(target_date):
                    forecast_day = d; break
            if not forecast_day:
                forecast_day = weather["forecast"]["forecastday"][0]

        if forecast_day:
            max_t    = forecast_day["day"]["maxtemp_c"]
            min_t    = forecast_day["day"]["mintemp_c"]
            precip   = forecast_day["day"]["daily_chance_of_rain"]
            cond_txt = forecast_day["day"]["condition"]["text"]
            icon     = weather_icon(forecast_day["day"]["condition"]["code"])
        else:
            max_t = min_t = precip = 0; cond_txt = "Sem dados"; icon = "❓"

        # Card
        st.markdown(f"""
        <div class="city-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.8rem">
                <div>
                    <div style="font-size:1.1rem;font-weight:700;color:#f0f0f0">{icon} {city}</div>
                    <div class="label">{target_date.strftime('%d/%m/%Y')} · {cond_txt}</div>
                </div>
                <div class="temp-big">{max_t:.0f}°C</div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem">
                <div><div class="label">Mínima</div><div class="value">{min_t:.0f}°C</div></div>
                <div><div class="label">Máxima</div><div class="value">{max_t:.0f}°C</div></div>
                <div><div class="label">Chuva</div><div class="value">{precip:.0f}%</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Polymarket
        event_url = f"https://polymarket.com/event/{slug}"
        if markets:
            st.markdown(f"**📊 Polymarket** · [ver mercado]({event_url})")
            m = markets[0]
            if m["outcomes"] and m["prices"]:
                pairs = sorted(zip(m["outcomes"], m["prices"]), key=lambda x: x[1], reverse=True)
                max_p = max(m["prices"])
                for outcome, price in pairs[:7]:
                    pct   = price * 100
                    color = "#6366f1" if price == max_p else "#3d4166"
                    st.markdown(f"""
                    <div class="odds-row">
                        <span style="font-size:13px;color:#e0e0e0;width:130px;flex-shrink:0">{outcome}</span>
                        <div class="odds-bar-bg"><div class="odds-bar" style="width:{pct}%;background:{color}"></div></div>
                        <span style="font-size:13px;font-weight:600;color:#a0a4c8;width:38px;text-align:right">{pct:.0f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                st.caption(f"Volume total: ${m['volume']:,.0f}")
        else:
            st.markdown(f"_Mercado não encontrado para esta data._ [Verificar no Polymarket]({event_url})")

        # AI
        verdict = ai_verdict(max_t, precip, markets or [])
        st.markdown(f"""
        <div class="ai-box">
            <div style="font-size:.75rem;color:#6366f1;font-weight:700;margin-bottom:.4rem">🤖 ANÁLISE</div>
            {verdict}
        </div>
        """, unsafe_allow_html=True)

        # 5-day
        if weather:
            st.markdown("**Próximos dias**")
            rows = []
            for d in weather["forecast"]["forecastday"]:
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

st.caption("Dados: WeatherAPI.com · Polymarket Gamma API · Não é conselho financeiro.")
