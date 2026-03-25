import streamlit as st
from openai import OpenAI
import datetime
import pyperclip

# ── Page config ──────────────────────────────────────────────────────────────
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

/* ── Header bar ── */
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

/* ── Generate button ── */
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
    cursor: pointer !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* ── Copy button special style ── */
.copy-btn > button {
    background: var(--surface) !important;
    color: var(--accent) !important;
    border: 1px solid var(--accent) !important;
    font-size: 11px !important;
    padding: 8px 20px !important;
    width: auto !important;
}

/* ── Report card ── */
.report-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 32px 36px;
    margin-top: 24px;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 14px;
    line-height: 1.75;
    color: var(--text);
    white-space: pre-wrap;
    word-break: break-word;
}

/* ── Section label pill ── */
.section-pill {
    display: inline-block;
    background: rgba(0,212,255,0.08);
    border: 1px solid rgba(0,212,255,0.25);
    border-radius: 3px;
    padding: 2px 10px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--accent);
    text-transform: uppercase;
    margin-bottom: 16px;
}

/* ── Status / info boxes ── */
.status-box {
    background: rgba(0,212,255,0.05);
    border-left: 3px solid var(--accent);
    padding: 12px 18px;
    border-radius: 0 4px 4px 0;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--subtext);
    margin-bottom: 12px;
}

/* ── Spinner override ── */
.stSpinner > div { border-top-color: var(--accent) !important; }

/* ── Text area (API key) ── */
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

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

/* ── Labels ── */
label, .stTextInput label { color: var(--subtext) !important; font-size: 12px !important; letter-spacing: 1px; }

/* ── Success/error messages ── */
.stSuccess { background: rgba(0,229,160,0.08) !important; border-left: 3px solid var(--positive) !important; }
.stError   { background: rgba(255,64,96,0.08)  !important; border-left: 3px solid var(--negative) !important; }

/* ── Markdown in report output ── */
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
.report-output p  { margin-bottom: 10px; }
.report-output strong { color: #fff; }
.report-output em { color: var(--subtext); }
</style>
""", unsafe_allow_html=True)

# ── Prompt template ───────────────────────────────────────────────────────────
def build_prompt(today_str: str) -> str:
    return f"""Hoy es {today_str}.

Actúa como analista senior de Equity Sales & Trading en una mesa institucional. Estoy preparando un Midday Market Update para AFORES e inversionistas institucionales, enviado por correo electrónico. Todo el contenido debe entregarse en español, con tono institucional, técnico y conciso, en máximo una página. Prioriza únicamente información que cambie decisiones de inversión hoy.

🔷 MODO DE TRABAJO (OBLIGATORIO)
Investiga automáticamente en internet las noticias financieras más recientes del día {today_str}. No solicites textos, URLs ni inputs manuales. Verifica que la información corresponda al día actual. Solo utiliza fuentes financieras reconocidas (CNBC, Bloomberg, Reuters, WSJ, FT, El Financiero, El Economista, BMV, Banxico, SHCP, etc.). Si no encuentras información del día, indícalo explícitamente. Entrega el resultado final completo sin pedir confirmaciones intermedias.

🔷 ESTRUCTURA DEL MIDDAY
Construye el reporte en este orden exacto:

### LECTURA EJECUTIVA
Determina el Market Sentiment (Extreme Fear / Fear / Neutral / Greed / Extreme Greed) con un marco tipo Fear & Greed basado en: reacción a resultados, tipo de movers (defensivos vs growth vs high beta), noticias dominantes, movimiento en tasas y dólar, amplitud del mercado, flujos implícitos. Incluye:
- Market Sentiment: [valor]
- Driver dominante: [frase corta]
- Lectura general: [1 frase institucional]

### MOVERS DEL DÍA
Busca el artículo más reciente del día tipo "Stocks making the biggest moves midday". Extrae todas las acciones mencionadas relevantes. Reglas editoriales obligatorias: cada párrafo inicia con **TICKER**, coma, nombre de empresa. Indica si subió o bajó y variación porcentual. Resume en menos de 30 palabras. Monedas inician con US$. Usa punto en lugar de coma en porcentajes. Negritas solo en el ticker. Elimina movimientos totalmente anecdóticos o irrelevantes.

### NOTICIAS EE.UU.
Máximo 3–4 bullets. Solo incluye noticias con impacto en: mercado, política monetaria, regulación, sentimiento de riesgo, datos macro relevantes, resultados corporativos sistémicos. Formato: TEMA / TICKER: hecho + implicación para mercado.

### NOTICIAS MÉXICO
Máximo 3–4 bullets. Prioriza: política económica, regulación, Banxico, SHCP, emisoras relevantes del IPC, flujos y mercado local, tipo de cambio y tasas locales. Formato: TEMA / TICKER: hecho + implicación para mercado.

### LECTURA DE FLUJOS
Describe brevemente: flujos institucionales locales, flujos extranjeros, movimiento en SIC, comportamiento en renta fija, lectura cualitativa institucional. Solo incluir si hay evidencia en fuentes del día.

### CIERRE
Una sola frase clara con sesgo esperado para la tarde (alcista, defensivo, volátil, rango, risk-off, etc.).

🔷 REGLA FINAL
Si una información no cambia decisiones hoy, se omite. No incluir relleno. No repetir información. No extender más de una página. Tono institucional. Lenguaje técnico claro. Orientado a mesa institucional."""

# ── Grok API call ─────────────────────────────────────────────────────────────
def generate_midday(api_key: str) -> str:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )
    today_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).strftime("%d de %B de %Y")
    prompt = build_prompt(today_str)

    response = client.chat.completions.create(
        model="grok-3",
        messages=[
            {
                "role": "system",
                "content": "Eres un analista senior de Equity Sales & Trading. Tienes acceso a internet y debes buscar noticias financieras del día en curso antes de responder. Responde siempre en español con tono institucional.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2500,
    )
    return response.choices[0].message.content

# ── App layout ────────────────────────────────────────────────────────────────
now_cdmx = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6)))

st.markdown(f"""
<div class="header-bar">
    <div class="header-logo">⬛ Midday Market Update</div>
    <div class="header-date">{now_cdmx.strftime("%A, %d %b %Y  •  %H:%M")} CDMX</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar: API key ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;letter-spacing:2px;color:#4a5568;text-transform:uppercase;margin-bottom:16px;">Configuración</div>', unsafe_allow_html=True)
    api_key_input = st.text_input(
        "xAI API KEY",
        type="password",
        placeholder="xai-...",
        help="Obtén tu key en console.x.ai",
    )
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#4a5568;line-height:1.6;">Modelo: grok-3<br>Búsqueda web: activa<br>Idioma: Español<br>Mercado: MX / US</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#4a5568;">Tu API key se usa solo en esta sesión y nunca se almacena.</div>', unsafe_allow_html=True)

# ── Main area ─────────────────────────────────────────────────────────────────
col_btn, col_spacer = st.columns([1, 2])
with col_btn:
    generate_btn = st.button("⚡  Generar Midday Update")

# ── State ─────────────────────────────────────────────────────────────────────
if "report" not in st.session_state:
    st.session_state.report = None
if "error" not in st.session_state:
    st.session_state.error = None

# ── Generate ──────────────────────────────────────────────────────────────────
if generate_btn:
    key = api_key_input.strip()
    if not key:
        st.error("Ingresa tu xAI API key en el panel lateral.")
    else:
        st.session_state.error = None
        with st.spinner("Consultando mercados y redactando reporte..."):
            try:
                report = generate_midday(key)
                st.session_state.report = report
            except Exception as e:
                st.session_state.error = str(e)
                st.session_state.report = None

# ── Display error ─────────────────────────────────────────────────────────────
if st.session_state.error:
    st.error(f"Error al conectar con Grok: {st.session_state.error}")

# ── Display report ────────────────────────────────────────────────────────────
if st.session_state.report:
    report_text = st.session_state.report

    # Copy button + timestamp
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:11px;color:#4a5568;margin-top:8px;">Generado {now_cdmx.strftime("%H:%M")} CDMX</div>', unsafe_allow_html=True)
    with col2:
        # Streamlit doesn't support native clipboard — use a text area trick
        copy_clicked = st.button("📋  Copiar texto")

    # Render report
    st.markdown('<div class="report-output">', unsafe_allow_html=True)
    st.markdown(report_text)
    st.markdown('</div>', unsafe_allow_html=True)

    # Hidden text area to enable easy copy
    st.markdown("---")
    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;letter-spacing:1px;color:#4a5568;margin-bottom:6px;">TEXTO PLANO PARA COPIAR → CANVA</div>', unsafe_allow_html=True)
    st.text_area(
        label="",
        value=report_text,
        height=220,
        label_visibility="collapsed",
        key="plain_text_output",
    )
    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#4a5568;">Selecciona todo el texto (Ctrl+A / Cmd+A) y copia.</div>', unsafe_allow_html=True)

else:
    # Empty state
    st.markdown("""
    <div style="margin-top:60px;text-align:center;">
        <div style="font-size:40px;margin-bottom:16px;">📊</div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:2px;color:#4a5568;text-transform:uppercase;">
            Ingresa tu API key y presiona Generar
        </div>
        <div style="font-family:'IBM Plex Sans',sans-serif;font-size:13px;color:#2d3748;margin-top:8px;">
            Grok buscará noticias del día en tiempo real
        </div>
    </div>
    """, unsafe_allow_html=True)
