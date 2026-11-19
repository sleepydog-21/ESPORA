#!/usr/bin/env python3
"""
Actualiza la encuesta 118334 ("Encuesta primer contacto") en ls-test.c3.unam.mx:
1. Cambia 'facultad' -> 'entidad', agrega Facultad de Odontología (A32) y agrupa por:
   - Facultades y Escuelas Nacionales
   - Preparatoria (ENP) y CCH
   - Institutos, Centros y Coordinaciones
2. Agrega la Matriz de Selección Múltiple (Checkboxes) de Horarios:
   - Filas: Franjas amplias (Matutino, Mediodía, Vespertino)
   - Columnas: Días (Lunes a Sábado)
   - Filtrada dinámicamente por la Entidad seleccionada (solo permite marcar los días/franjas en que esa Entidad abre).
"""

import base64
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import settings

RPC_URL = settings.limesurvey_rpc_url
USERNAME = settings.limesurvey_username
PASSWORD = settings.limesurvey_password
SURVEY_ID = 118334

# Catálogo completo de 32 Entidades agrupadas en 3 sectores y con sus horarios exactos del Excel
ENTITIES = [
    # 1. Facultades y Escuelas Nacionales
    {"code": "A1",  "sector": "FAC", "name": "Facultad de Ciencias", "schedule_text": "Lun a Jue 8:00-20:00 | Vie 11:00-19:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A2",  "sector": "FAC", "name": "Facultad de Ciencias Políticas y Sociales", "schedule_text": "Lun, Mié y Jue 9:00-17:00 | Mar 8:00-17:00 | Vie 13:00-17:00 | Sáb 9:00-13:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MED", "VES"], "S": ["MAT", "MED"]}},
    {"code": "A3",  "sector": "FAC", "name": "Facultad de Economía", "schedule_text": "Mar 10:00-14:00 | Mié 10:00-19:00 | Jue 10:00-13:00 y 14:00-17:00",
     "slots": {"M": ["MAT", "MED"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"]}},
    {"code": "A4",  "sector": "FAC", "name": "Facultad de Enfermería y Obstetricia (FENO)", "schedule_text": "Lun a Mié 10:00-18:00 | Jue 12:00-18:00 | Vie 10:00-16:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A5",  "sector": "FAC", "name": "Facultad de Filosofía y Letras", "schedule_text": "Lun a Vie 9:00-18:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A6",  "sector": "FAC", "name": "Facultad de Ingeniería", "schedule_text": "Mar, Jue y Vie 15:00-19:00",
     "slots": {"M": ["VES"], "J": ["VES"], "V": ["VES"]}},
    {"code": "A32", "sector": "FAC", "name": "Facultad de Odontología", "schedule_text": "Lun 11:00-18:00 | Mar 10:00-14:00 | Mié 8:00-14:00 | Jue 9:00-15:00 | Vie 13:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED"], "X": ["MAT", "MED"], "J": ["MAT", "MED"], "V": ["MED", "VES"]}},
    {"code": "A7",  "sector": "FAC", "name": "Escuela Nacional de Artes Cinematográficas (ENAC)", "schedule_text": "Lun 9:00-16:00 | Mar 10:00-19:00 | Mié 9:00-17:00 | Jue 9:00-14:00 | Vie 9:00-12:00 y 15:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED"], "V": ["MAT", "VES"]}},
    {"code": "A8",  "sector": "FAC", "name": "Escuela Nacional de Ciencias de la Tierra (ENCIT)", "schedule_text": "Lun 9:00-16:00 | Mar 10:00-19:00 | Mié 9:00-17:00 | Jue 9:00-14:00 | Vie 9:00-12:00 y 15:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED"], "V": ["MAT", "VES"]}},
    {"code": "A9",  "sector": "FAC", "name": "Escuela Nacional de Ciencias Forenses (ENACIF)", "schedule_text": "Lun 9:00-16:00 | Mar 10:00-19:00 | Mié 9:00-17:00 | Jue 9:00-14:00 | Vie 9:00-12:00 y 15:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED"], "V": ["MAT", "VES"]}},
    {"code": "A10", "sector": "FAC", "name": "Escuela Nacional de Trabajo Social (ENTS)", "schedule_text": "Lun y Jue 11:00-17:00 | Mar y Mié 10:00-16:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"]}},

    # 2. Preparatoria (ENP) y CCH
    {"code": "A11", "sector": "BAC", "name": "Colegio de Ciencias y Humanidades, Plantel Oriente", "schedule_text": "Lun a Jue 9:00-18:00 | Vie 9:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A12", "sector": "BAC", "name": "Colegio de Ciencias y Humanidades, Plantel Vallejo", "schedule_text": "Lun a Mié 10:00-18:00 | Jue 12:00-18:00 | Vie 10:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A13", "sector": "BAC", "name": "Colegio de Ciencias y Humanidades, Plantel Sur", "schedule_text": "Lun a Vie 11:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A14", "sector": "BAC", "name": "Colegio de Ciencias y Humanidades, Plantel Naucalpan", "schedule_text": "Lun y Jue 9:00-18:00 | Mar, Mié y Vie 9:30-17:30",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A15", "sector": "BAC", "name": "Colegio de Ciencias y Humanidades, Plantel Azcapotzalco", "schedule_text": "Lun a Mié y Vie 9:00-17:00 | Jue 12:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A16", "sector": "BAC", "name": "Escuela Nacional Preparatoria, Plantel 1", "schedule_text": "Lun a Jue 10:00-18:00 | Vie 11:00-18:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A17", "sector": "BAC", "name": "Escuela Nacional Preparatoria, Plantel 2", "schedule_text": "Lun a Mié 10:00-18:00 | Vie 10:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A18", "sector": "BAC", "name": "Escuela Nacional Preparatoria, Plantel 3", "schedule_text": "Lun a Jue 10:00-18:00 | Vie 12:00-18:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MED", "VES"]}},
    {"code": "A19", "sector": "BAC", "name": "Escuela Nacional Preparatoria, Plantel 4", "schedule_text": "Lun a Vie 9:00-18:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A20", "sector": "BAC", "name": "Escuela Nacional Preparatoria, Plantel 5", "schedule_text": "Lun y Mar 10:00-18:00 | Mié y Vie 10:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A21", "sector": "BAC", "name": "Escuela Nacional Preparatoria, Plantel 6", "schedule_text": "Lun 9:00-17:00 | Mar, Mié y Vie 9:00-16:00 | Jue (Sólo API)",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A22", "sector": "BAC", "name": "Escuela Nacional Preparatoria, Plantel 7", "schedule_text": "Lun y Mié 9:30-17:00 | Mar 9:30-17:50 | Jue 13:40-16:10 | Vie 9:30-15:20",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A23", "sector": "BAC", "name": "Escuela Nacional Preparatoria, Plantel 8", "schedule_text": "Lun y Mar 8:00-17:00 | Mié 7:50-17:00 | Jue 8:40-17:00 | Vie 8:00-16:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A24", "sector": "BAC", "name": "Escuela Nacional Preparatoria, Plantel 9", "schedule_text": "Lun, Mar y Vie 9:00-19:00 | Mié y Jue 10:00-18:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},

    # 3. Institutos, Centros y Coordinaciones
    {"code": "A25", "sector": "INS", "name": "Instituto de Ecología", "schedule_text": "Jue 10:00-18:00 | Vie 10:00-12:00",
     "slots": {"J": ["MAT", "MED", "VES"], "V": ["MAT"]}},
    {"code": "A26", "sector": "INS", "name": "Instituto de Fisiología Celular", "schedule_text": "Lun y Mar 10:00-18:00 | Vie 17:00-21:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "V": ["VES"]}},
    {"code": "A27", "sector": "INS", "name": "Instituto de Ingeniería", "schedule_text": "Lun, Jue y Vie 8:00-18:00 | Mar 9:00-15:00 | Mié 10:00-14:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED"], "X": ["MAT", "MED"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "MED", "VES"]}},
    {"code": "A28", "sector": "INS", "name": "Instituto de Neurobiología, en Querétaro", "schedule_text": "Lun 9:00-16:00 | Mar 10:00-19:00 | Mié 9:00-17:00 | Jue 9:00-14:00 | Vie 9:00-12:00 y 15:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED"], "V": ["MAT", "VES"]}},
    {"code": "A29", "sector": "INS", "name": "Campus Morelos", "schedule_text": "Lun, Mié y Jue 9:00-19:00 | Mar 9:00-17:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED", "VES"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"]}},
    {"code": "A30", "sector": "INS", "name": "Coordinación de Difusión y Cultura", "schedule_text": "Lun 13:00-18:00 | Mar 11:00-18:00 | Jue 10:00-18:00 | Vie 10:00-14:00",
     "slots": {"L": ["MED", "VES"], "M": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "MED"]}},
    {"code": "A31", "sector": "INS", "name": "Coordinación General de Estudios de Posgrado", "schedule_text": "Lun 11:00-18:00 | Mar 9:00-15:00 | Mié 10:00-18:00 | Jue 10:00-16:00 | Vie 9:00-12:00 y 16:00-18:00",
     "slots": {"L": ["MAT", "MED", "VES"], "M": ["MAT", "MED"], "X": ["MAT", "MED", "VES"], "J": ["MAT", "MED", "VES"], "V": ["MAT", "VES"]}},
]

DAYS = [
    ("L", "Lunes"),
    ("M", "Martes"),
    ("X", "Miércoles"),
    ("J", "Jueves"),
    ("V", "Viernes"),
    ("S", "Sábado"),
]

FRANJAS = [
    ("MAT", "Matutino (8:00 a 12:00 hrs)"),
    ("MED", "Mediodía / Intermedio (12:00 a 15:00 hrs)"),
    ("VES", "Vespertino (15:00 a 19:00 hrs)"),
]


def build_relevance_for_slot(day_code: str, franja_code: str) -> str:
    """
    Genera la ecuación de relevancia ExpressionScript en LimeSurvey para que una celda/opción
    (Día x Franja) solo esté disponible para las Entidades que abren en ese día y franja.
    """
    allowed_codes = [
        e["code"]
        for e in ENTITIES
        if franja_code in e["slots"].get(day_code, [])
    ]
    if not allowed_codes:
        return "0"
    if len(allowed_codes) == len(ENTITIES):
        return "!is_empty(entidad.NAOK)"
    quoted = ", ".join(f'"{c}"' for c in allowed_codes)
    return f"in_array(entidad.NAOK, array({quoted}))"


def build_relevance_for_franja_row(franja_code: str) -> str:
    """
    Ecuación de relevancia para toda una fila de la Matriz (ej. ocultar Matutino/Mediodía en Ingeniería).
    """
    allowed_codes = [
        e["code"]
        for e in ENTITIES
        if any(franja_code in franjas for franjas in e["slots"].values())
    ]
    if len(allowed_codes) == len(ENTITIES):
        return "!is_empty(entidad.NAOK)"
    quoted = ", ".join(f'"{c}"' for c in allowed_codes)
    return f"in_array(entidad.NAOK, array({quoted}))"


def print_summary():
    print("=" * 75)
    print("RESUMEN DE AGRUPACIÓN DE ENTIDADES Y MATRIZ DE HORARIOS (ENCUESTA 118334)")
    print("=" * 75)
    sectors = {
        "FAC": "1. Facultades y Escuelas Nacionales",
        "BAC": "2. Escuela Nacional Preparatoria (ENP) y CCH",
        "INS": "3. Institutos, Centros y Coordinaciones"
    }
    for sec_code, sec_title in sectors.items():
        items = [e for e in ENTITIES if e["sector"] == sec_code]
        print(f"\n### {sec_title} ({len(items)} entidades)")
        for e in items:
            active_pairs = [
                f"{d_code}:{'/'.join(e['slots'][d_code])}"
                for d_code, _ in DAYS
                if d_code in e["slots"]
            ]
            print(f"  - [{e['code']:3s}] {e['name']:48s} -> {', '.join(active_pairs)}")


def build_relevance_for_day_col(day_code: str) -> str:
    """
    Ecuación de relevancia nativa para una columna de Día (L, M, X, J, V, S):
    oculta automáticamente las columnas de los días en que la Entidad seleccionada NO abre.
    """
    allowed_codes = [
        e["code"]
        for e in ENTITIES
        if len(e["slots"].get(day_code, [])) > 0
    ]
    if not allowed_codes:
        return "0"
    if len(allowed_codes) == len(ENTITIES):
        return "!is_empty(entidad.NAOK)"
    quoted = ", ".join(f'"{c}"' for c in allowed_codes)
    return f"in_array(entidad.NAOK, array({quoted}))"


def build_clean_horarios_question_html() -> str:
    schedule_text_cases = " ".join(
        f'if(entidad.NAOK == "{e["code"]}", "{e["name"]}: {e["schedule_text"]}", '
        for e in ENTITIES
    ) + '""' + (")" * len(ENTITIES))

    return (
        "<p><strong>¿En qué días y franjas horarias tienes disponibilidad para asistir a tus sesiones?</strong></p>"
        f'<p style="color:#0d6efd;font-size:0.95em;"><em>Horario de atención en tu entidad: {{{schedule_text_cases}}}</em></p>'
    )


def build_horarios_lsq_xml(sid: int, gid: int) -> str:
    """
    Construye un archivo .lsq (XML de LimeSurvey) para importar la Matriz de Casillas Múltiples
    de Horarios (tipo ':' con multiflexible_checkbox=1), con filas = MAT/MED/VES y columnas = L..S,
    usando 100% relevancia nativa de LimeSurvey (sin tags <script> que el filtro XSS bloquea).
    """
    question_html = build_clean_horarios_question_html()

    mat_rel = build_relevance_for_franja_row("MAT")
    med_rel = build_relevance_for_franja_row("MED")
    ves_rel = build_relevance_for_franja_row("VES")

    l_rel = build_relevance_for_day_col("L")
    m_rel = build_relevance_for_day_col("M")
    x_rel = build_relevance_for_day_col("X")
    j_rel = build_relevance_for_day_col("J")
    v_rel = build_relevance_for_day_col("V")
    s_rel = build_relevance_for_day_col("S")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<document>
 <LimeSurveyDocType>Question</LimeSurveyDocType>
 <DBVersion>623</DBVersion>
 <languages>
  <language>es-MX</language>
 </languages>
 <questions>
  <fields>
   <fieldname>qid</fieldname>
   <fieldname>parent_qid</fieldname>
   <fieldname>sid</fieldname>
   <fieldname>gid</fieldname>
   <fieldname>type</fieldname>
   <fieldname>title</fieldname>
   <fieldname>preg</fieldname>
   <fieldname>other</fieldname>
   <fieldname>mandatory</fieldname>
   <fieldname>question_order</fieldname>
   <fieldname>scale_id</fieldname>
   <fieldname>same_default</fieldname>
   <fieldname>relevance</fieldname>
   <fieldname>modulename</fieldname>
  </fields>
  <rows>
   <row>
    <qid><![CDATA[9001]]></qid>
    <parent_qid><![CDATA[0]]></parent_qid>
    <sid><![CDATA[{sid}]]></sid>
    <gid><![CDATA[{gid}]]></gid>
    <type><![CDATA[:]]></type>
    <title><![CDATA[horarios]]></title>
    <preg/>
    <other><![CDATA[N]]></other>
    <mandatory><![CDATA[Y]]></mandatory>
    <question_order><![CDATA[10]]></question_order>
    <scale_id><![CDATA[0]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[!is_empty(entidad.NAOK)]]></relevance>
    <modulename/>
   </row>
  </rows>
 </questions>
 <subquestions>
  <fields>
   <fieldname>qid</fieldname>
   <fieldname>parent_qid</fieldname>
   <fieldname>sid</fieldname>
   <fieldname>gid</fieldname>
   <fieldname>type</fieldname>
   <fieldname>title</fieldname>
   <fieldname>preg</fieldname>
   <fieldname>other</fieldname>
   <fieldname>mandatory</fieldname>
   <fieldname>question_order</fieldname>
   <fieldname>scale_id</fieldname>
   <fieldname>same_default</fieldname>
   <fieldname>relevance</fieldname>
   <fieldname>modulename</fieldname>
  </fields>
  <rows>
   <row>
    <qid><![CDATA[9002]]></qid>
    <parent_qid><![CDATA[9001]]></parent_qid>
    <sid><![CDATA[{sid}]]></sid>
    <gid><![CDATA[{gid}]]></gid>
    <type><![CDATA[T]]></type>
    <title><![CDATA[MAT]]></title>
    <other><![CDATA[N]]></other>
    <question_order><![CDATA[1]]></question_order>
    <scale_id><![CDATA[0]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[{mat_rel}]]></relevance>
   </row>
   <row>
    <qid><![CDATA[9003]]></qid>
    <parent_qid><![CDATA[9001]]></parent_qid>
    <sid><![CDATA[{sid}]]></sid>
    <gid><![CDATA[{gid}]]></gid>
    <type><![CDATA[T]]></type>
    <title><![CDATA[MED]]></title>
    <other><![CDATA[N]]></other>
    <question_order><![CDATA[2]]></question_order>
    <scale_id><![CDATA[0]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[{med_rel}]]></relevance>
   </row>
   <row>
    <qid><![CDATA[9004]]></qid>
    <parent_qid><![CDATA[9001]]></parent_qid>
    <sid><![CDATA[{sid}]]></sid>
    <gid><![CDATA[{gid}]]></gid>
    <type><![CDATA[T]]></type>
    <title><![CDATA[VES]]></title>
    <other><![CDATA[N]]></other>
    <question_order><![CDATA[3]]></question_order>
    <scale_id><![CDATA[0]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[{ves_rel}]]></relevance>
   </row>
   <row>
    <qid><![CDATA[9005]]></qid>
    <parent_qid><![CDATA[9001]]></parent_qid>
    <sid><![CDATA[{sid}]]></sid>
    <gid><![CDATA[{gid}]]></gid>
    <type><![CDATA[T]]></type>
    <title><![CDATA[L]]></title>
    <other><![CDATA[N]]></other>
    <question_order><![CDATA[1]]></question_order>
    <scale_id><![CDATA[1]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[{l_rel}]]></relevance>
   </row>
   <row>
    <qid><![CDATA[9006]]></qid>
    <parent_qid><![CDATA[9001]]></parent_qid>
    <sid><![CDATA[{sid}]]></sid>
    <gid><![CDATA[{gid}]]></gid>
    <type><![CDATA[T]]></type>
    <title><![CDATA[M]]></title>
    <other><![CDATA[N]]></other>
    <question_order><![CDATA[2]]></question_order>
    <scale_id><![CDATA[1]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[{m_rel}]]></relevance>
   </row>
   <row>
    <qid><![CDATA[9007]]></qid>
    <parent_qid><![CDATA[9001]]></parent_qid>
    <sid><![CDATA[{sid}]]></sid>
    <gid><![CDATA[{gid}]]></gid>
    <type><![CDATA[T]]></type>
    <title><![CDATA[X]]></title>
    <other><![CDATA[N]]></other>
    <question_order><![CDATA[3]]></question_order>
    <scale_id><![CDATA[1]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[{x_rel}]]></relevance>
   </row>
   <row>
    <qid><![CDATA[9008]]></qid>
    <parent_qid><![CDATA[9001]]></parent_qid>
    <sid><![CDATA[{sid}]]></sid>
    <gid><![CDATA[{gid}]]></gid>
    <type><![CDATA[T]]></type>
    <title><![CDATA[J]]></title>
    <other><![CDATA[N]]></other>
    <question_order><![CDATA[4]]></question_order>
    <scale_id><![CDATA[1]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[{j_rel}]]></relevance>
   </row>
   <row>
    <qid><![CDATA[9009]]></qid>
    <parent_qid><![CDATA[9001]]></parent_qid>
    <sid><![CDATA[{sid}]]></sid>
    <gid><![CDATA[{gid}]]></gid>
    <type><![CDATA[T]]></type>
    <title><![CDATA[V]]></title>
    <other><![CDATA[N]]></other>
    <question_order><![CDATA[5]]></question_order>
    <scale_id><![CDATA[1]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[{v_rel}]]></relevance>
   </row>
   <row>
    <qid><![CDATA[9010]]></qid>
    <parent_qid><![CDATA[9001]]></parent_qid>
    <sid><![CDATA[{sid}]]></sid>
    <gid><![CDATA[{gid}]]></gid>
    <type><![CDATA[T]]></type>
    <title><![CDATA[S]]></title>
    <other><![CDATA[N]]></other>
    <question_order><![CDATA[6]]></question_order>
    <scale_id><![CDATA[1]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[{s_rel}]]></relevance>
   </row>
  </rows>
 </subquestions>
 <question_l10ns>
  <fields>
   <fieldname>id</fieldname>
   <fieldname>qid</fieldname>
   <fieldname>question</fieldname>
   <fieldname>help</fieldname>
   <fieldname>language</fieldname>
  </fields>
  <rows>
   <row>
    <id><![CDATA[1]]></id>
    <qid><![CDATA[9001]]></qid>
    <question><![CDATA[{question_html}]]></question>
    <help><![CDATA[Puedes seleccionar todas las casillas de día y turno en las que tengas disponibilidad.]]></help>
    <language><![CDATA[es-MX]]></language>
   </row>
   <row>
    <id><![CDATA[2]]></id>
    <qid><![CDATA[9002]]></qid>
    <question><![CDATA[Matutino (8:00 a 12:00 hrs)]]></question>
    <help/>
    <language><![CDATA[es-MX]]></language>
   </row>
   <row>
    <id><![CDATA[3]]></id>
    <qid><![CDATA[9003]]></qid>
    <question><![CDATA[Mediodía / Intermedio (12:00 a 15:00 hrs)]]></question>
    <help/>
    <language><![CDATA[es-MX]]></language>
   </row>
   <row>
    <id><![CDATA[4]]></id>
    <qid><![CDATA[9004]]></qid>
    <question><![CDATA[Vespertino (15:00 a 19:00 hrs)]]></question>
    <help/>
    <language><![CDATA[es-MX]]></language>
   </row>
   <row>
    <id><![CDATA[5]]></id>
    <qid><![CDATA[9005]]></qid>
    <question><![CDATA[Lunes]]></question>
    <help/>
    <language><![CDATA[es-MX]]></language>
   </row>
   <row>
    <id><![CDATA[6]]></id>
    <qid><![CDATA[9006]]></qid>
    <question><![CDATA[Martes]]></question>
    <help/>
    <language><![CDATA[es-MX]]></language>
   </row>
   <row>
    <id><![CDATA[7]]></id>
    <qid><![CDATA[9007]]></qid>
    <question><![CDATA[Miércoles]]></question>
    <help/>
    <language><![CDATA[es-MX]]></language>
   </row>
   <row>
    <id><![CDATA[8]]></id>
    <qid><![CDATA[9008]]></qid>
    <question><![CDATA[Jueves]]></question>
    <help/>
    <language><![CDATA[es-MX]]></language>
   </row>
   <row>
    <id><![CDATA[9]]></id>
    <qid><![CDATA[9009]]></qid>
    <question><![CDATA[Viernes]]></question>
    <help/>
    <language><![CDATA[es-MX]]></language>
   </row>
   <row>
    <id><![CDATA[10]]></id>
    <qid><![CDATA[9010]]></qid>
    <question><![CDATA[Sábado]]></question>
    <help/>
    <language><![CDATA[es-MX]]></language>
   </row>
  </rows>
 </question_l10ns>
 <question_attributes>
  <fields>
   <fieldname>qid</fieldname>
   <fieldname>attribute</fieldname>
   <fieldname>value</fieldname>
   <fieldname>language</fieldname>
  </fields>
  <rows>
   <row>
    <qid><![CDATA[9001]]></qid>
    <attribute><![CDATA[multiflexible_checkbox]]></attribute>
    <value><![CDATA[1]]></value>
    <language/>
   </row>
  </rows>
 </question_attributes>
</document>"""


def apply_to_limesurvey():
    """
    Se conecta vía JSON-RPC a ls-test.c3.unam.mx:
      1. Quita fecha de expiración vencida
      2. Actualiza 'facultad' -> 'entidad' (QID 16)
      3. Corrige 'conacto2' -> 'contacto2' (QID 14)
      4. Importa la Matriz Checkbox 'horarios' en el Grupo 4 (Tus datos) si aún no existe.
    """
    print("\nConectando a", RPC_URL, "...")
    skey_res = requests.post(
        RPC_URL,
        json={"method": "get_session_key", "params": [USERNAME, PASSWORD], "id": 1},
        timeout=10
    ).json()
    skey = skey_res.get("result")
    if not isinstance(skey, str):
        raise RuntimeError(f"No se pudo abrir sesión RPC: {skey_res}")

    try:
        # 1. Quitar fecha de expiración vencida en la encuesta 118334
        r_prop = requests.post(
            RPC_URL,
            json={
                "method": "set_survey_properties",
                "params": [skey, SURVEY_ID, {"expires": None}],
                "id": 2
            },
            timeout=10
        ).json()
        print("1. Propiedades de encuesta actualizadas (expires=None):", r_prop.get("result"))

        # 2. Actualizar código y texto de QID 16 (facultad -> entidad)
        r_q16 = requests.post(
            RPC_URL,
            json={
                "method": "set_question_properties",
                "params": [
                    skey,
                    16,
                    {
                        "title": "entidad",
                        "question": "¿En qué Entidad académica (Facultad, Escuela, Plantel ENP/CCH, Instituto o Centro) realizas tus estudios?"
                    }
                ],
                "id": 3
            },
            timeout=10
        ).json()
        print("2. Pregunta 16 actualizada a 'entidad':", r_q16.get("result"))

        # 3. Corregir typo en QID 14 (conacto2 -> contacto2)
        r_q14 = requests.post(
            RPC_URL,
            json={
                "method": "set_question_properties",
                "params": [skey, 14, {"title": "contacto2"}],
                "id": 4
            },
            timeout=10
        ).json()
        print("3. Pregunta 14 corregida a 'contacto2':", r_q14.get("result"))

        # 4. Verificar si ya existe la pregunta 'horarios' y limpiarla / actualizarla
        q_list = requests.post(
            RPC_URL,
            json={"method": "list_questions", "params": [skey, SURVEY_ID], "id": 5},
            timeout=10
        ).json().get("result", [])
        horarios_q = next((q for q in q_list if isinstance(q, dict) and q.get("title") == "horarios"), None)

        if horarios_q:
            hqid = int(horarios_q["qid"])
            clean_html = build_clean_horarios_question_html()
            r_upd = requests.post(
                RPC_URL,
                json={
                    "method": "set_question_properties",
                    "params": [
                        skey,
                        hqid,
                        {
                            "question": clean_html,
                            "help": "Selecciona todas las casillas de día y turno en las que tengas disponibilidad (dentro del horario de tu entidad)."
                        }
                    ],
                    "id": 6
                },
                timeout=15
            ).json()
            print(f"4. Texto de la pregunta 'horarios' (QID {hqid}) limpiado exitosamente:", r_upd.get("result"))
        else:
            lsq_xml = build_horarios_lsq_xml(SURVEY_ID, 4)
            lsq_b64 = base64.b64encode(lsq_xml.encode("utf-8")).decode("ascii")
            r_imp = requests.post(
                RPC_URL,
                json={
                    "method": "import_question",
                    "params": [skey, SURVEY_ID, 4, lsq_b64, "lsq", "N", "horarios"],
                    "id": 6
                },
                timeout=15
            ).json()
            print("4. Matriz 'horarios' importada en Grupo 4 (QID nuevo):", r_imp)

    finally:
        requests.post(
            RPC_URL,
            json={"method": "release_session_key", "params": [skey], "id": 99},
            timeout=5
        )


def activate_and_inspect(activate: bool = False):
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from services.limesurvey_service import limesurvey_service

    skey_res = requests.post(
        RPC_URL,
        json={"method": "get_session_key", "params": [USERNAME, PASSWORD], "id": 1},
        timeout=10
    ).json()
    skey = skey_res.get("result")
    try:
        if activate:
            r_act = requests.post(
                RPC_URL,
                json={"method": "activate_survey", "params": [skey, SURVEY_ID], "id": 2},
                timeout=15
            ).json()
            print("Encuesta 118334 activada:", r_act)
    finally:
        if isinstance(skey, str):
            requests.post(
                RPC_URL,
                json={"method": "release_session_key", "params": [skey], "id": 99},
                timeout=5
            )

    responses = limesurvey_service.fetch_translated_responses(str(SURVEY_ID))
    print(f"\n=== RESPUESTAS ENCONTRADAS EN ENCUESTA {SURVEY_ID}: {len(responses)} ===")
    print(json.dumps(responses, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if "--apply" in sys.argv:
        apply_to_limesurvey()
    elif "--activate" in sys.argv:
        activate_and_inspect(activate=True)
    elif "--responses" in sys.argv:
        activate_and_inspect(activate=False)
    else:
        print_summary()
