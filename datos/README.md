# Directorio de Datos e Históricos de ESPORA

Este directorio (`datos/`) centraliza y organiza los archivos de bases de datos, hojas de cálculo de reporte e históricos de alumnos que interactúan con la plataforma de ESPORA.

## Organización del Directorio

```text
datos/
├── README.md                                  # Este archivo explicativo.
├── conglomerados/
│   └── conglomerado_semestral_espora.xlsx     # Reporte semestral consolidado de atención clínica de alumnos.
├── historicos/
│   ├── registro_historico_prepas.xlsx         # Base de datos histórica para importación automática.
│   └── nueva_base_datos_prepas.xlsx          # Copia de respaldo original de la base de datos de Prepas.
└── respaldos/
    ├── espora_respaldo_actual.xlsx            # Respaldo consolidado más reciente de todas las tablas vivas.
    └── espora_respaldo_YYYYMMDD_HHMMSS.xlsx   # Respaldos históricos autogenerados con fecha y hora.
```

---

## Detalle de las Bases de Datos / Hojas de Cálculo

### 1. `historicos/registro_historico_prepas.xlsx`
* **Descripción:** Base de datos histórica de los consultantes de nivel preparatoria (Prepas).
* **Uso en el sistema:** El script de importación del backend (`backend/scripts/import_excel.py`) lee de este archivo para crear los participantes y semillar sus valores históricos de campos dinámicos en la base de datos PostgreSQL.
* **Columnas Importantes:** Folios, datos de asignación de sedes, fecha de inicio del tratamiento, y campos dinámicos para control terapéutico (Edad, CURP, Sexo, Grupo, etc.).

### 2. `historicos/nueva_base_datos_prepas.xlsx`
* **Descripción:** Duplicado de respaldo de la base de datos de Prepas en su formato original para restauraciones o consultas offline.

### 3. `conglomerados/conglomerado_semestral_espora.xlsx`
* **Descripción:** Concentrado semestral consolidado que resume las métricas de atención clínica de alumnos del proyecto ESPORA, útil para reportes estadísticos e indicadores agregados.

### 4. `respaldos/espora_respaldo_actual.xlsx`
* **Descripción:** Hoja de cálculo multi-pestaña autogenerada que contiene una copia fiel e instantánea de la base de datos PostgreSQL viva.
* **Hojas incluidas:** Usuarios, Participantes, Casos, Sesiones/Evoluciones, Datos de Control de Proceso, Plantillas, Campos, Sumisiones, Valores de Campos, Archivos Adjuntos y Auditoría.

---

## Scripts y Relación con el Sistema

* **Script de Ingesta:** `backend/scripts/import_excel.py`
  * **Ruta de lectura dentro del contenedor:** `/app/datos/historicos/registro_historico_prepas.xlsx`
  * **Comando de ejecución:**
    ```bash
    docker compose exec backend python scripts/import_excel.py
    ```
* **Script de Respaldo Automático:** `backend/scripts/backup_db.py`
  * **Ruta de salida:** `/app/datos/respaldos/espora_respaldo_actual.xlsx`
  * **Comando de ejecución:**
    ```bash
    docker compose exec backend python scripts/backup_db.py
    ```
  * **Planificador (Scheduler):** Se ejecuta automáticamente al arrancar el contenedor del backend y posteriormente cada 12 horas.
* **Montaje en Docker Compose:**
  * El directorio local `./datos` se monta en el contenedor en `/app/datos` mediante:
    ```yaml
    volumes:
      - ./datos:/app/datos
    ```

---

## Integración con LimeSurvey y Destino de las Encuestas

Cuando se implementen las encuestas de LimeSurvey en el sistema mediante el webhook de recepción, los datos se registrarán relacionalmente en la base de datos viva (PostgreSQL) y se reflejarán en los respaldos automáticos de la siguiente manera:

### 1. Ubicación de Almacenamiento en la Base de Datos
* **Alumnos y Contacto (`participants`):** Si es el primer cuestionario que llena el estudiante (por ejemplo, la Ficha de Ingreso), el webhook crea un registro aquí con su matrícula, nombre, correo, teléfono, facultad/sede y carrera.
* **Expediente / Tratamiento (`cases`):** Se asocia al participante y se crea un caso con estado `WAITING` (Lista de Espera) y origen de entrada `"limesurvey"`.
* **Plantillas de Cuestionarios (`form_templates`):** Cada tipo de encuesta de LimeSurvey se representa con una plantilla única en el sistema (ej. `"Ficha de Ingreso (LimeSurvey)"`, `"Evaluación de Satisfacción (LimeSurvey)"`).
* **Envíos Clínicos (`form_submissions`):** Vincula la encuesta de LimeSurvey al participante y a su caso correspondiente con la fecha y hora de recepción.
* **Preguntas y Respuestas Dinámicas (`form_fields` y `form_field_values`):** Cada pregunta y respuesta específica se guarda dinámicamente en estas tablas. Esto permite soportar cualquier encuesta de LimeSurvey sin necesidad de alterar la estructura física de las tablas del sistema.

### 2. Respaldos en Excel
Dado que las respuestas de LimeSurvey se guardan en las tablas relacionales mencionadas, los respaldos automáticos de Excel en `/datos/respaldos/espora_respaldo_actual.xlsx` incluirán de inmediato todas las encuestas y sus valores recolectados bajo las pestañas:
* `Alumnos_Consultantes` (Detalles demográficos del estudiante)
* `Plantillas_Cuestionarios` (Nombre de la encuesta de LimeSurvey)
* `Campos_Formularios` (Nombres de las preguntas)
* `Sumisiones` (Registro de cada envío)
* `Valores_Campos` (Las respuestas textuales o numéricas de los alumnos)

### 3. Visualización en la Interfaz (Dash)
* **Historial Clínico (Timeline):** Los terapeutas autorizados verán las encuestas contestadas por el consultante directamente como tarjetas interactivas de evaluación dentro de la línea de tiempo del expediente.
* **Alerta y Riesgo (Ficha de Ingreso):** El dashboard de coordinación procesará el resumen inicial enviado por LimeSurvey para clasificar el nivel de riesgo y detectar palabras críticas de manera automatizada.
