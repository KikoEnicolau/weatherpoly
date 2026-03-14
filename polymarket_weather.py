import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import json
import re
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

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
    .hourly-row { display:flex; gap:8px; overflow-x:auto; padding-bottom:4px; margin-bottom:.5rem; }
    .hour-box   { background:#12151f; border:1px solid #2d3147; border-radius:10px; padding:8px 10px; text-align:center; min-width:58px; flex-shrink:0; }
    .hour-time  { font-size:.7rem; color:#8b8fa8; margin-bottom:3px; }
    .hour-temp  { font-size:1rem; font-weight:600; color:#f0f0f0; }
    .hour-icon  { font-size:.9rem; margin-bottom:2px; }
    .hour-rain  { font-size:.68rem; color:#60a5fa; margin-top:2px; }
    .section-lbl{ font-size:.78rem; color:#8b8fa8; text-transform:uppercase; letter-spacing:.07em; margin:.8rem 0 .4rem; font-weight:600; }
    .bank-card  { background:#1a1d27; border:1px solid #2d3147; border-radius:14px; padding:1.2rem; margin-bottom:1rem; }
    .metric-box { background:#12151f; border-radius:10px; padding:.8rem 1rem; text-align:center; }
    .metric-val { font-size:1.5rem; font-weight:700; }
    .metric-lbl { font-size:.72rem; color:#8b8fa8; text-transform:uppercase; letter-spacing:.06em; margin-top:2px; }
    div[data-testid="stHorizontalBlock"] { gap: 1rem; }
</style>
""", unsafe_allow_html=True)

# ── Config ─────────────────────────────────────────────────────────────────────
WEATHER_API_KEY = st.secrets.get("WEATHER_API_KEY", "309038af8627473d88d130403261403")

CITIES = {
    "São Paulo":    {"lat":-23.55,"lon":-46.63,"poly":"sao-paulo",     "tz":"America/Sao_Paulo"},
    "Ankara":       {"lat":39.93, "lon":32.86, "poly":"ankara",        "tz":"Europe/Istanbul"},
    "London":       {"lat":51.51, "lon":-0.13, "poly":"london",        "tz":"Europe/London"},
    "Paris":        {"lat":48.85, "lon":2.35,  "poly":"paris",         "tz":"Europe/Paris"},
    "Seoul":        {"lat":37.57, "lon":126.98,"poly":"seoul",         "tz":"Asia/Seoul"},
    "New York":     {"lat":40.71, "lon":-74.01,"poly":"nyc",           "tz":"America/New_York"},
    "Chicago":      {"lat":41.88, "lon":-87.63,"poly":"chicago",       "tz":"America/Chicago"},
    "Dallas":       {"lat":32.78, "lon":-96.80,"poly":"dallas",        "tz":"America/Chicago"},
    "Miami":        {"lat":25.77, "lon":-80.19,"poly":"miami",         "tz":"America/New_York"},
    "Atlanta":      {"lat":33.75, "lon":-84.39,"poly":"atlanta",       "tz":"America/New_York"},
    "Seattle":      {"lat":47.61, "lon":-122.33,"poly":"seattle",      "tz":"America/Los_Angeles"},
    "Toronto":      {"lat":43.65, "lon":-79.38,"poly":"toronto",       "tz":"America/Toronto"},
    "Buenos Aires": {"lat":-34.60,"lon":-58.38,"poly":"buenos-aires",  "tz":"America/Argentina/Buenos_Aires"},
    "Wellington":   {"lat":-41.29,"lon":174.78,"poly":"wellington",    "tz":"Pacific/Auckland"},
}

# ── Bankroll storage (JSON file) ───────────────────────────────────────────────
BANK_FILE = "bankroll.json"

def load_bank():
    try:
        with open(BANK_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"entries": [], "banca_inicial": 100.0}

def save_bank(data):
    with open(BANK_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

# ── API calls ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_weather_realtime(lat, lon):
    url    = "http://api.weatherapi.com/v1/forecast.json"
    params = {"key": WEATHER_API_KEY, "q": f"{lat},{lon}", "days": 2, "aqi": "no", "alerts": "no"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=600)
def get_weather_forecast(lat, lon):
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
        rows = []
        for m in markets:
            prices = m.get("outcomePrices", "[]")
            if isinstance(prices, str):
                try: prices = [float(x) for x in json.loads(prices)]
                except: continue
            if len(prices) < 2:
                continue
            yes_price = prices[0]
            no_price  = prices[1]
            label     = m.get("groupItemTitle", "")
            nums      = re.findall(r'\d+', label)
            if not nums:
                continue
            rows.append({
                "label":     label,
                "question":  m.get("question", ""),
                "mkt_temp":  int(nums[0]),
                "yes_price": yes_price,
                "no_price":  no_price,
                "yes_c":     round(yes_price * 100),
                "no_c":      round(no_price * 100),
                "yes_pct":   round(yes_price * 100),
                "volume":    float(m.get("volume") or 0),
            })
        rows.sort(key=lambda x: x["mkt_temp"])
        return (rows if rows else None), slug
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

def local_time(tz_str):
    """Return current time formatted for a given timezone."""
    try:
        tz = ZoneInfo(tz_str)
        return datetime.now(tz).strftime("%H:%M")
    except Exception:
        return ""

def trend_arrow(current, forecast_max):
    if forecast_max > current + 2:  return "↗️"
    if forecast_max < current - 2:  return "↘️"
    return "→"

def build_hourly_html(hours, current_hour):
    boxes = []
    for h in hours:
        t      = datetime.strptime(h["time"], "%Y-%m-%d %H:%M")
        hr     = t.hour
        temp   = h["temp_c"]
        rain   = h["chance_of_rain"]
        icon   = weather_icon(h["condition"]["code"])
        is_now = (hr == current_hour)
        border = "border:1.5px solid #6366f1;" if is_now else ""
        now_lbl= '<div style="font-size:.6rem;color:#6366f1;font-weight:700">AGORA</div>' if is_now else ""
        boxes.append(
            f'<div class="hour-box" style="{border}">'
            f'{now_lbl}<div class="hour-time">{t.strftime("%H:%M")}</div>'
            f'<div class="hour-icon">{icon}</div>'
            f'<div class="hour-temp">{temp:.0f}°</div>'
            f'<div class="hour-rain">💧{rain:.0f}%</div></div>'
        )
    return f'<div class="hourly-row">{"".join(boxes)}</div>'

def score_rows(rows, max_t, precip):
    """
    Score rows prioritizing NÃO.
    NÃO: any outcome where forecast clearly says it WON'T happen.
      Best NÃO = yes_price is still high enough to give good NÃO payout,
                 AND temp is far enough from forecast to be confident.
    SIM: only when forecast matches closely AND market is underpricing.
    """
    eff_max  = max_t - 1.0 if precip >= 50 else max_t
    frounded = round(eff_max)
    scored   = []

    for r in rows:
        dist = r["mkt_temp"] - frounded  # positive = above forecast

        # ── NÃO scoring (priority) ──
        # Sweet spot: yes_price between 10-60¢ (market overpricing something unlikely)
        # dist >= 2 or dist <= -2 → forecast clearly contradicts
        # dist == 1 with rain → rain makes it unlikely
        # dist == -1 without rain → unlikely to go below forecast
        if dist >= 2:
            # Clearly above forecast → strong NÃO
            # More value if yes_price is high (bigger NÃO payout)
            if r["yes_price"] >= 0.10:
                nao_value = (3 + min(dist, 4)) * r["yes_price"]
                scored.append({**r, "action": "NÃO", "buy_c": r["no_c"],
                               "payout": 100 - r["no_c"], "dist": dist,
                               "value": nao_value, "reason": "nao_above"})
        elif dist <= -2:
            # Clearly below forecast → strong NÃO
            if r["yes_price"] >= 0.10:
                nao_value = (3 + min(abs(dist), 4)) * r["yes_price"]
                scored.append({**r, "action": "NÃO", "buy_c": r["no_c"],
                               "payout": 100 - r["no_c"], "dist": dist,
                               "value": nao_value, "reason": "nao_below"})
        elif dist == 1 and precip >= 40:
            # 1° above forecast + rain → unlikely
            if r["yes_price"] >= 0.15:
                nao_value = 2.5 * r["yes_price"]
                scored.append({**r, "action": "NÃO", "buy_c": r["no_c"],
                               "payout": 100 - r["no_c"], "dist": dist,
                               "value": nao_value, "reason": "nao_rain"})
        elif dist == -1 and precip < 30:
            # 1° below forecast, dry day → unlikely to be lower
            if r["yes_price"] >= 0.15:
                nao_value = 2.0 * r["yes_price"]
                scored.append({**r, "action": "NÃO", "buy_c": r["no_c"],
                               "payout": 100 - r["no_c"], "dist": dist,
                               "value": nao_value, "reason": "nao_below_dry"})

        # ── SIM scoring (only when clearly better than NÃO) ──
        elif dist == 0 and r["yes_price"] < 0.55:
            # Exact match AND market underpricing
            sim_value = 2.5 * (1 - r["yes_price"])
            scored.append({**r, "action": "SIM", "buy_c": r["yes_c"],
                           "payout": 100 - r["yes_c"], "dist": dist,
                           "value": sim_value, "reason": "sim_exact"})
        elif dist == -1 and precip >= 50:
            # Rain pulls max down → SIM on lower temp
            sim_value = 2.0 * (1 - r["yes_price"])
            scored.append({**r, "action": "SIM", "buy_c": r["yes_c"],
                           "payout": 100 - r["yes_c"], "dist": dist,
                           "value": sim_value, "reason": "sim_rain_low"})

    # Sort by value descending
    scored.sort(key=lambda x: -x["value"])
    return scored, frounded, eff_max

def ai_analysis(today_max, today_precip, tmrw_max, tmrw_precip,
                today_rows, tmrw_rows, today_date, tmrw_date,
                today_slug="", tmrw_slug=""):
    sections = []

    for label, date, max_t, precip, rows, slug in [
        ("HOJE",   today_date, today_max, today_precip, today_rows,  today_slug),
        ("AMANHÃ", tmrw_date,  tmrw_max,  tmrw_precip,  tmrw_rows,   tmrw_slug),
    ]:
        event_url = f"https://polymarket.com/event/{slug}"
        rain_note = f" · ⚠️ {precip:.0f}% chuva" if precip >= 40 else ""
        header    = f"<b>{label} — {date.strftime('%d/%m')} · Previsão: {max_t:.1f}°C{rain_note}</b>"

        if not rows:
            sections.append(
                f"{header}<br><span style='color:#8b8fa8;font-size:.84rem'>Nenhum mercado ativo. "
                f"<a href='{event_url}' style='color:#6366f1'>Verificar no Polymarket ↗</a></span>"
            )
            continue

        scored, frounded, eff_max = score_rows(rows, max_t, precip)

        # Table — all rows
        trows = ""
        top2_temps = {r["mkt_temp"] for r in scored[:2]}
        for r in rows:
            is_best = r["mkt_temp"] in top2_temps
            bg   = "background:#1e2035;" if is_best else ""
            fw   = "600" if is_best else "400"
            star = "⭐ " if is_best else "&nbsp;&nbsp;&nbsp;"
            trows += (
                f"<tr style='{bg}'>"
                f"<td style='padding:5px 8px;color:#e0e0e0;font-weight:{fw}'>{star}{r['label']}</td>"
                f"<td style='padding:5px 8px;text-align:center;color:#8b8fa8'>{r['yes_pct']:.0f}%</td>"
                f"<td style='padding:5px 8px;text-align:center;color:#4ade80'>Yes {r['yes_c']}¢</td>"
                f"<td style='padding:5px 8px;text-align:center;color:#f87171'>No {r['no_c']}¢</td>"
                f"</tr>"
            )

        table_html = (
            f"<table style='width:100%;border-collapse:collapse;font-size:.82rem;margin:.5rem 0'>"
            f"<thead><tr style='border-bottom:1px solid #2d3147'>"
            f"<th style='padding:4px 8px;text-align:left;color:#8b8fa8;font-weight:500'>Temp</th>"
            f"<th style='padding:4px 8px;text-align:center;color:#8b8fa8;font-weight:500'>Prob.</th>"
            f"<th style='padding:4px 8px;text-align:center;color:#8b8fa8;font-weight:500'>Buy Yes</th>"
            f"<th style='padding:4px 8px;text-align:center;color:#8b8fa8;font-weight:500'>Buy No</th>"
            f"</tr></thead><tbody>{trows}</tbody></table>"
            f"<div style='font-size:.75rem;margin-bottom:.6rem'>"
            f"<a href='{event_url}' style='color:#6366f1'>Abrir no Polymarket ↗</a></div>"
        )

        # Picks
        def explain(p):
            badge = "sim-badge" if p["action"] == "SIM" else "nao-badge"
            reason_map = {
                "nao_above":    f"Forecast aponta {eff_max:.1f}°C — {p['mkt_temp']}°C está {abs(p['dist'])}°C acima. Mercado dá {p['yes_pct']:.0f}% mas improvável.",
                "nao_below":    f"Forecast aponta {eff_max:.1f}°C — {p['mkt_temp']}°C está {abs(p['dist'])}°C abaixo. Mercado dá {p['yes_pct']:.0f}% mas improvável.",
                "nao_rain":     f"Forecast {eff_max:.1f}°C + {precip:.0f}% chuva deve segurar a máxima abaixo de {p['mkt_temp']}°C.",
                "nao_below_dry":f"Dia seco com previsão de {eff_max:.1f}°C — {p['mkt_temp']}°C abaixo do esperado.",
                "sim_exact":    f"Previsão bate exato em {frounded}°C — mercado a {p['yes_pct']:.0f}%, subprecificado.",
                "sim_rain_low": f"Com {precip:.0f}% de chuva, máxima deve cair para {p['mkt_temp']}°C.",
            }
            why = reason_map.get(p.get("reason",""), f"Distância de {abs(p['dist'])}°C da previsão.")
            return (
                f"<div style='display:flex;align-items:center;gap:10px;margin:.35rem 0'>"
                f"<span style='font-size:1rem;font-weight:700;color:#f0f0f0'>{p['label']}</span>"
                f"<span class='{badge}'>{p['action']}</span>"
                f"<span style='color:#8b8fa8;font-size:.82rem'>{p['buy_c']}¢ → lucro {p['payout']}¢</span>"
                f"</div>"
                f"<span style='font-size:.84rem;color:#a0a4c8'>{why}</span>"
            )

        top2      = scored[:2]
        lbl_txt   = "Melhor entrada" if len(top2) == 1 else "2 melhores entradas"
        picks_html = (
            f"<div style='margin:.6rem 0 .3rem'><span style='font-size:.75rem;color:#8b8fa8;"
            f"text-transform:uppercase;letter-spacing:.06em'>{lbl_txt}</span></div>"
        )
        for i, p in enumerate(top2):
            if i > 0:
                picks_html += "<div style='border-top:1px solid #2d3147;margin:.5rem 0'></div>"
            picks_html += explain(p)

        if not top2:
            picks_html += "<span style='color:#8b8fa8;font-size:.84rem'>Nenhuma entrada com valor claro identificada.</span>"

        sections.append(f"{header}{table_html}{picks_html}")

    return "<br><br>".join(sections)

# ── Bankroll simulator ─────────────────────────────────────────────────────────
def render_bankroll():
    st.markdown("## 💰 Simulador de Banca")
    st.caption("Registre suas entradas e acompanhe lucro/perda nos últimos 7 dias.")

    bank = load_bank()
    entries = bank.get("entries", [])

    # Filter last 7 days
    cutoff  = datetime.now() - timedelta(days=7)
    entries = [e for e in entries if datetime.fromisoformat(e["data"]) >= cutoff]
    bank["entries"] = entries

    # ── Summary metrics ──
    total_apostado = sum(e["valor"] for e in entries)
    total_lucro    = sum(e["resultado"] for e in entries if e["status"] == "Ganhou")
    total_perda    = sum(e["valor"] for e in entries if e["status"] == "Perdeu")
    saldo          = total_lucro - total_perda
    n_ganhou       = sum(1 for e in entries if e["status"] == "Ganhou")
    n_perdeu       = sum(1 for e in entries if e["status"] == "Perdeu")
    n_aberto       = sum(1 for e in entries if e["status"] == "Aberto")
    taxa_acerto    = (n_ganhou / (n_ganhou + n_perdeu) * 100) if (n_ganhou + n_perdeu) > 0 else 0

    saldo_color = "#4ade80" if saldo >= 0 else "#f87171"
    saldo_sign  = "+" if saldo >= 0 else ""

    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:1rem">
        <div class="metric-box">
            <div class="metric-val" style="color:{saldo_color}">{saldo_sign}${saldo:.2f}</div>
            <div class="metric-lbl">Saldo 7 dias</div>
        </div>
        <div class="metric-box">
            <div class="metric-val" style="color:#4ade80">${total_lucro:.2f}</div>
            <div class="metric-lbl">Total ganho</div>
        </div>
        <div class="metric-box">
            <div class="metric-val" style="color:#f87171">${total_perda:.2f}</div>
            <div class="metric-lbl">Total perdido</div>
        </div>
        <div class="metric-box">
            <div class="metric-val" style="color:#a0a4c8">{taxa_acerto:.0f}%</div>
            <div class="metric-lbl">Taxa de acerto · {n_ganhou}G {n_perdeu}P {n_aberto}A</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Add new entry ──
    with st.expander("➕ Registrar nova entrada", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            cidade_inp  = st.selectbox("Cidade", list(CITIES.keys()), key="bk_city")
            temp_inp    = st.text_input("Temperatura apostada (ex: 13°C)", key="bk_temp")
        with col2:
            acao_inp    = st.selectbox("Ação", ["NÃO", "SIM"], key="bk_acao")
            valor_inp   = st.number_input("Valor apostado ($)", min_value=0.01, value=10.0, step=0.01, key="bk_valor")
        with col3:
            preco_inp   = st.number_input("Preço de compra (¢)", min_value=1, max_value=99, value=30, key="bk_preco")
            data_inp    = st.date_input("Data do mercado", value=datetime.today().date(), key="bk_data")

        lucro_potencial = round(valor_inp * (100 - preco_inp) / preco_inp, 2)
        st.caption(f"Lucro potencial se ganhar: **${lucro_potencial}** · Retorno: **{(100-preco_inp)/preco_inp*100:.0f}%**")

        if st.button("Salvar entrada", key="bk_save"):
            if temp_inp:
                nova = {
                    "id":        len(entries) + 1,
                    "data":      datetime.now().isoformat(),
                    "data_mkt":  str(data_inp),
                    "cidade":    cidade_inp,
                    "temp":      temp_inp,
                    "acao":      acao_inp,
                    "valor":     valor_inp,
                    "preco_c":   preco_inp,
                    "lucro_pot": lucro_potencial,
                    "resultado": 0.0,
                    "status":    "Aberto",
                }
                bank["entries"].append(nova)
                save_bank(bank)
                st.success("Entrada salva!")
                st.rerun()

    # ── Entries table ──
    if entries:
        st.markdown('<div class="section-lbl">📋 Histórico (7 dias)</div>', unsafe_allow_html=True)

        for e in reversed(entries):
            status_color = {"Ganhou": "#4ade80", "Perdeu": "#f87171", "Aberto": "#a0a4c8"}.get(e["status"], "#a0a4c8")
            resultado_str = f"+${e['resultado']:.2f}" if e["status"] == "Ganhou" else f"-${e['valor']:.2f}" if e["status"] == "Perdeu" else "—"
            resultado_color = "#4ade80" if e["status"] == "Ganhou" else "#f87171" if e["status"] == "Perdeu" else "#8b8fa8"

            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1, 1, 1.5])
                with c1:
                    st.markdown(f"**{e['cidade']}** · {e['temp']} · {e['acao']}")
                    st.caption(f"{e['data_mkt']} · comprou {e['preco_c']}¢ · apostou ${e['valor']:.2f}")
                with c2:
                    st.markdown(f"<span style='color:{resultado_color};font-weight:700;font-size:1.1rem'>{resultado_str}</span>", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"<span style='color:{status_color};font-size:.85rem;font-weight:600'>{e['status']}</span>", unsafe_allow_html=True)
                with c4:
                    # Update result buttons
                    if e["status"] == "Aberto":
                        if st.button("✅ Ganhou", key=f"win_{e['id']}"):
                            for entry in bank["entries"]:
                                if entry["id"] == e["id"]:
                                    entry["status"]    = "Ganhou"
                                    entry["resultado"] = entry["lucro_pot"]
                            save_bank(bank)
                            st.rerun()
                with c5:
                    if e["status"] == "Aberto":
                        if st.button("❌ Perdeu", key=f"lose_{e['id']}"):
                            for entry in bank["entries"]:
                                if entry["id"] == e["id"]:
                                    entry["status"]    = "Perdeu"
                                    entry["resultado"] = 0.0
                            save_bank(bank)
                            st.rerun()
                    if st.button("🗑️", key=f"del_{e['id']}"):
                        bank["entries"] = [x for x in bank["entries"] if x["id"] != e["id"]]
                        save_bank(bank)
                        st.rerun()
                st.divider()

        # ── Daily chart ──
        if len([e for e in entries if e["status"] != "Aberto"]) > 0:
            st.markdown('<div class="section-lbl">📈 Resultado por dia</div>', unsafe_allow_html=True)
            daily = {}
            for e in entries:
                if e["status"] == "Aberto":
                    continue
                d = e["data_mkt"]
                if d not in daily:
                    daily[d] = 0.0
                if e["status"] == "Ganhou":
                    daily[d] += e["resultado"]
                else:
                    daily[d] -= e["valor"]

            df_chart = pd.DataFrame([
                {"Data": k, "Resultado ($)": round(v, 2)}
                for k, v in sorted(daily.items())
            ])
            st.bar_chart(df_chart.set_index("Data"))
    else:
        st.info("Nenhuma entrada registrada ainda. Adicione sua primeira entrada acima!")

# ── Main UI ────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🌡️ Análise de Mercados", "💰 Simulador de Banca"])

with tab1:
    st.markdown("## 🌡️ Polymarket Weather Tracker")
    st.caption("Temperatura em tempo real · Previsão hora a hora · Análise NÃO/SIM para os mercados Polymarket")
    st.divider()

    c1, c2, c3 = st.columns([3, 1, 1])
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
        st.info("Selecione pelo menos uma cidade.")
        st.stop()

    st.divider()

    today     = datetime.today().date()
    tomorrow  = today + timedelta(days=1)
    now_hour  = datetime.now().hour
    cols      = st.columns(2)

    for i, city in enumerate(selected):
        cfg = CITIES[city]
        with cols[i % 2]:
            with st.spinner(f"Carregando {city}..."):
                wdata         = get_weather_realtime(cfg["lat"], cfg["lon"])
                forecast_data = get_weather_forecast(cfg["lat"], cfg["lon"])
                today_mkts, today_slug = get_polymarket(cfg["poly"], today)
                tmrw_mkts,  tmrw_slug  = get_polymarket(cfg["poly"], tomorrow)

            if not wdata:
                st.error(f"Erro ao carregar dados de {city}"); continue

            current  = wdata["current"]
            cur_temp = current["temp_c"]
            cur_feel = current["feelslike_c"]
            cur_cond = current["condition"]["text"]
            cur_icon = weather_icon(current["condition"]["code"])
            cur_wind = current["wind_kph"]
            cur_hum  = current["humidity"]

            today_day  = wdata["forecast"]["forecastday"][0]["day"]
            today_max  = today_day["maxtemp_c"]
            today_min  = today_day["mintemp_c"]
            today_rain = today_day["daily_chance_of_rain"]

            tmrw_day  = wdata["forecast"]["forecastday"][1]["day"] if len(wdata["forecast"]["forecastday"]) > 1 else today_day
            tmrw_max  = tmrw_day["maxtemp_c"]
            tmrw_min  = tmrw_day["mintemp_c"]
            tmrw_rain = tmrw_day["daily_chance_of_rain"]

            city_time = local_time(cfg["tz"])
            arrow = trend_arrow(cur_temp, today_max)

            # Current conditions card
            st.markdown(f"""
            <div class="city-card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem">
                    <div>
                        <div style="font-size:1.15rem;font-weight:700;color:#f0f0f0;margin-bottom:4px">
                            {cur_icon} {city} &nbsp;<span class="now-badge">AO VIVO</span>
                        </div>
                        <div class="label">{cur_cond} · 🕐 {city_time} (horário local)</div>
                    </div>
                    <div style="text-align:right">
                        <div class="temp-big">{cur_temp:.1f}°C {arrow}</div>
                        <div class="temp-feel">Sensação {cur_feel:.0f}°C</div>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem">
                    <div><div class="label">Máx hoje</div><div class="value">{today_max:.0f}°C</div></div>
                    <div><div class="label">Mín hoje</div><div class="value">{today_min:.0f}°C</div></div>
                    <div><div class="label">Umidade</div><div class="value">{cur_hum}%</div></div>
                    <div><div class="label">Vento</div><div class="value">{cur_wind:.0f} km/h</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Hourly
            st.markdown('<div class="section-lbl">⏱ Hoje — hora a hora</div>', unsafe_allow_html=True)
            st.markdown(build_hourly_html(wdata["forecast"]["forecastday"][0]["hour"], now_hour), unsafe_allow_html=True)

            if len(wdata["forecast"]["forecastday"]) > 1:
                st.markdown('<div class="section-lbl">📅 Amanhã — hora a hora</div>', unsafe_allow_html=True)
                st.markdown(build_hourly_html(wdata["forecast"]["forecastday"][1]["hour"], -1), unsafe_allow_html=True)

            # Analysis
            st.markdown('<div class="section-lbl">🤖 Análise — melhores entradas</div>', unsafe_allow_html=True)
            analysis = ai_analysis(
                today_max, today_rain, tmrw_max, tmrw_rain,
                today_mkts, tmrw_mkts,
                today, tomorrow,
                today_slug, tmrw_slug,
            )
            st.markdown(f'<div class="ai-box">{analysis}</div>', unsafe_allow_html=True)

            # 5-day
            if forecast_data:
                st.markdown('<div class="section-lbl">📆 Próximos 5 dias</div>', unsafe_allow_html=True)
                rows_5d = []
                for d in forecast_data["forecast"]["forecastday"]:
                    dt = datetime.strptime(d["date"], "%Y-%m-%d")
                    rows_5d.append({
                        "Dia":   dt.strftime("%a %d/%m"),
                        "":      weather_icon(d["day"]["condition"]["code"]),
                        "Máx":   f"{d['day']['maxtemp_c']:.0f}°C",
                        "Mín":   f"{d['day']['mintemp_c']:.0f}°C",
                        "Chuva": f"{d['day']['daily_chance_of_rain']:.0f}%",
                    })
                st.dataframe(pd.DataFrame(rows_5d), use_container_width=True, hide_index=True)

            st.divider()

    st.caption("Dados: WeatherAPI.com · Polymarket Gamma API · Atualiza a cada 5 min · Não é conselho financeiro.")

with tab2:
    render_bankroll()
