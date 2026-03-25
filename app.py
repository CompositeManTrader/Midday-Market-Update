import streamlit as st
from groq import Groq
from tavily import TavilyClient
import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Midday Market Update",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg:       #0a0d12;
    --surface:  #111620;
    --border:   #1e2736;
    --accent:   #00d4ff;
    --accent2:  #0077ff;
    --positive: #00e5a0;
    --negative: #ff4060;
    --muted:    #4a5568;
    --text:     #e2e8f0;
    --subtext:  #8899aa;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    font-family: 'IBM Plex Sans', sans-serif;
    color: var(--text);
}
[data-testid="stHeader"] { background: transparent !important; }

.header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 0 10px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 28px;
}
.header-logo {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    letter-spacing: 3px;
    color: var(--accent);
    text-transform: uppercase;
}
.header-date {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: var(--subtext);
    letter-spacing: 1px;
}

.stButton > button {
    background: linear-gradient(135deg, var(--accent2), var(--accent)) !important;
    color: #000 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 12px 32px !important;
    width: 100% !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

.stSpinner > div { border-top-color: var(--accent) !important; }

[data-testid="stTextInput"] input {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 13px !important;
    border-radius: 4px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent) !important;
}

hr { border-color: var(--border) !important; }

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

label, .stTextInput label {
    color: var(--subtext) !important;
    font-size: 12px !important;
    letter-spacing: 1px;
}

.stSuccess { background: rgba(0,229,160,0.08) !important; border-left: 3px solid var(--positive) !important; }
.stError   { background: rgba(255,64,96,0.08)  !important; border-left: 3px solid var(--negative) !important; }

.report-output h3 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    letter-spacing: 2px;
    color: var(--accent);
    text-transform: uppercase;
    margin-top: 24px;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
}
.report-output p { margin-bottom: 10px; }
.report-output strong { color: #fff; }
</style>
""", unsafe_allow_html=True)

# ── Search queries ────────────────────────────────────────────────────────────
SEARCH_QUERIES = [
    "stocks biggest movers midday today",
    "US stock market news today macro fed",
    "S&P 500 Nasdaq market update today",
    "Mexico stock market IPC Banxico today",
    "peso dolar tipo de cambio hoy",
    "Mexico economia noticias financieras hoy",
]

# ── Tavily search ─────────────────────────────────────────────────────────────
def run_searches(tavily_key: str) -> str:
    client = TavilyClient(api_key=tavily_key)
    all_results = []

    for query in SEARCH_QUERIES:
        try:
            resp = client.search(
                query=query,
                search_depth="basic",
                max_results=4,
                include_answer=True,
            )
            block = f"\n\n### Busqueda: {query}\n"
            if resp.get("answer"):
                block += f"Resumen: {resp['answer']}\n"
            for r in resp.get("results", []):
                block += f"- [{r.get('title','')}] {r.get('content','')[:300]}\n"
            all_results.append(block)
        except Exception as e:
            all_results.append(f"\n### Busqueda: {query}\nError: {e}\n")

    return "\n".join(all_results)

# ── Build prompt ──────────────────────────────────────────────────────────────
def build_prompt(today_str: str, search_context: str) -> str:
    return f"""Hoy es {today_str}.

A continuacion tienes los resultados de busqueda web con las noticias financieras mas recientes del dia. Usalos como fuente principal para construir el reporte.

=== CONTEXTO DE BUSQUEDA ===
{search_context}
=== FIN CONTEXTO ===

Actua como analista senior de Equity Sales & Trading en una mesa institucional. Prepara un Midday Market Update para AFORES e inversionistas institucionales. Todo en espanol, tono institucional, tecnico y conciso, maximo una pagina. Prioriza unicamente informacion que cambie decisiones de inversion hoy.

Construye el reporte en este orden exacto:

### LECTURA EJECUTIVA
Determina el Market Sentiment (Extreme Fear / Fear / Neutral / Greed / Extreme Greed) basado en: reaccion a resultados, tipo de movers (defensivos vs growth vs high beta), noticias dominantes, movimiento en tasas y dolar, amplitud del mercado, flujos implicitos.
- Market Sentiment: [valor]
- Driver dominante: [frase corta]
- Lectura general: [1 frase institucional]

### MOVERS DEL DIA
Extrae las acciones con mayores movimientos del dia. Reglas: cada parrafo inicia con **TICKER**, coma, nombre. Indica si subio o bajo y variacion porcentual. Maximo 30 palabras por entrada. Monedas con US$. Punto en lugar de coma en porcentajes. Negritas solo en ticker.

### NOTICIAS EE.UU.
Maximo 3-4 bullets. Solo noticias con impacto en mercado, politica monetaria, datos macro, resultados sistemicos. Formato: TEMA / TICKER: hecho + implicacion.

### NOTICIAS MEXICO
Maximo 3-4 bullets. Prioriza: Banxico, SHCP, IPC, tipo de cambio, tasas locales, flujos. Formato: TEMA / TICKER: hecho + implicacion.

### LECTURA DE FLUJOS
Flujos institucionales locales, extranjeros, SIC, renta fija. Solo si hay evidencia en las busquedas.

### CIERRE
Una sola frase con sesgo esperado para la tarde (alcista, defensivo, volatil, rango, risk-off, etc.).

REGLA FINAL: Si una informacion no cambia decisiones hoy, se omite. Sin relleno. Sin repeticion. Tono institucional."""

# ── Groq inference ────────────────────────────────────────────────────────────
def generate_report(groq_key: str, search_context: str) -> str:
    client = Groq(api_key=groq_key)
    today_str = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=-6))
    ).strftime("%d de %B de %Y")

    prompt = build_prompt(today_str, search_context)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "Eres un analista senior de Equity Sales & Trading en una mesa institucional mexicana. Redactas reportes en espanol con tono tecnico e institucional, orientados a AFORES e inversionistas institucionales.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
    )
    return response.choices[0].message.content

# ── Layout ────────────────────────────────────────────────────────────────────
now_cdmx = datetime.datetime.now(
    datetime.timezone(datetime.timedelta(hours=-6))
)

st.markdown(f"""
<div class="header-bar">
    <div class="header-logo">&#9632; Midday Market Update</div>
    <div class="header-date">{now_cdmx.strftime("%A, %d %b %Y  &bull;  %H:%M")} CDMX</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:10px;letter-spacing:2px;color:#4a5568;text-transform:uppercase;margin-bottom:16px;">Configuracion</div>', unsafe_allow_html=True)

    groq_key = st.text_input("GROQ API KEY", type="password", placeholder="gsk_...", help="console.groq.com")
    tavily_key = st.text_input("TAVILY API KEY", type="password", placeholder="tvly-...", help="app.tavily.com")

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5568;line-height:1.8;">Modelo: llama-3.3-70b<br>Busquedas: Tavily (6)<br>Idioma: Espanol<br>Mercado: MX / US</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5568;">Las keys se usan solo en esta sesion y nunca se almacenan.</div>', unsafe_allow_html=True)

# ── Generate button ───────────────────────────────────────────────────────────
col_btn, col_spacer = st.columns([1, 2])
with col_btn:
    generate_btn = st.button("Generar Midday Update")

# ── Session state ─────────────────────────────────────────────────────────────
if "report" not in st.session_state:
    st.session_state.report = None
if "error" not in st.session_state:
    st.session_state.error = None

# ── Run pipeline ──────────────────────────────────────────────────────────────
if generate_btn:
    gk = groq_key.strip()
    tk = tavily_key.strip()

    if not gk or not tk:
        st.error("Ingresa ambas API keys en el panel lateral.")
    else:
        st.session_state.error = None
        st.session_state.report = None

        progress = st.empty()

        with progress.container():
            with st.spinner("Buscando noticias del dia (Tavily)..."):
                try:
                    search_context = run_searches(tk)
                except Exception as e:
                    st.session_state.error = f"Error en Tavily: {e}"
                    search_context = None

        if search_context:
            with progress.container():
                with st.spinner("Redactando reporte (Groq)..."):
                    try:
                        report = generate_report(gk, search_context)
                        st.session_state.report = report
                    except Exception as e:
                        st.session_state.error = f"Error en Groq: {e}"

        progress.empty()

# ── Display error ─────────────────────────────────────────────────────────────
if st.session_state.error:
    st.error(st.session_state.error)

# ── Display report ────────────────────────────────────────────────────────────
if st.session_state.report:
    report_text = st.session_state.report

    st.markdown(
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:11px;color:#4a5568;margin-bottom:16px;">'
        f'Generado {now_cdmx.strftime("%H:%M")} CDMX &nbsp;&bull;&nbsp; '
        f'Busquedas: {len(SEARCH_QUERIES)} &nbsp;&bull;&nbsp; Modelo: llama-3.3-70b</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="report-output">', unsafe_allow_html=True)
    st.markdown(report_text)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        '<div style="font-family:IBM Plex Mono,monospace;font-size:10px;letter-spacing:1px;color:#4a5568;margin-bottom:6px;">'
        'TEXTO PLANO PARA COPIAR A CANVA</div>',
        unsafe_allow_html=True,
    )
    st.text_area(
        label="",
        value=report_text,
        height=220,
        label_visibility="collapsed",
        key="plain_text_output",
    )
    st.markdown(
        '<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5568;">'
        'Clic en el cuadro de texto -> Ctrl+A -> Ctrl+C -> pegar en Canva.</div>',
        unsafe_allow_html=True,
    )

else:
    st.markdown("""
    <div style="margin-top:60px;text-align:center;">
        <div style="font-size:40px;margin-bottom:16px;">📊</div>
        <div style="font-family:IBM Plex Mono,monospace;font-size:12px;letter-spacing:2px;color:#4a5568;text-transform:uppercase;">
            Ingresa tus API keys y presiona Generar
        </div>
        <div style="font-family:IBM Plex Sans,sans-serif;font-size:13px;color:#2d3748;margin-top:10px;">
            Tavily buscara noticias del dia &middot; Groq redactara el reporte
        </div>
    </div>
    """, unsafe_allow_html=True)
