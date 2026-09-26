# QZero — Puntos de llamada a modelos de IA / LLM

**Proyecto:** QZero (detector de anomalías de red con ML cuántico, QSVM/QI-VAE)
**Fecha del análisis:** 2026-09-02
**Método:** grep exhaustivo sobre todo el repo (`.py`, `.sh`, `.yml`, `.toml`, `.md`, `.env`), excluyendo `.venv/`, `.git/`, `reports/`, `training-status/`, `integrity-reports/`, `model-performance-reports/` (artefactos generados).

---

## RESULTADO PRINCIPAL

**QZero NO llama a ningún modelo de IA / LLM (ni a API de OpenAI, Anthropic, etc.).**

No existe ninguna integración con:
- OpenAI / Anthropic / Google Gemini / xAI / Groq
- OpenRouter / DeepSeek / Mistral / Together / Ollama / vLLM / TGI / LiteLLM
- Ningún *base_url* / *api_key* de proveedor LLM (no hay `sk-*`, `OPENAI_API_KEY`, etc.)

No hay dependencias LLM en `pyproject.toml` ni en `requirements*.txt` (zero-clientes: no `openai`, no `anthropic`, no `httpx` LLM).

Lo que el proyecto llama "modelos" son **modelos de ML clásicos/cuánticos entrenados y ejecutados localmente**:
- `QSVM` (Quantum Support Vector Machine)
- `QI-VAE` (Quantum-Inspired Variational Autoencoder)
- Baselines clásicos (Random Forest, SVM-RBF, Gradient Boosting, MLP)
Estos se entrenan con `scikit-learn` / `qiskit` y hacen **inferencia local en memoria**, sin ninguna llamada de red a un servicio de modelo externo.

---

## Puntos de llamada a red reales (los únicos HTTP del proyecto)

Para que quede documentado, estos son **todos** los puntos donde QZero hace una solicitud HTTP saliente. **Ninguno es una llamada a un LLM.**

### 1. Hub interno QZero (API propia, no LLM)
`src/qzero/agent/agent.py`
- **L.360–366** — `_heartbeat()`: `POST {hub_url}/api/v1/agents/{agent_id}/heartbeat`
- **L.377–385** — `_push_with_retry()`: `POST {hub_url}/api/v1/agents/{agent_id}/alerts`
- URL base: `QZERO_HUB_URL` (por defecto `http://localhost:8000`), definido en `docker-compose.agent.yml`.

### 2. Dashboard → Hub
`app/dashboard.py`
- **L.153–154** — `api_get()` usa `urllib.request.urlopen` para consultar la API del hub.
- URL base: `QZERO_API_URL` (por defecto `http://qzero-api:8000`), línea 39.

### 3. Enriquecimiento ASN (geolocalización IP, NO LLM)
`app/intel.py`
- **L.66–67** — `asn_lookup()`: consulta `https://ipinfo.io/{ip}/json` con fallback `http://ip-api.com/json/{ip}?fields=...` (identifica org/ASN/país de IPs públicas; cacheado con TTL 24h).

### 4. Notificación Telegram (NO LLM)
`src/qzero/logger.py`
- **L.319** — `send_telegram_alert()`: `POST https://api.telegram.org/bot{bot_token}/sendMessage` (envía alertas al chat, no es un modelo).

---

## Conclusión

QZero es un sistema puramente de **ML clásico/cuántico local** (detección de anomalías sobre tráfico de red). **No consume LLMs en ningún punto del código.** Si el requisito es integrar un LLM (p. ej. para los reportes "threat-relevance" o las tareas autónomas), hoy **no existe** ese código — sería trabajo nuevo, no una llamada existente.
