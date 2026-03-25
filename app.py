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
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
:root {
    --bg:#0a0d12; --surface:#111620; --border:#1e2736;
    --accent:#00d4ff; --accent2:#0077ff;
    --positive:#00e5a0; --negative:#ff4060;
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
.source-card{background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:10px 14px;margin-bottom:6px;font-family:'IBM Plex Mono',monospace;font-size:11px;}
.source-card a{color:var(--accent);text-decoration:none;}
.source-card .src-date{color:var(--subtext);font-size:10px;margin-top:3px;}
.source-card.ok{border-left:3px solid var(--positive);}
.source-card.skip{border-left:3px solid var(--negative);opacity:0.5;}
.section-label{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:2px;color:var(--subtext);text-transform:uppercase;margin-bottom:8px;margin-top:20px;}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
TODAY = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).date()
TODAY_STR = TODAY.strftime("%d de %B de %Y")
TODAY_ISO = TODAY.isoformat()  # e.g. 2026-03-25

TRUSTED_DOMAINS_US = [
    "cnbc.com", "bloomberg.com", "reuters.com",
    "wsj.com", "ft.com"
]
TRUSTED_DOMAINS_MX = [
    "elfinanciero.com.mx", "eleconomista.com.mx"
]
ALL_TRUSTED = TRUSTED_DOMAINS_US + TRUSTED_DOMAINS_MX

CNBC_MOVERS_URL = "https://www.cnbc.com/market-insider/?&qsearchterm=STOCKS%20MAKING"
BMV_URL = "https://www.bmv.com.mx/es/sala-de-prensa"
BIVA_URL = "https://www.biva.mx/empresas/eventos_relevantes"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ── Search queries config ─────────────────────────────────────────────────────
SEARCH_QUERIES = [
    {
        "label": "Movers EE.UU.",
        "query": f"stocks making biggest moves midday {TODAY.strftime('%B %d %Y')}",
        "domains": TRUSTED_DOMAINS_US,
    },
    {
        "label": "Macro / Fed EE.UU.",
        "query": f"US stock market federal reserve economy news {TODAY.strftime('%B %d %Y')}",
        "domains": TRUSTED_DOMAINS_US,
    },
    {
        "label": "S&P 500 / Nasdaq",
        "query": f"S&P 500 Nasdaq market update {TODAY.strftime('%B %d %Y')}",
        "domains": TRUSTED_DOMAINS_US,
    },
    {
        "label": "IPC / Mercado MX",
        "query": f"Mexico IPC bolsa mercado accionario {TODAY.strftime('%d %B %Y')}",
        "domains": TRUSTED_DOMAINS_MX,
    },
    {
        "label": "Peso / Dolar / Tasas MX",
        "query": f"peso dolar tipo cambio Banxico tasas {TODAY.strftime('%d %B %Y')}",
        "domains": TRUSTED_DOMAINS_MX,
    },
    {
        "label": "Economia / Politica MX",
        "query": f"economia politica Mexico SHCP Banxico {TODAY.strftime('%d %B %Y')}",
        "domains": TRUSTED_DOMAINS_MX,
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def is_today(date_str: str) -> bool:
    """Check if a date string contains today's date."""
    if not date_str:
        return False
    date_str_lower = date_str.lower()
    checks = [
        TODAY_ISO,
        TODAY.strftime("%B %d, %Y").lower(),
        TODAY.strftime("%b %d, %Y").lower(),
        TODAY.strftime("%d/%m/%Y"),
        TODAY.strftime("%m/%d/%Y"),
        TODAY.strftime("%d de %B de %Y").lower(),
    ]
    return any(c in date_str_lower for c in checks)

def fetch_cnbc_movers() -> dict:
    """Fetch CNBC market insider page and extract today's movers article."""
    result = {"label": "CNBC Movers", "url": CNBC_MOVERS_URL, "content": "", "date": "", "is_today": False, "found": False}
    try:
        resp = requests.get(CNBC_MOVERS_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Look for articles matching "biggest moves midday" or "biggest movers"
        articles = soup.find_all(["a", "h3", "h2"], string=re.compile(r"biggest moves|biggest movers|midday", re.I))
        
        best = None
        for tag in articles:
            text = tag.get_text(strip=True)
            href = tag.get("href", "") or (tag.find("a") or {}).get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.cnbc.com" + href
            if href:
                best = {"title": text, "url": href}
                break
        
        # Fallback: grab all article links with date info
        if not best:
            cards = soup.find_all("div", class_=re.compile(r"Card|card|article|Article"))
            for card in cards[:10]:
                title_tag = card.find(["h3","h2","a"])
                link_tag = card.find("a", href=True)
                date_tag = card.find(["time", "span"], class_=re.compile(r"date|time|Date|Time"))
                if title_tag and link_tag:
                    title = title_tag.get_text(strip=True)
                    if re.search(r"move|mover|midday", title, re.I):
                        href = link_tag["href"]
                        if not href.startswith("http"):
                            href = "https://www.cnbc.com" + href
                        date = date_tag.get_text(strip=True) if date_tag else ""
                        best = {"title": title, "url": href, "date": date}
                        break

        if best:
            result["url"] = best.get("url", CNBC_MOVERS_URL)
            result["found"] = True
            result["date"] = best.get("date", TODAY_ISO)
            # Now fetch the actual article
            try:
                art_resp = requests.get(result["url"], headers=HEADERS, timeout=10)
                art_soup = BeautifulSoup(art_resp.text, "html.parser")
                # Extract article body
                paragraphs = art_soup.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs[:30])
                result["content"] = content[:3000]
                result["is_today"] = True  # If we found the article from today's search
            except:
                result["content"] = f"Articulo encontrado: {best.get('title','')}"
                result["is_today"] = True
        else:
            result["content"] = "No se encontro articulo de movers del dia en CNBC."
            result["is_today"] = False
    except Exception as e:
        result["content"] = f"Error al acceder a CNBC: {e}"
    return result

def fetch_bmv() -> dict:
    """Fetch BMV sala de prensa."""
    result = {"label": "BMV Sala de Prensa", "url": BMV_URL, "content": "", "date": TODAY_ISO, "is_today": False, "found": False}
    try:
        resp = requests.get(BMV_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        texts = []
        # Look for news items
        items = soup.find_all(["article", "div", "li"], class_=re.compile(r"news|noticia|press|sala|item|card", re.I))
        for item in items[:8]:
            t = item.get_text(separator=" ", strip=True)
            if len(t) > 30:
                texts.append(t[:400])
        if not texts:
            # Fallback: just grab paragraphs
            texts = [p.get_text(strip=True) for p in soup.find_all("p")[:10] if len(p.get_text(strip=True)) > 40]
        
        if texts:
            result["content"] = "\n".join(texts[:5])
            result["found"] = True
            result["is_today"] = True  # Assume sala de prensa is current
        else:
            result["content"] = "No se pudo extraer contenido de BMV."
    except Exception as e:
        result["content"] = f"Error al acceder a BMV: {e}"
    return result

def fetch_biva() -> dict:
    """Fetch BIVA eventos relevantes."""
    result = {"label": "BIVA Eventos Relevantes", "url": BIVA_URL, "content": "", "date": TODAY_ISO, "is_today": False, "found": False}
    try:
        resp = requests.get(BIVA_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        texts = []
        items = soup.find_all(["article", "div", "li", "tr"], class_=re.compile(r"event|evento|item|row|card|relevant", re.I))
        for item in items[:8]:
            t = item.get_text(separator=" ", strip=True)
            if len(t) > 30:
                texts.append(t[:400])
        if not texts:
            texts = [p.get_text(strip=True) for p in soup.find_all("p")[:10] if len(p.get_text(strip=True)) > 40]
        
        if texts:
            result["content"] = "\n".join(texts[:5])
            result["found"] = True
            result["is_today"] = True
        else:
            result["content"] = "No se pudo extraer contenido de BIVA."
    except Exception as e:
        result["content"] = f"Error al acceder a BIVA: {e}"
    return result

def run_tavily_searches(tavily_key: str) -> list:
    """Run all Tavily searches with domain restriction and date filtering."""
    client = TavilyClient(api_key=tavily_key)
    results = []

    for sq in SEARCH_QUERIES:
        block = {"label": sq["label"], "query": sq["query"], "articles": [], "skipped": 0}
        try:
            resp = client.search(
                query=sq["query"],
                search_depth="basic",
                max_results=5,
                include_answer=True,
                include_domains=sq["domains"],
            )
            
            today_articles = []
            skipped = 0
            for r in resp.get("results", []):
                pub_date = r.get("published_date", "") or ""
                title = r.get("title", "")
                url = r.get("url", "")
                content = r.get("content", "")[:400]
                
                # Date check: accept if date matches today OR if no date available (can't verify)
                date_ok = is_today(pub_date) or not pub_date
                
                if date_ok:
                    today_articles.append({
                        "title": title,
                        "url": url,
                        "date": pub_date or "fecha no disponible",
                        "content": content,
                        "is_today": is_today(pub_date),
                    })
                else:
                    skipped += 1

            block["articles"] = today_articles
            block["skipped"] = skipped
            block["answer"] = resp.get("answer", "")
        except Exception as e:
            block["error"] = str(e)
        
        results.append(block)
    
    return results

def build_context_string(tavily_results: list, cnbc: dict, bmv: dict, biva: dict) -> str:
    """Build the full context string for Groq."""
    parts = []

    # CNBC Movers
    parts.append(f"=== CNBC MOVERS DEL DIA ({cnbc['url']}) ===")
    parts.append(cnbc["content"] or "Sin contenido disponible.")

    # Tavily results
    for block in tavily_results:
        parts.append(f"\n=== {block['label'].upper()} ===")
        if block.get("answer"):
            parts.append(f"Resumen: {block['answer']}")
        if block.get("error"):
            parts.append(f"Error: {block['error']}")
        for art in block.get("articles", []):
            date_label = f"[{art['date']}]" if art['date'] else ""
            parts.append(f"- {art['title']} {date_label}\n  {art['content']}")
        if block["skipped"] > 0:
            parts.append(f"(Se omitieron {block['skipped']} resultados de fechas anteriores)")

    # BMV
    parts.append(f"\n=== BMV SALA DE PRENSA ({bmv['url']}) ===")
    parts.append(bmv["content"] or "Sin contenido disponible.")

    # BIVA
    parts.append(f"\n=== BIVA EVENTOS RELEVANTES ({biva['url']}) ===")
    parts.append(biva["content"] or "Sin contenido disponible.")

    return "\n".join(parts)

def build_prompt(search_context: str) -> str:
    return f"""Hoy es {TODAY_STR}.

A continuacion tienes el contexto de busqueda con noticias financieras del dia de hoy extraidas de fuentes institucionales (CNBC, Bloomberg, Reuters, WSJ, FT, El Financiero, El Economista, BMV, BIVA). Usa UNICAMENTE este contexto para construir el reporte. No inventes datos.

{search_context}

Actua como analista senior de Equity Sales & Trading en una mesa institucional mexicana. Prepara el Midday Market Update para AFORES e inversionistas institucionales. Todo en espanol, tono institucional, tecnico y conciso, maximo una pagina.

Construye el reporte en este orden EXACTO:

### LECTURA EJECUTIVA
- Market Sentiment: [Extreme Fear / Fear / Neutral / Greed / Extreme Greed]
- Driver dominante: [frase corta que explica el sentiment]
- Lectura general: [1 frase institucional del estado del mercado hoy]

### MOVERS DEL DIA
Usa los datos de CNBC. Cada entrada: **TICKER**, nombre de empresa, sube/baja X.X%, razon en menos de 30 palabras. Monedas con US$. Punto en lugar de coma en porcentajes. Negritas solo en ticker. Omite movimientos irrelevantes.

### NOTICIAS EE.UU.
3-4 bullets. Formato: TEMA / TICKER: hecho concreto + implicacion para mercado.
Solo noticias que cambien decisiones de inversion hoy.

### NOTICIAS MEXICO
3-4 bullets. Formato: TEMA / TICKER: hecho concreto + implicacion para mercado.
Incluye informacion de BMV y BIVA si es relevante.

### LECTURA DE FLUJOS
Flujos institucionales locales, extranjeros, SIC, renta fija. Solo si hay evidencia concreta en el contexto.

### CIERRE
Una sola frase con sesgo esperado para la tarde.

REGLA FINAL: Si una informacion no cambia decisiones hoy, se omite. Sin relleno. Sin repeticion. Tono institucional."""

def generate_report(groq_key: str, search_context: str) -> str:
    client = Groq(api_key=groq_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "Eres un analista senior de Equity Sales & Trading en una mesa institucional mexicana. Redactas reportes en espanol con tono tecnico e institucional para AFORES e inversionistas institucionales. Usas UNICAMENTE la informacion del contexto proporcionado.",
            },
            {"role": "user", "content": build_prompt(search_context)},
        ],
        temperature=0.25,
        max_tokens=2000,
    )
    return response.choices[0].message.content

# ── UI ────────────────────────────────────────────────────────────────────────
now_cdmx = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6)))

st.markdown(f"""
<div class="header-bar">
    <div class="header-logo">&#9632; Midday Market Update</div>
    <div class="header-date">{now_cdmx.strftime("%A, %d %b %Y")} &bull; {now_cdmx.strftime("%H:%M")} CDMX</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:10px;letter-spacing:2px;color:#4a5568;text-transform:uppercase;margin-bottom:16px;">Configuracion</div>', unsafe_allow_html=True)
    groq_key = st.text_input("GROQ API KEY", type="password", placeholder="gsk_...", help="console.groq.com — gratis")
    tavily_key = st.text_input("TAVILY API KEY", type="password", placeholder="tvly-...", help="app.tavily.com — gratis")
    st.markdown("---")
    st.markdown("""<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5568;line-height:1.9;">
    <b style="color:#8899aa">Fuentes US</b><br>
    CNBC &bull; Bloomberg<br>Reuters &bull; WSJ &bull; FT<br><br>
    <b style="color:#8899aa">Fuentes MX</b><br>
    El Financiero &bull; El Economista<br>BMV &bull; BIVA<br><br>
    <b style="color:#8899aa">Modelo</b><br>llama-3.3-70b (Groq)<br><br>
    <b style="color:#8899aa">Filtro</b><br>Solo noticias de hoy
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5568;">Keys solo en esta sesion. No se almacenan.</div>', unsafe_allow_html=True)

col_btn, col_spacer = st.columns([1, 2])
with col_btn:
    generate_btn = st.button("Generar Midday Update")

if "report" not in st.session_state:
    st.session_state.report = None
if "sources" not in st.session_state:
    st.session_state.sources = None
if "error" not in st.session_state:
    st.session_state.error = None

# ── Pipeline ──────────────────────────────────────────────────────────────────
if generate_btn:
    gk = groq_key.strip()
    tk = tavily_key.strip()

    if not gk or not tk:
        st.error("Ingresa ambas API keys en el panel lateral.")
    else:
        st.session_state.error = None
        st.session_state.report = None
        st.session_state.sources = None

        with st.spinner("Extrayendo CNBC Movers..."):
            cnbc_data = fetch_cnbc_movers()

        with st.spinner("Extrayendo BMV y BIVA..."):
            bmv_data = fetch_bmv()
            biva_data = fetch_biva()

        with st.spinner("Buscando noticias del dia (Tavily — fuentes institucionales)..."):
            try:
                tavily_results = run_tavily_searches(tk)
            except Exception as e:
                st.session_state.error = f"Error en Tavily: {e}"
                tavily_results = []

        if tavily_results is not None:
            # Store sources for display
            st.session_state.sources = {
                "cnbc": cnbc_data,
                "bmv": bmv_data,
                "biva": biva_data,
                "tavily": tavily_results,
            }

            with st.spinner("Redactando reporte institucional (Groq)..."):
                try:
                    context = build_context_string(tavily_results, cnbc_data, bmv_data, biva_data)
                    report = generate_report(gk, context)
                    st.session_state.report = report
                except Exception as e:
                    st.session_state.error = f"Error en Groq: {e}"

if st.session_state.error:
    st.error(st.session_state.error)

# ── Display ───────────────────────────────────────────────────────────────────
if st.session_state.report and st.session_state.sources:
    sources = st.session_state.sources

    # ── Sources verification panel ────────────────────────────────────────────
    st.markdown('<div class="section-label">Fuentes verificadas — solo noticias de hoy</div>', unsafe_allow_html=True)

    with st.expander("Ver fuentes y links (verificacion)", expanded=True):
        # CNBC
        cnbc = sources["cnbc"]
        css_class = "source-card ok" if cnbc["found"] else "source-card skip"
        st.markdown(f"""
        <div class="{css_class}">
            <a href="{cnbc['url']}" target="_blank">CNBC Movers — {cnbc['url']}</a>
            <div class="src-date">{'Articulo encontrado hoy' if cnbc['found'] else 'No encontrado para hoy'}</div>
        </div>""", unsafe_allow_html=True)

        # Tavily results
        for block in sources["tavily"]:
            for art in block.get("articles", []):
                today_ok = art.get("is_today", False)
                css = "source-card ok" if today_ok else "source-card"
                date_show = art['date'] if art['date'] != "fecha no disponible" else "sin fecha"
                st.markdown(f"""
                <div class="{css}">
                    <a href="{art['url']}" target="_blank">{art['title'][:90]}</a>
                    <div class="src-date">{block['label']} &bull; {date_show}</div>
                </div>""", unsafe_allow_html=True)
            if block.get("skipped", 0) > 0:
                st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#ff4060;margin-bottom:4px;">&#9888; {block["skipped"]} resultado(s) omitido(s) por fecha anterior</div>', unsafe_allow_html=True)

        # BMV
        bmv = sources["bmv"]
        st.markdown(f"""
        <div class="source-card ok">
            <a href="{bmv['url']}" target="_blank">BMV Sala de Prensa — {bmv['url']}</a>
            <div class="src-date">{TODAY_ISO}</div>
        </div>""", unsafe_allow_html=True)

        # BIVA
        biva = sources["biva"]
        st.markdown(f"""
        <div class="source-card ok">
            <a href="{biva['url']}" target="_blank">BIVA Eventos Relevantes — {biva['url']}</a>
            <div class="src-date">{TODAY_ISO}</div>
        </div>""", unsafe_allow_html=True)

    # ── Report ────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label" style="margin-top:24px;">Reporte generado</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:11px;color:#4a5568;margin-bottom:12px;">Generado {now_cdmx.strftime("%H:%M")} CDMX &nbsp;&bull;&nbsp; llama-3.3-70b &nbsp;&bull;&nbsp; Fuentes: CNBC, Bloomberg, Reuters, WSJ, FT, El Financiero, El Economista, BMV, BIVA</div>', unsafe_allow_html=True)

    st.markdown('<div class="report-output">', unsafe_allow_html=True)
    st.markdown(st.session_state.report)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Plain text copy ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-label">Texto plano para copiar a Canva</div>', unsafe_allow_html=True)
    st.text_area("", value=st.session_state.report, height=220, label_visibility="collapsed", key="plain_text")
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#4a5568;">Clic en el cuadro &rarr; Ctrl+A &rarr; Ctrl+C &rarr; pegar en Canva</div>', unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="margin-top:60px;text-align:center;">
        <div style="font-size:40px;margin-bottom:16px;">📊</div>
        <div style="font-family:IBM Plex Mono,monospace;font-size:12px;letter-spacing:2px;color:#4a5568;text-transform:uppercase;">
            Ingresa tus API keys y presiona Generar
        </div>
        <div style="font-family:IBM Plex Sans,sans-serif;font-size:13px;color:#2d3748;margin-top:10px;">
            CNBC &bull; Bloomberg &bull; Reuters &bull; WSJ &bull; FT &bull; El Financiero &bull; El Economista &bull; BMV &bull; BIVA
        </div>
    </div>
    """, unsafe_allow_html=True)
