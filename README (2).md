# 📊 Midday Market Update — Streamlit App

App institucional que genera automáticamente el **Midday Market Update** para AFORES e inversionistas institucionales, usando **Grok (xAI)** con búsqueda web en tiempo real.

---

## 🚀 Deploy en Streamlit Cloud (5 minutos)

### 1. Sube el código a GitHub
Crea un repositorio nuevo (puede ser privado) y sube estos dos archivos:
```
app.py
requirements.txt
```

### 2. Conecta en Streamlit Cloud
1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Clic en **"New app"**
3. Selecciona tu repositorio y rama
4. En **"Main file path"** escribe: `app.py`
5. Clic en **"Deploy"**

### 3. (Opcional) Guarda tu API key como Secret
Para no tener que escribirla cada vez:
1. En Streamlit Cloud → tu app → **Settings → Secrets**
2. Agrega:
```toml
XAI_API_KEY = "xai-tu-key-aqui"
```
3. En `app.py`, reemplaza la línea del `text_input` por:
```python
import os
api_key_input = os.environ.get("XAI_API_KEY", "")
```

---

## 🔑 API Key de xAI (Grok)
Obtén tu key en: [console.x.ai](https://console.x.ai)

Modelo usado: **grok-3** (con búsqueda web nativa en tiempo real)

---

## 📋 Workflow diario
1. Abre la app (~11:30 AM CDMX)
2. Clic en **"Generar Midday Update"**
3. Espera ~30–60 segundos mientras Grok busca noticias
4. Copia el texto del cuadro inferior (Ctrl+A → Ctrl+C)
5. Pega en tu template de Canva

---

## 🗂 Estructura del reporte generado
1. **Lectura Ejecutiva** — Sentiment + driver dominante
2. **Movers del día** — Acciones con mayor movimiento
3. **Noticias EE.UU.** — 3–4 bullets con impacto macro
4. **Noticias México** — 3–4 bullets (Banxico, IPC, FX, tasas)
5. **Lectura de Flujos** — Institucionales, SIC, renta fija
6. **Cierre** — Sesgo para la tarde

---

## ⚠️ Notas
- La app **no almacena** tu API key entre sesiones
- Si usas Secrets de Streamlit, la key queda cifrada en su plataforma
- El modelo Grok-3 tiene acceso a internet en tiempo real — no requiere plugins adicionales
