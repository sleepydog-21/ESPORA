# ESPORA: Sistema Universitario de Gestión Clínica y Analítica Forense

Plataforma de infraestructura clínico-administrativa diseñada para la asignación inteligente de terapeutas, reducción de abandono (drop-outs) y mitigación del síndrome de burnout institucional.

## 🚀 Alcance y Capacidades
1. **Directorio Institucional:** Control maestro ("God-Mode") para generación de facultades y personal.
2. **Tableros de Prevención de Burnout:** Lectura en tiempo real (vía Dash/Plotly) de la carga de los consultantes.
3. **Expediente Forense y Timelines:** Línea de tiempo inmutable con tracking de notas, ausencias y estatus de riesgo suicida de los pacientes.
4. **Carga Segura Automatizada:** Webhook público capaz de ingerir formularios completos vía LimeSurvey sin necesidad de digitación local.
5. **Smart-Match:** Asignación paramétrica recomendada para equidad laboral de salud mental en psicólogos de facultad.

## 🛠 Entorno Tecnológico
- **Frontend / DataViz:** Plotly Dash (Python)
- **Backend Replicacional:** FastAPI 
- **Persistencia (RDBMS):** PostgreSQL (Controlado con SQLAlchemy y Pydantic)
- **Asincronía & Tareas:** APScheduler

## ⚙️ Inicio Rápido (Despliegue)
Requisitos recomendados: `Docker` y `Docker Compose`.

1. Clona el repositorio a tu infraestructura segura:
   ```bash
   git clone <URL_REPOSITORIO>
   cd ESPORA
   ```

2. Fija las variables de entorno:
   Renombra o consolida las variables (DB, URLs) asegurando un archivo `.env` o pasando variables CLI para evitar subirlas.

3. Despliegue Multicontenedor:
   ```bash
   docker-compose up --build -d
   ```

4. Accesos Globales Pre-Configurados:
   - Dashboard Directivo (React/Dash): `http://localhost:18050`
   - API e Interfaces HTTP: `http://localhost:8000/docs`

> *Las estadísticas, nombres e identidades utilizadas en las capturas son estipuladas bajo dominios mock (falsa sintaxis) en el ambiente dev.*
