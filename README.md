# ESPORA: Plataforma Universitaria de Gestión Clínica

Sistema integral de administración hospitalaria y clínica de primer nivel enfocado a entornos universitarios. Diseñado orgánicamente para solventar la trazabilidad de expedientes, mitigar la carga laboral (síndrome de burnout) del cuerpo de terapeutas e incrementar la retención del paciente institucional.

---

## 1. Naturaleza del Proyecto
El sistema ESPORA nació de la necesidad de estructurar clínicas psicológicas a gran escala dentro del entorno universitario. Inicialmente dependiendo de hojas de cálculo descentralizadas, el proyecto evolucionó hacia una infraestructura relacional centralizada (PostgreSQL + Inteligencia Artificial Básica). 

Su objetivo núcleo no es solo digitalizar el papel, sino transformar los datos clínicos aislados en **Indicadores de Acción Preactiva**. Permite a los coordinadores de sede garantizar un reparto de pacientes matemáticamente justo, protegiendo la salud mental del cuerpo médico, al mismo tiempo que audita de forma inmutable quién modifica qué datos a lo largo del paso del paciente por las distintas instalaciones.

---

## 2. Arquitectura de Módulos Implementados

### 2.1. Nivel Base: Módulo del Terapeuta
Panel táctico para gestionar la historia clínica interactiva del paciente.
- **Calendario Clínico Dinámico:** Una interfaz que traza a 14 y 30 días las recaídas o sesiones activas.
- **Notas de Evolución Interconectadas:** Generador de reportes mediante clics rápidos dentro del calendario. 
- **Expediente Cronológico (Timeline):** Todo movimiento de un alumno se centraliza en su perfil vertical interactivo. Integra botones prioritarios para alertas rojas de riesgos severos.

### 2.2. Nivel Gerencial: Módulo de Coordinación Local
Herramientas operativas diseñadas para líderes de Sede/Facultad.
- **Monitor de Salud Ocupacional:** Mapeos de densidad clínica que evidencian cuántas horas o desgaste mantiene cada médico adscrito a la sede.
- **Motor de Asignación Estratégica:** Algoritmo paramétrico capaz de leer disponibilidades cruzadas y arrojar recomendaciones puntuales sobre qué psicólogo debería absorber los casos entrantes en la Lista de Espera.
- **Directorio Local de Profesionales:** Interfaz libre de fricción que permite incrustar nuevos doctores y terapeutas mediante un portal de alta directa ligada a PostgreSQL.

### 2.3. Nivel Directivo: Módulo de Coordinación General (God-Mode)
Panel de control de infraestructura central, invisible para eslabones inferiores.
- **Lanzador de Sedes:** Herramienta interna para inicializar Facultades y configuraciones operativas dinámicas directamente sobre las bases de datos. Permite designar qué campos son obligatorios o no en ramas periféricas institucionales.
- **Directorio Operativo Institucional:** Visor de administradores regionales en tiempo real. 
- **Auditoría Forense Inmutable:** Sistema de *log* cifrado que recaba permanentemente cualquier alteración en todos los sistemas subyacentes. Todo bloque de información manipulado queda grabado con "Timestamp", "Quien" y "Cual campo".
- **Visualización Analítica Nacional:** Mapas de calor (Heatmaps) consolidados para entender las tasas de deserción en contraste con éxito clínico de todos los estados universitarios centralizados.

### 2.4. Automatización: Ecosistema Externo
- **Endpoint Webhook (Recepción Automática):** Enlace receptor activo capaz de interceptar cargas JSON provenientes de plataformas externas (como LimeSurvey). Automatiza la captación y mapeos de datos de prospectos sin la intervención de digitadores institucionales, arrojándolos crudos directo a listas de espera de su facultad asignada.

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
