import streamlit as st
from groq import Groq
from tavily import TavilyClient
import datetime
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(
    page_title="Midday Market Update",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
:root {
    --bg:#0a0d12; --surface:#111620; --border:#1e2736;
    --accent:#00d4ff; --accent2:#0077ff;
    --positive:#00e5a0; --negative:#ff4060;
    --warn:#f6c90e;
    --text:#e2e8f0; --subtext:#8899aa;
}
html,body,[data-testid="stAppViewContainer"]{background-color:var(--bg)!important;font-family:'IBM Plex Sans',sans-serif;color:var(--text);}
[data-testid="stHeader"]{background:transparent!important;}
.header-bar{display:flex;align-items:center;justify-content:space-between;padding:18px 0 10px 0;border-bottom:1px solid var(--border);margin-bottom:28px;}
.header-logo{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:3px;color:var(--accent);text-transform:uppercase;}
.header-date{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--subtext);letter-spacing:1px;}
.stButton>button{background:linear-gradient(135deg,var(--accent2),var(--accent))!important;color:#000!important;font-family:'IBM Plex Mono',monospace!important;font-weight:600!important;font-size:13px!important;letter-spacing:2px!important;text-transform:uppercase!important;border:none!important;border-radius:4px!important;padding:12px 32px!important;width:100%!important;transition:opacity 0.2s!important;}
.stButton>button:hover{opacity:0.85!important;}
[data-testid="stTextInput"] input{background:var(--surface)!important;border:1px solid var(--border)!important;color:var(--text)!important;font-family:'IBM Plex Mono',monospace!important;font-size:13px!important;border-radius:4px!important;}
[data-testid="stSidebar"]{background:var(--surface)!important;border-right:1px solid var(--border)!important;}
label,.stTextInput label{color:var(--subtext)!important;font-size:12px!important;letter-spacing:1px;}
hr{border-color:var(--border)!important;}
.report-output h3{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:2px;color:var(--accent);text-transform:uppercase;margin-top:24px;margin-bottom:8px;border-bottom:1px solid var(--border);padding-bottom:6px;}
.report-output p{margin-bottom:10px;}
.report-output strong{color:#fff;}
.src-card{background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:10px 14px;margin-bottom:6px;}
.src-card.ok{border-left:3px solid var(--positive);}
.src-card.skip{border-left:3px solid var(--negative);opacity:0.55;}
.src-title{font-family:'IBM Plex Sans',sans-serif;font-size:13px;font-weight:500;color:var(--text);margin-bottom:3px;}
.src-url{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--accent);word-break:break-all;}
.src-meta{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--subtext);margin-top:3px;}
.section-label{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:2px;color:var(--subtext);text-transform:uppercase;margin-bottom:8px;margin-top:20px;}
.key-ok{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--positive);margin-bottom:6px;}
.key-missing{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--negative);margin-bottom:4px;}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
TZ_CDMX   = datetime.timezone(datetime.timedelta(hours=-6))
NOW       = datetime.datetime.now(TZ_CDMX)
TODAY     = NOW.date()
TODAY_STR = TODAY.strftime("%d de %B de %Y")
TODAY_ISO = TODAY.isoformat()

TRUSTED_US = ["cnbc.com","bloomberg.com","reuters.com","wsj.com","ft.com"]
TRUSTED_MX = ["elfinanciero.com.mx","eleconomista.com.mx"]

CNBC_URL = "https://www.cnbc.com/market-insider/?&qsearchterm=STOCKS%20MAKING"
BMV_URL  = "https://www.bmv.com.mx/es/sala-de-prensa"
BIVA_URL = "https://www.biva.mx/empresas/eventos_relevantes"

HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

SEARCH_QUERIES = [
    {"label":"Movers EE.UU.",      "query":f"stocks biggest moves midday {TODAY.strftime('%B %d %Y')}",                     "domains":TRUSTED_US},
    {"label":"Macro / Fed",        "query":f"federal reserve inflation rates economy {TODAY.strftime('%B %d %Y')}",          "domains":TRUSTED_US},
    {"label":"S&P 500 / Nasdaq",   "query":f"S&P 500 Nasdaq market performance {TODAY.strftime('%B %d %Y')}",               "domains":TRUSTED_US},
    {"label":"Earnings / Corp US", "query":f"earnings results corporate guidance {TODAY.strftime('%B %d %Y')}",              "domains":TRUSTED_US},
    {"label":"IPC / Bolsa MX",     "query":f"Mexico IPC bolsa indice sectores {TODAY.strftime('%d %B %Y')}",                "domains":TRUSTED_MX},
    {"label":"Peso / Banxico",     "query":f"peso dolar tipo cambio Banxico tasas {TODAY.strftime('%d %B %Y')}",             "domains":TRUSTED_MX},
    {"label":"Economia MX",        "query":f"economia Mexico SHCP politica fiscal {TODAY.strftime('%d %B %Y')}",             "domains":TRUSTED_MX},
    {"label":"Emisoras MX",        "query":f"emisoras IPC resultados noticias corporativas Mexico {TODAY.strftime('%d %B %Y')}", "domains":TRUSTED_MX},
]

# ── Key resolution ────────────────────────────────────────────────────────────
def resolve_key(secret_name: str, fallback: str) -> str:
    try:
        v = st.secrets.get(secret_name, "")
        if v: return v.strip()
    except Exception:
        pass
    return fallback.strip()

# ── Date helpers ──────────────────────────────────────────────────────────────
def is_today(date_str: str) -> bool:
    if not date_str or not date_str.strip():
        return False
    s = date_str.lower()
    checks = [
        TODAY_ISO,
        TODAY.strftime("%B %d, %Y").lower(),
        TODAY.strftime("%b %d, %Y").lower(),
        TODAY.strftime("%d/%m/%Y"),
        TODAY.strftime("%m/%d/%Y"),
        TODAY.strftime("%d de %B de %Y").lower(),
    ]
    return any(c in s for c in checks)

# ── Scrapers ──────────────────────────────────────────────────────────────────
def fetch_cnbc_movers() -> dict:
    result = {"label":"CNBC — Stocks Making the Biggest Moves Midday",
              "url":CNBC_URL, "articles":[], "found":False, "error":""}
    try:
        resp = requests.get(CNBC_URL, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(resp.text, "html.parser")
        found_url, found_title = None, None
        for tag in soup.find_all("a", href=True):
            text = tag.get_text(strip=True)
            href = tag["href"]
            if re.search(r"biggest moves|biggest movers|midday", text, re.I):
                if not href.startswith("http"):
                    href = "https://www.cnbc.com" + href
                found_url, found_title = href, text
                break
        if found_url:
            art  = requests.get(found_url, headers=HEADERS, timeout=12)
            asoup = BeautifulSoup(art.text, "html.parser")
            paras = [p.get_text(strip=True) for p in asoup.find_all("p") if len(p.get_text(strip=True)) > 40]
            content = " ".join(paras[:40])
            result["articles"].append({"title": found_title or "CNBC Movers",
                                        "url": found_url, "date": TODAY_ISO,
                                        "content": content[:5000]})
            result["found"] = True
        else:
            result["error"] = "No se encontro articulo de movers del dia."
    except Exception as e:
        result["error"] = str(e)
    return result

def fetch_direct(label: str, url: str) -> dict:
    result = {"label": label, "url": url, "articles": [], "found": False}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(resp.text, "html.parser")
        texts = []
        for tag in soup.find_all(["article","li","div"],
                                  class_=re.compile(r"news|noticia|press|item|card|event|evento|row", re.I)):
            t = tag.get_text(separator=" ", strip=True)
            if len(t) > 50:
                texts.append(t[:500])
        if not texts:
            texts = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 50]
        if texts:
            result["articles"].append({"title": label, "url": url,
                                        "date": TODAY_ISO, "content": "\n".join(texts[:6])})
            result["found"] = True
    except Exception as e:
        result["articles"].append({"title": label, "url": url,
                                    "date": TODAY_ISO, "content": f"Error: {e}"})
    return result

def run_tavily(tavily_key: str) -> list:
    client = TavilyClient(api_key=tavily_key)
    blocks = []
    for sq in SEARCH_QUERIES:
        block = {"label": sq["label"], "articles": [], "skipped": 0, "no_date": 0}
        try:
            resp = client.search(
                query=sq["query"],
                search_depth="advanced",
                max_results=6,
                include_answer=False,
                include_domains=sq["domains"],
            )
            for r in resp.get("results", []):
                pub = r.get("published_date", "") or ""
                if not pub.strip():
                    block["no_date"] += 1
                    continue
                if not is_today(pub):
                    block["skipped"] += 1
                    continue
                block["articles"].append({
                    "title":   r.get("title", "Sin titulo"),
                    "url":     r.get("url", ""),
                    "date":    pub,
                    "content": r.get("content", "")[:600],
                })
        except Exception as e:
            block["error"] = str(e)
        blocks.append(block)
    return blocks

# ── Context builder ───────────────────────────────────────────────────────────
def build_context(tavily: list, cnbc: dict, bmv: dict, biva: dict) -> str:
    parts = []

    parts.append("=== CNBC — STOCKS MAKING THE BIGGEST MOVES MIDDAY ===")
    for a in cnbc["articles"]:
        parts.append(f"URL: {a['url']}\nFECHA: {a['date']}\n{a['content']}")
    if cnbc["error"]:
        parts.append(f"NOTA: {cnbc['error']}")

    for block in tavily:
        if not block["articles"]:
            continue
        parts.append(f"\n=== {block['label'].upper()} ===")
        for a in block["articles"]:
            parts.append(f"TITULO: {a['title']}\nFECHA: {a['date']}\nURL: {a['url']}\nCONTENIDO: {a['content']}\n---")

    parts.append(f"\n=== BMV SALA DE PRENSA ===\nURL: {bmv['url']}")
    for a in bmv["articles"]:
        parts.append(a["content"])

    parts.append(f"\n=== BIVA EVENTOS RELEVANTES ===\nURL: {biva['url']}")
    for a in biva["articles"]:
        parts.append(a["content"])

    return "\n".join(parts)

# ── Prompt ────────────────────────────────────────────────────────────────────
def build_prompt(context: str) -> str:
    return f"""Hoy es {TODAY_STR}. Son las {NOW.strftime('%H:%M')} hora Ciudad de Mexico.

Eres analista senior de Equity Sales & Trading en una mesa institucional mexicana de capitales.
Tus clientes son AFORES y aseguradoras con exposicion en renta variable MX (IPC) y EE.UU. (S&P 500, Nasdaq).
Redacta el Midday Market Update. Idioma: espanol. Tono: institucional, tecnico, directo.
USA UNICAMENTE la informacion del contexto. No inventes cifras ni precios.

=== CONTEXTO DE NOTICIAS DEL DIA ===
{context}
=== FIN CONTEXTO ===

Construye el reporte en este orden exacto, con estos encabezados:

---

### LECTURA EJECUTIVA
Tres lineas fijas:
- Market Sentiment: [Extreme Fear / Fear / Neutral / Greed / Extreme Greed]
- Driver dominante: [frase corta — el factor que mas mueve el mercado hoy]
- Niveles de referencia: S&P 500 [nivel/variacion%] | IPC [nivel/variacion%] | USD/MXN [nivel/variacion%]
Luego una sola frase de lectura institucional del mercado en este momento.

---

### MOVERS EE.UU.
Fuente: articulo CNBC del dia. Incluye TODAS las acciones mencionadas con movimiento relevante.
Formato por entrada:
**TICKER**, Nombre Empresa — [sube/baja] X.X%
[30-50 palabras: razon del movimiento, contexto y relevancia para un portafolio institucional. Monedas con US$. Punto en decimales.]

---

### PANORAMA IPC
NO es una lista de movers. Es un analisis del indice como conjunto. Incluye:
- Nivel y variacion del IPC en el dia
- Sectores que lideran y sectores que rezagan
- Breadth del mercado (mayoria de emisoras al alza o a la baja)
- Una lectura cualitativa sobre el tono del mercado local
Si una emisora especifica tiene noticia concreta que explique su movimiento, puedes mencionarla aqui.
Maximo 5-6 lineas. Redaccion de parrafo, no lista de tickers.

---

### NOTICIAS EE.UU.
TODAS las noticias relevantes del contexto US que impacten flujos de capital, politica monetaria, datos macro o resultados sistemicos.
Sin limite de bullets. Formato:
**TEMA / TICKER:** hecho concreto del dia + implicacion directa para mercados en 30-50 palabras.

---

### NOTICIAS MEXICO
TODAS las noticias relevantes del contexto MX, BMV y BIVA que impacten IPC, tipo de cambio, tasas o flujos.
Sin limite de bullets. Formato:
**TEMA / TICKER:** hecho concreto del dia + implicacion directa para mercados en 30-50 palabras.

---

### FLUJOS Y POSICIONAMIENTO INSTITUCIONAL
Infiere con base en TODAS las noticias del contexto. No inventes datos, solo lectura cualitativa:
- Flujos locales: [comportamiento implicito de inversionistas institucionales MX]
- Flujos extranjeros: [lectura de entrada/salida de capital foraneo a MX]
- SIC: [comportamiento implicito del mercado internacional de capitales desde Mexico]
- Renta fija local: [lectura de tasas y postura de Banxico si hay evidencia]

---

### IDEA DE MESA
Una o dos frases maximo. No solo el sesgo — incluye el instrumento o segmento accionable y la razon.
Ejemplo de formato: "Sesgo defensivo ante [razon]: favorecemos [segmento/emisora/indice] sobre [alternativa]."

---

REGLAS FINALES:
- Si una noticia no cambia decisiones de inversion hoy, se omite.
- Sin relleno ni repeticion entre secciones.
- Tono de mesa institucional en todo momento.
- Cada seccion debe aportar informacion nueva, no repetir lo de la anterior."""

# ── Groq ──────────────────────────────────────────────────────────────────────
def generate(groq_key: str, context: str) -> str:
    client = Groq(api_key=groq_key)
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role":"system","content":"Eres analista senior de Equity Sales & Trading en una mesa institucional mexicana de capitales. Redactas midday market updates en espanol para AFORES y aseguradoras con exposicion en renta variable MX y US. Usas UNICAMENTE el contexto proporcionado. Tono institucional, tecnico, directo."},
            {"role":"user","content":build_prompt(context)},
        ],
        temperature=0.2,
        max_tokens=3500,
    )
    return resp.choices[0].message.content

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="header-bar">
    <div class="header-logo">&#9632; Midday Market Update</div>
    <div class="header-date">{NOW.strftime("%A, %d %b %Y")} &bull; {NOW.strftime("%H:%M")} CDMX</div>
</div>""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:10px;letter-spacing:2px;color:#8899aa;text-transform:uppercase;margin-bottom:12px;">API Keys</div>', unsafe_allow_html=True)

    try:
        groq_in_secrets   = bool(st.secrets.get("GROQ_API_KEY",""))
        tavily_in_secrets = bool(st.secrets.get("TAVILY_API_KEY",""))
    except Exception:
        groq_in_secrets = tavily_in_secrets = False

    if groq_in_secrets:
        st.markdown('<div class="key-ok">&#10003; GROQ_API_KEY — Secrets</div>', unsafe_allow_html=True)
        groq_input = ""
    else:
        st.markdown('<div class="key-missing">&#9888; GROQ_API_KEY no configurada</div>', unsafe_allow_html=True)
        groq_input = st.text_input("Groq API Key", type="password", placeholder="gsk_...", help="console.groq.com")

    if tavily_in_secrets:
        st.markdown('<div class="key-ok">&#10003; TAVILY_API_KEY — Secrets</div>', unsafe_allow_html=True)
        tavily_input = ""
    else:
        st.markdown('<div class="key-missing">&#9888; TAVILY_API_KEY no configurada</div>', unsafe_allow_html=True)
        tavily_input = st.text_input("Tavily API Key", type="password", placeholder="tvly-...", help="app.tavily.com")

    st.markdown("---")
    st.markdown("""<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5568;line-height:2.0;">
<b style="color:#8899aa">Estructura del reporte</b><br>
1. Lectura Ejecutiva<br>
2. Movers EE.UU.<br>
3. Panorama IPC<br>
4. Noticias EE.UU.<br>
5. Noticias Mexico<br>
6. Flujos Institucionales<br>
7. Idea de Mesa<br><br>
<b style="color:#8899aa">Fuentes</b><br>
CNBC &bull; Bloomberg &bull; Reuters<br>
WSJ &bull; FT &bull; El Financiero<br>
El Economista &bull; BMV &bull; BIVA<br><br>
<b style="color:#8899aa">Filtro</b><br>
Solo noticias con fecha = hoy<br>
Sin fecha = descartada
</div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""<div style="font-family:IBM Plex Mono,monospace;font-size:9px;color:#2d3748;line-height:1.7;">
Secrets permanentes:<br>
Streamlit Cloud &rarr; Settings<br>
&rarr; Secrets<br>
GROQ_API_KEY = "gsk_..."<br>
TAVILY_API_KEY = "tvly-..."
</div>""", unsafe_allow_html=True)

# ── Button ────────────────────────────────────────────────────────────────────
col_btn, _ = st.columns([1, 2])
with col_btn:
    run = st.button("Generar Midday Update")

for key in ["report","sources","error"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ── Pipeline ──────────────────────────────────────────────────────────────────
if run:
    gk = resolve_key("GROQ_API_KEY",   groq_input)
    tk = resolve_key("TAVILY_API_KEY", tavily_input)

    if not gk or not tk:
        st.error("Faltan API keys. Configuralas en Streamlit Secrets o ingrésalas manualmente.")
    else:
        for key in ["report","sources","error"]:
            st.session_state[key] = None

        with st.spinner("Extrayendo CNBC Movers..."):
            cnbc = fetch_cnbc_movers()

        with st.spinner("Extrayendo BMV y BIVA..."):
            bmv  = fetch_direct("BMV Sala de Prensa", BMV_URL)
            biva = fetch_direct("BIVA Eventos Relevantes", BIVA_URL)

        with st.spinner("Buscando noticias del dia (Tavily)..."):
            try:
                tavily = run_tavily(tk)
            except Exception as e:
                st.session_state.error = f"Error Tavily: {e}"
                tavily = []

        st.session_state.sources = {"cnbc":cnbc,"bmv":bmv,"biva":biva,"tavily":tavily}

        with st.spinner("Redactando reporte (Groq — llama-3.3-70b)..."):
            try:
                ctx    = build_context(tavily, cnbc, bmv, biva)
                report = generate(gk, ctx)
                st.session_state.report = report
            except Exception as e:
                st.session_state.error = f"Error Groq: {e}"

if st.session_state.error:
    st.error(st.session_state.error)

# ── Display ───────────────────────────────────────────────────────────────────
if st.session_state.report and st.session_state.sources:
    src = st.session_state.sources

    # Metrics
    total_ok = sum(len(b.get("articles",[])) for b in src["tavily"])
    total_ok += len(src["cnbc"]["articles"])
    total_skip   = sum(b.get("skipped",0)  for b in src["tavily"])
    total_nodate = sum(b.get("no_date",0)  for b in src["tavily"])

    st.markdown('<div class="section-label">Fuentes procesadas</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Noticias aceptadas hoy", total_ok)
    c2.metric("Descartadas (fecha vieja)", total_skip)
    c3.metric("Descartadas (sin fecha)", total_nodate)

    # Sources expander
    with st.expander("Ver fuentes y links", expanded=False):
        # CNBC
        for a in src["cnbc"]["articles"]:
            st.markdown(f"""<div class="src-card ok">
                <div class="src-title">{a['title']}</div>
                <div class="src-url"><a href="{a['url']}" target="_blank">{a['url']}</a></div>
                <div class="src-meta">CNBC &bull; {a['date']}</div>
            </div>""", unsafe_allow_html=True)
        if src["cnbc"]["error"]:
            st.markdown(f'<div class="src-card skip"><div class="src-title">CNBC: {src["cnbc"]["error"]}</div><div class="src-url"><a href="{CNBC_URL}" target="_blank">{CNBC_URL}</a></div></div>', unsafe_allow_html=True)

        # Tavily
        for block in src["tavily"]:
            for a in block["articles"]:
                st.markdown(f"""<div class="src-card ok">
                    <div class="src-title">{a['title']}</div>
                    <div class="src-url"><a href="{a['url']}" target="_blank">{a['url']}</a></div>
                    <div class="src-meta">{block['label']} &bull; {a['date']}</div>
                </div>""", unsafe_allow_html=True)
            skip = block.get("skipped",0) + block.get("no_date",0)
            if skip:
                st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#ff4060;margin-bottom:4px;">&#9888; {block["label"]}: {skip} resultado(s) descartado(s)</div>', unsafe_allow_html=True)

        # BMV / BIVA
        for s in [src["bmv"], src["biva"]]:
            st.markdown(f"""<div class="src-card ok">
                <div class="src-title">{s['label']}</div>
                <div class="src-url"><a href="{s['url']}" target="_blank">{s['url']}</a></div>
                <div class="src-meta">{TODAY_ISO}</div>
            </div>""", unsafe_allow_html=True)

    # Report
    st.markdown('<div class="section-label" style="margin-top:28px;">Reporte institucional</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5568;margin-bottom:14px;">{NOW.strftime("%H:%M")} CDMX &nbsp;&bull;&nbsp; llama-3.3-70b &nbsp;&bull;&nbsp; {total_ok} fuentes &nbsp;&bull;&nbsp; AFORES / Aseguradoras</div>', unsafe_allow_html=True)

    st.markdown('<div class="report-output">', unsafe_allow_html=True)
    st.markdown(st.session_state.report)
    st.markdown('</div>', unsafe_allow_html=True)

    # Copy box
    st.markdown("---")
    st.markdown('<div class="section-label">Texto plano para Canva</div>', unsafe_allow_html=True)
    st.text_area("", value=st.session_state.report, height=260,
                 label_visibility="collapsed", key="plain_copy")
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5568;">Clic &rarr; Ctrl+A &rarr; Ctrl+C &rarr; pegar en Canva</div>', unsafe_allow_html=True)

else:
    keys_ready = groq_in_secrets and tavily_in_secrets
    st.markdown(f"""
    <div style="margin-top:60px;text-align:center;">
        <div style="font-size:40px;margin-bottom:16px;">📊</div>
        <div style="font-family:IBM Plex Mono,monospace;font-size:12px;letter-spacing:2px;color:#4a5568;text-transform:uppercase;">
            {'Keys configuradas &mdash; listo para generar' if keys_ready else 'Configura tus API keys y presiona Generar'}
        </div>
        <div style="font-family:IBM Plex Sans,sans-serif;font-size:12px;color:#2d3748;margin-top:12px;line-height:2;">
            1. Lectura Ejecutiva &nbsp;&bull;&nbsp; 2. Movers EE.UU. &nbsp;&bull;&nbsp; 3. Panorama IPC<br>
            4. Noticias EE.UU. &nbsp;&bull;&nbsp; 5. Noticias Mexico &nbsp;&bull;&nbsp; 6. Flujos Institucionales &nbsp;&bull;&nbsp; 7. Idea de Mesa
        </div>
    </div>""", unsafe_allow_html=True)
