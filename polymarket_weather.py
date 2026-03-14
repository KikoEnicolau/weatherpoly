import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Polymarket Weather Tracker",
    page_icon="🌡️",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .city-card {
        background: #1a1d27;
        border: 1px solid #2d3147;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .temp-big { font-size: 2.2rem; font-weight: 700; color: #f0f0f0; }
    .label { font-size: 0.75rem; color: #8b8fa8; text-transform: uppercase; letter-spacing: 0.08em; }
    .value { font-size: 1rem; font-weight: 600; color: #e0e0e0; }
    .badge-yes  { background:#1a3a2a; color:#4ade80; border-radius:6px; padding:2px 10px; font-size:0.82rem; font-weight:600; }
    .badge-no   { background:#3a1a1a; color:#f87171; border-radius:6px; padding:2px 10px; font-size:0.82rem; font-weight:600; }
    .badge-neutral { background:#2a2a3a; color:#a0a0c0; border-radius:6px; padding:2px 10px; font-size:0.82rem; font-weight:600; }
    .ai-box { background:#12151f; border-left:3px solid #6366f1; border-radius:0 8px 8px 0; padding:0.8rem 1rem; margin-top:0.8rem; font-size:0.88rem; color:#c0c4d8; line-height:1.6; }
    .section-header { font-size:1.5rem; font-weight:700; color:#f0f0f0; margin-bottom:0.5rem; }
    .stProgress > div > div > div { background-color: #6366f1; }
    hr { border-color: #2d3147; }
</style>
""", unsafe_allow_html=True)

# ── Cities config ─────────────────────────────────────────────────────────────
CITIES = {
    "Ankara":       {"lat": 39.93,  "lon":  32.86,  "tz": "Europe/Istanbul",                      "poly_name": "Ankara"},
    "London":       {"lat": 51.51,  "lon":  -0.13,  "tz": "Europe/London",                        "poly_name": "London"},
    "Paris":        {"lat": 48.85,  "lon":   2.35,  "tz": "Europe/Paris",                         "poly_name": "Paris"},
    "Seoul":        {"lat": 37.57,  "lon": 126.98,  "tz": "Asia/Seoul",                           "poly_name": "Seoul"},
    "New York":     {"lat": 40.71,  "lon": -74.01,  "tz": "America/New_York",                     "poly_name": "NYC"},
    "Chicago":      {"lat": 41.88,  "lon": -87.63,  "tz": "America/Chicago",                      "poly_name": "Chicago"},
    "Dallas":       {"lat": 32.78,  "lon": -96.80,  "tz": "America/Chicago",                      "poly_name": "Dallas"},
    "Miami":        {"lat": 25.77,  "lon": -80.19,  "tz": "America/New_York",                     "poly_name": "Miami"},
    "Atlanta":      {"lat": 33.75,  "lon": -84.39,  "tz": "America/New_York",                     "poly_name": "Atlanta"},
    "Seattle":      {"lat": 47.61,  "lon": -122.33, "tz": "America/Los_Angeles",                  "poly_name": "Seattle"},
    "Toronto":      {"lat": 43.65,  "lon": -79.38,  "tz": "America/Toronto",                      "poly_name": "Toronto"},
    "Buenos Aires": {"lat": -34.60, "lon": -58.38,  "tz": "America/Argentina/Buenos_Aires",       "poly_name": "Buenos Aires"},
    "São Paulo":    {"lat": -23.55, "lon": -46.63,  "tz": "America/Sao_Paulo",                    "poly_name": "Sao Paulo"},
    "Wellington":   {"lat": -41.29, "lon": 174.78,  "tz": "Pacific/Auckland",                     "poly_name": "Wellington"},
}

# ── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_weather(lat, lon, tz):
    """Fetch 5-day forecast from Open-Meteo (free, no key needed)."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
        "timezone": tz,
        "forecast_days": 5,
    }
    try:
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=300)
def get_polymarket_odds(city_name, poly_name, target_date):
    """Search Polymarket Gamma API for temperature markets for a city."""
    # Try multiple search strategies
    search_queries = [
        f"highest temperature in {poly_name.lower()}",
        f"temperature {poly_name.lower()}",
        poly_name.lower(),
    ]
    url = "https://gamma-api.polymarket.com/markets"

    results = []
    seen = set()

    for search_query in search_queries:
        params = {
            "active": "true",
            "limit": 30,
            "order": "volume24hr",
            "ascending": "false",
            "q": search_query,
        }
        try:
            r = requests.get(url, params=params, timeout=8)
            r.raise_for_status()
            markets = r.json()
            for m in markets:
                q = m.get("question", "").lower()
                slug = m.get("slug", "")
                if slug in seen:
                    continue
                # Match city name (handle both "São Paulo" and "Sao Paulo")
                city_lower = poly_name.lower()
                if city_lower not in q and city_lower.replace(" ", "-") not in slug:
                    continue
                if "temperature" not in q and "highest" not in q:
                    continue
                # Filter by date if possible
                date_str = target_date.strftime("%B %-d").lower()
                date_str2 = target_date.strftime("%B %d").lower()
                if date_str not in q and date_str2 not in q:
                    continue
                seen.add(slug)
                outcomes = m.get("outcomes", "[]")
                prices   = m.get("outcomePrices", "[]")
                if isinstance(outcomes, str):
                    import json
                    try:
                        outcomes = json.loads(outcomes)
                        prices   = json.loads(prices)
                    except Exception:
                        outcomes, prices = [], []
                results.append({
                    "question": m.get("question", ""),
                    "volume":   float(m.get("volume24hr") or 0),
                    "outcomes": outcomes,
                    "prices":   [float(p) for p in prices],
                    "url":      f"https://polymarket.com/event/{slug}",
                })
        except Exception:
            continue

    return results

def weather_icon(code):
    if code == 0:            return "☀️"
    elif code in (1,2,3):    return "⛅"
    elif code in range(45,68): return "🌧️"
    elif code in range(71,78): return "❄️"
    elif code in range(80,83): return "🌦️"
    elif code in range(95,100): return "⛈️"
    return "🌤️"

def ai_analysis(city, forecast_max, forecast_min, precip_pct, polymarket_data):
    """Simple rule-based analysis — no external API needed."""
    lines = []

    if not polymarket_data:
        return "Nenhum mercado Polymarket ativo encontrado para essa cidade hoje."

    for market in polymarket_data[:2]:
        q = market["question"]
        outcomes = market["outcomes"]
        prices   = market["prices"]

        if not outcomes or not prices:
            continue

        # Find the highest-probability outcome
        if prices:
            best_idx  = prices.index(max(prices))
            best_out  = outcomes[best_idx] if best_idx < len(outcomes) else "?"
            best_prob = max(prices) * 100

        lines.append(f"**Mercado:** {q}")

        # Try to parse the temperature value from the question
        import re
        match = re.search(r'(\d+)°?[Cc]', q)
        if match:
            mkt_temp = int(match.group(1))
            diff = forecast_max - mkt_temp
            if abs(diff) <= 0.5:
                verdict = "✅ **Previsão alinhada com o mercado** — apostar em SIM pode ter valor."
            elif diff > 0.5:
                verdict = f"⚠️ Previsão ({forecast_max:.0f}°C) está **acima** do mercado ({mkt_temp}°C) — o resultado pode ser um valor maior, NÃO pode ter valor."
            else:
                verdict = f"⚠️ Previsão ({forecast_max:.0f}°C) está **abaixo** do mercado ({mkt_temp}°C) — NÃO pode ter valor."
        else:
            verdict = f"Favorito do mercado: **{best_out}** ({best_prob:.0f}%)"

        # Rain adjustment
        if precip_pct >= 50:
            lines.append(f"🌧️ {precip_pct}% de chance de chuva — tende a reduzir a máxima.")
        elif precip_pct >= 25:
            lines.append(f"🌂 {precip_pct}% de chance de chuva — leve pressão de baixa na temperatura.")

        lines.append(verdict)
        lines.append("")

    return "\n".join(lines) if lines else "Análise indisponível."

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("## 🌡️ Polymarket Weather Tracker")
st.markdown("Previsão do tempo + odds do Polymarket + análise de IA para os mercados de temperatura.")
st.divider()

# Controls
col_date, col_cities, col_refresh = st.columns([2, 3, 1])
with col_date:
    target_date = st.date_input(
        "Data do mercado",
        value=datetime.today().date() + timedelta(days=1),
        min_value=datetime.today().date(),
        max_value=datetime.today().date() + timedelta(days=4),
    )
with col_cities:
    selected = st.multiselect(
        "Cidades",
        options=list(CITIES.keys()),
        default=["Ankara", "London", "New York", "São Paulo"],
    )
with col_refresh:
    st.write("")
    st.write("")
    refresh = st.button("🔄 Atualizar", use_container_width=True)

if refresh:
    st.cache_data.clear()

if not selected:
    st.info("Selecione pelo menos uma cidade acima.")
    st.stop()

st.divider()

# Grid: 2 columns
cols = st.columns(2)

for i, city in enumerate(selected):
    cfg = CITIES[city]
    with cols[i % 2]:
        weather = get_weather(cfg["lat"], cfg["lon"], cfg["tz"])
        poly    = get_polymarket_odds(city, cfg["poly_name"], target_date)

        # Find index for target_date in weather data
        today_idx = 1  # default to tomorrow
        if weather and "daily" in weather:
            dates = weather["daily"].get("time", [])
            target_str = str(target_date)
            if target_str in dates:
                today_idx = dates.index(target_str)
            else:
                # fallback: use index 1 (tomorrow)
                today_idx = min(1, len(dates) - 1)

        if weather:
            daily    = weather["daily"]
            max_t    = daily["temperature_2m_max"][today_idx]
            min_t    = daily["temperature_2m_min"][today_idx]
            precip   = daily["precipitation_probability_max"][today_idx]
            wcode    = daily["weathercode"][today_idx]
            icon     = weather_icon(wcode)
        else:
            max_t = min_t = precip = 0
            icon = "❓"

        # Card header
        st.markdown(f"""
        <div class="city-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
                <div>
                    <div style="font-size:1.1rem; font-weight:700; color:#f0f0f0;">{icon} {city}</div>
                    <div class="label">{target_date.strftime('%d/%m/%Y')}</div>
                </div>
                <div class="temp-big">{max_t:.0f}°C</div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.5rem; margin-bottom:0.8rem;">
                <div>
                    <div class="label">Mínima</div>
                    <div class="value">{min_t:.0f}°C</div>
                </div>
                <div>
                    <div class="label">Máxima</div>
                    <div class="value">{max_t:.0f}°C</div>
                </div>
                <div>
                    <div class="label">Chuva</div>
                    <div class="value">{precip:.0f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Polymarket odds
        if poly:
            st.markdown(f"**📊 Mercados Polymarket** — {len(poly)} encontrado(s)")
            for mkt in poly[:3]:
                with st.expander(mkt["question"][:80] + "...", expanded=False):
                    if mkt["outcomes"] and mkt["prices"]:
                        df = pd.DataFrame({
                            "Resultado": mkt["outcomes"],
                            "Probabilidade": [f"{p*100:.0f}%" for p in mkt["prices"]],
                            "Preço ($)": [f"${p:.2f}" for p in mkt["prices"]],
                        })
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    st.caption(f"Volume 24h: ${mkt['volume']:,.0f} · [Abrir no Polymarket]({mkt['url']})")
        else:
            st.markdown("_Nenhum mercado ativo encontrado no Polymarket para esta data._")

        # AI analysis
        analysis = ai_analysis(city, max_t, min_t, precip, poly)
        st.markdown(f"""
        <div class="ai-box">
        <div style="font-size:0.75rem; color:#6366f1; font-weight:700; margin-bottom:0.4rem;">🤖 ANÁLISE</div>
        {analysis.replace(chr(10), '<br>')}
        </div>
        """, unsafe_allow_html=True)

        # 5-day mini forecast
        if weather:
            st.markdown("**Próximos 5 dias**")
            dates  = weather["daily"]["time"]
            maxes  = weather["daily"]["temperature_2m_max"]
            mins   = weather["daily"]["temperature_2m_min"]
            wcodes = weather["daily"]["weathercode"]
            rows   = []
            for d, mx, mn, wc in zip(dates[:5], maxes[:5], mins[:5], wcodes[:5]):
                dt = datetime.strptime(d, "%Y-%m-%d")
                rows.append({
                    "Dia": dt.strftime("%a %d/%m"),
                    "": weather_icon(wc),
                    "Máx": f"{mx:.0f}°C",
                    "Mín": f"{mn:.0f}°C",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.divider()

# Footer
st.markdown("""
<div style="text-align:center; color:#444; font-size:0.8rem; margin-top:2rem;">
Dados: <a href="https://open-meteo.com" style="color:#6366f1;">Open-Meteo</a> · 
<a href="https://polymarket.com" style="color:#6366f1;">Polymarket Gamma API</a> · 
Atualiza a cada 5–10 min · Não é conselho financeiro.
</div>
""", unsafe_allow_html=True)
