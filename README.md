# ESPORA: Plataforma Universitaria de Gestión Clínica

Sistema integral de administración hospitalaria y clínica de primer nivel enfocado a entornos universitarios. Diseñado orgánicamente para solventar la trazabilidad de expedientes, mitigar la carga laboral (síndrome de burnout) del cuerpo de terapeutas e incrementar la retención del paciente institucional.

---

## 1. Naturaleza del Proyecto
El sistema ESPORA nació de la necesidad de estructurar clínicas psicológicas a gran escala dentro del entorno universitario. Inicialmente dependiendo de hojas de cálculo descentralizadas, el proyecto evolucionó hacia una infraestructura relacional centralizada (PostgreSQL + Inteligencia Artificial Básica). 

Su objetivo núcleo no es solo digitalizar el papel, sino transformar los datos clínicos aislados en **Indicadores de Acción Preactiva**. Permite a los coordinadores de sede garantizar un reparto de pacientes matemáticamente justo, protegiendo la salud mental del cuerpo médico, al mismo tiempo que audita de forma inmutable quién modifica qué datos a lo largo del paso del paciente por las distintas instalaciones.

---

## 2. Arquitectura de Módulos Implementados

### 2.1. Nivel Base: Módulo del Terapeuta y Protocolo API
Panel táctico para gestionar la historia clínica interactiva del paciente y registrar contenciones de emergencia.
- **Calendario Clínico Dinámico:** Una interfaz que traza a 14 y 30 días las recaídas o sesiones activas.
- **Notas de Evolución Interconectadas:** Generador de reportes mediante clics rápidos dentro del calendario, incluyendo checklist de 25 problemáticas trabajadas y evaluación de ideación/intentos suicidas.
- **Botón `🚨 Protocolo API` (Contención):** Disponible para cualquier terapeuta o personal de API en el consultorio (`/therapist`) para registrar contenciones o emergencias (alumno nuevo o paciente existente), guardando la ficha en el historial clínico y permitiendo derivar en un clic a la Lista de Espera de la sede con la etiqueta `🚨 Derivado de API`.
- **Expediente Cronológico (Timeline):** Todo movimiento de un alumno se centraliza en su perfil vertical interactivo (`/patient/<id>`).
- **Expediente Editable en Vivo:** Ficha clínica de control de proceso (`CaseProcessData`) en la pantalla del paciente que permite modificar variables (edad, inasistencias, canalización, diagnósticos, sesiones API) con guardado en base de datos.
- **Envío de Cuestionarios de Seguimiento y Egreso por Correo Oficial (`espora@c3.unam.mx`):** Desde el perfil del paciente, el terapeuta envía enlaces personalizados de LimeSurvey prellenados con el Folio del alumno (*Información Complementaria de Inicio `#228334`* y *Formato de Egreso + Escala CRES-4 `#338334`*) y sincroniza las respuestas directo al expediente.
- **Módulo de Anexo Rápido:** Capacidad para arrastrar, soltar o subir fotografías de notas escritas a mano, dictados o reportes en formato PDF/Imagen directamente en la línea de tiempo del paciente, almacenados en Base64 en PostgreSQL.
- **Descarga Histórica Completa:** Generación instantánea en un solo clic de un libro de Excel consolidado multi-pestaña con el expediente completo (sesiones, datos de proceso, adjuntos, y logs de auditoría).

### 2.2. Nivel Gerencial: Módulo de Coordinación Local (Por Entidad)
Herramientas operativas diseñadas para líderes de las 32 Entidades (Facultades, Escuelas Nacionales, ENP 1–9, CCH, Institutos, Posgrado, Cultura y Morelos).
- **Lista de Espera Inteligente y Ordenable Multi-Columna:** Tabla unificada por entidad con columnas ordenables de **`Origen`** (`🚨 Derivado de API`, `📋 LimeSurvey`, `✍️ Manual`), **`Riesgo`** (`3 🔴 Alto`, `2 🟡 Medio`, `1 🟢 Bajo`), **`No. Alarmas`** (diccionario clínico ampliado de palabras de cuidado), **`Grado de Urgencia`** (`5 🔴 Muy mal` a `1 🟢 Muy bien`), **`Horario Disponible`** y **`Fecha Ingreso`**.
- **Motor de Asignación Estratégica (Horario + Carga):** Algoritmo que cruza los bloques de `Horario Disponible` solicitados por el alumno en LimeSurvey contra las sesiones agendadas y carga activa de cada terapeuta de la sede, recomendando y preseleccionando al terapeuta óptimo (`⭐ RECOMENDADO`).
- **Alta Rápida con Llave Genérica y Recuperación de Contraseña:** Creación de cuentas de Terapeutas y Coordinadores ingresando únicamente su correo institucional (con envío automático de llave genérica por correo), botón `🔑 Cambiar Contraseña` en la barra superior y recuperación de contraseña mediante código de 6 dígitos por correo en `/login`.

### 2.3. Nivel Directivo: Módulo de Coordinación General (God-Mode)
Panel de control de infraestructura central, invisible para eslabones inferiores.
- **Lanzador de Sedes:** Herramienta interna para inicializar Facultades y configuraciones operativas dinámicas directamente sobre las bases de datos. Permite designar qué campos son obligatorios o no en ramas periféricas institucionales.
- **Directorio Operativo Institucional:** Visor y alta rápida de coordinadores de sede en tiempo real.
- **Auditoría Forense Inmutable:** Sistema de *log* que recaba permanentemente cualquier alteración en todos los sistemas subyacentes con `"Timestamp"`, `"Quien"` y `"Cual campo"`.
- **Visualización Analítica Nacional y Clima Laboral:** Mapas de calor (Heatmaps) consolidados y gráficas semanales de bienestar docente (prevención de *burnout*).

### 2.4. Automatización y Conector con LimeSurvey (Infraestructura C3)
- **Conector Bidireccional (`lsapi.c3.unam.mx` / `ls-test.c3.unam.mx`):** Sincronización activa de las 3 encuestas institucionales en LimeSurvey:
  1. **`SID 118334` (*Encuesta primer contacto*):** Incluye el catálogo de 32 Entidades de la UNAM y una Matriz de Selección Múltiple (Checkboxes) de Horarios (`Matutino / Mediodía / Vespertino` × `Lunes a Sábado`) condicionada a los horarios de atención de cada entidad.
  2. **`SID 228334` (*Información Complementaria de Inicio*):** Datos académicos, antecedentes psicológicos/psiquiátricos, áreas afectadas y duración del malestar.
  3. **`SID 338334` (*Formato de Egreso y Satisfacción CRES-4*):** Evaluación 1–10 del proceso con preguntas condicionales y escala oficial CRES-4.

### 2.5. Gestión de Datos y Respaldos Automatizados (Directorio `datos/`)
El sistema centraliza sus archivos de datos y reportes fuera de la estructura de código en la carpeta local `./datos/`, montada en el contenedor del backend:
- **`datos/historicos/`:** Aloja bases históricas en formato Excel (ej. `registro_historico_prepas.xlsx`) empleadas por el script `backend/scripts/import_excel.py` para poblar el sistema inicialmente.
- **`datos/conglomerados/`:** Hojas de cálculo semestrales unificadas de atención clínica para reportes agregados institucionales.
- **`datos/respaldos/`:** Directorio para respaldos multi-pestaña de la base de datos viva PostgreSQL (`espora_respaldo_actual.xlsx`).
- **Planificador de Respaldos (Scheduler):** FastAPI inicializa un planificador APScheduler que genera automáticamente un respaldo en Excel cada 12 horas, guardando además históricos con sello de fecha y hora para auditoría offline.

---

## 3. Topología Tecnológica
- **Motor de Persistencia Estructural:** PostgreSQL
- **Mapeo Relacional de Base de Datos:** SQLAlchemy y Pydantic (Validación Formal de Esquemas).
- **Control de Versiones y Migraciones Estructurales:** Alembic
- **Servicio REST API y Enrutamiento Backend:** FastAPI (Lenguaje base: Python 3). 
- **Analítica de Datos:** Pandas.
- **Framework de Interfaces Frontend Gráficas:** Plotly Dash y Dash Bootstrap Components.

---

## 4. Guía Institucional de Despliegue Local y Producción
Entorno recomendado y unificado mediado por Docker.

### 4.1. Iniciación del Entorno Aislado
Para ejecutar todo el perímetro ESPORA sin instalar las dependencias subyacentes en una máquina base, utilice la herramienta nativa Docker Compose. 

1. Sitúese en el directorio base donde se clonó el repositorio.
2. Ejecute la construcción secuencial de los tres microservicios (Backend, BD, Frontend):

```bash
docker-compose up --build -d
```

### 4.2 Verificación de Operaciones
Si la instanciación fue exitosa, las siguientes compuertas estarán activas:
- Interfaz Gráfica General (Usuarios/Administradores): `http://localhost:18050/login`
- Documentación OpenAPI Consolidada de Backend: `http://localhost:8000/docs`

*Nota: Durante despliegues de desarrollo, variables y correos genéricos pueden alojarse en los esquemas iniciales temporales para permitir inspección analítica del FrontEnd.*
