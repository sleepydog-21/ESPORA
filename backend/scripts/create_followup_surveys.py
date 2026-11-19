#!/usr/bin/env python3
"""
Crea y activa en ls-test.c3.unam.mx las 2 encuestas adicionales que envía el terapeuta desde el perfil del paciente:
1. Información Complementaria de Inicio - ESPORA (SID 228334)
2. Formato de Egreso y Satisfacción (CRES-4) - ESPORA (SID 338334)
"""

import base64
import json
import os
import sys
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import settings

RPC_URL = settings.limesurvey_rpc_url
USERNAME = settings.limesurvey_username
PASSWORD = settings.limesurvey_password

INICIO_SID = 228334
EGRESO_SID = 338334


def rpc_call(skey_or_none, method: str, params: list):
    res = httpx.post(
        RPC_URL,
        json={"method": method, "params": params, "id": 1},
        timeout=20,
        verify=False
    )
    res.raise_for_status()
    data = res.json()
    if data.get("error"):
        raise RuntimeError(f"RPC Error ({method}): {data['error']}")
    return data.get("result")


def build_question_lsq(sid: int, gid: int, title: str, qtype: str, question_text: str,
                       mandatory: str = "Y", order: int = 1, relevance: str = "1",
                       help_text: str = "", answers: list = None, subquestions: list = None) -> str:
    """
    Construye un XML .lsq válido para LimeSurvey (DBVersion 623) para preguntas tipo S, N, T, L o M.
    answers: lista de tuplas (code, text) para preguntas tipo L
    subquestions: lista de tuplas (code, text) para preguntas tipo M
    """
    subq_block = ""
    l10n_extra = ""
    next_l10n_id = 2

    if subquestions:
        sq_rows = []
        for idx, (sq_code, sq_text) in enumerate(subquestions, start=1):
            sq_qid = 9100 + idx
            sq_rows.append(f"""   <row>
    <qid><![CDATA[{sq_qid}]]></qid>
    <parent_qid><![CDATA[9001]]></parent_qid>
    <sid><![CDATA[{sid}]]></sid>
    <gid><![CDATA[{gid}]]></gid>
    <type><![CDATA[T]]></type>
    <title><![CDATA[{sq_code}]]></title>
    <other><![CDATA[N]]></other>
    <question_order><![CDATA[{idx}]]></question_order>
    <scale_id><![CDATA[0]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[1]]></relevance>
   </row>""")
            l10n_extra += f"""   <row>
    <id><![CDATA[{next_l10n_id}]]></id>
    <qid><![CDATA[{sq_qid}]]></qid>
    <question><![CDATA[{sq_text}]]></question>
    <help/>
    <language><![CDATA[es-MX]]></language>
   </row>\n"""
            next_l10n_id += 1

        subq_block = f""" <subquestions>
  <fields>
   <fieldname>qid</fieldname>
   <fieldname>parent_qid</fieldname>
   <fieldname>sid</fieldname>
   <fieldname>gid</fieldname>
   <fieldname>type</fieldname>
   <fieldname>title</fieldname>
   <fieldname>other</fieldname>
   <fieldname>question_order</fieldname>
   <fieldname>scale_id</fieldname>
   <fieldname>same_default</fieldname>
   <fieldname>relevance</fieldname>
  </fields>
  <rows>
{chr(10).join(sq_rows)}
  </rows>
 </subquestions>"""

    ans_block = ""
    if answers:
        ans_rows = []
        ans_l10n_rows = []
        for idx, (a_code, a_text) in enumerate(answers, start=1):
            aid = 8100 + idx
            ans_rows.append(f"""   <row>
    <aid><![CDATA[{aid}]]></aid>
    <qid><![CDATA[9001]]></qid>
    <code><![CDATA[{a_code}]]></code>
    <sortorder><![CDATA[{idx}]]></sortorder>
    <assessment_value><![CDATA[0]]></assessment_value>
    <scale_id><![CDATA[0]]></scale_id>
   </row>""")
            ans_l10n_rows.append(f"""   <row>
    <id><![CDATA[{idx}]]></id>
    <aid><![CDATA[{aid}]]></aid>
    <answer><![CDATA[{a_text}]]></answer>
    <language><![CDATA[es-MX]]></language>
   </row>""")
        ans_block = f""" <answers>
  <fields>
   <fieldname>aid</fieldname>
   <fieldname>qid</fieldname>
   <fieldname>code</fieldname>
   <fieldname>sortorder</fieldname>
   <fieldname>assessment_value</fieldname>
   <fieldname>scale_id</fieldname>
  </fields>
  <rows>
{chr(10).join(ans_rows)}
  </rows>
 </answers>
 <answer_l10ns>
  <fields>
   <fieldname>id</fieldname>
   <fieldname>aid</fieldname>
   <fieldname>answer</fieldname>
   <fieldname>language</fieldname>
  </fields>
  <rows>
{chr(10).join(ans_l10n_rows)}
  </rows>
 </answer_l10ns>"""

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
    <type><![CDATA[{qtype}]]></type>
    <title><![CDATA[{title}]]></title>
    <preg/>
    <other><![CDATA[N]]></other>
    <mandatory><![CDATA[{mandatory}]]></mandatory>
    <question_order><![CDATA[{order}]]></question_order>
    <scale_id><![CDATA[0]]></scale_id>
    <same_default><![CDATA[0]]></same_default>
    <relevance><![CDATA[{relevance}]]></relevance>
    <modulename/>
   </row>
  </rows>
 </questions>
{subq_block}
{ans_block}
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
    <question><![CDATA[{question_text}]]></question>
    <help><![CDATA[{help_text}]]></help>
    <language><![CDATA[es-MX]]></language>
   </row>
{l10n_extra}  </rows>
 </question_l10ns>
</document>"""


def import_q(skey: str, sid: int, gid: int, **kwargs):
    xml_str = build_question_lsq(sid=sid, gid=gid, **kwargs)
    b64_data = base64.b64encode(xml_str.encode("utf-8")).decode("ascii")
    res = rpc_call(skey, "import_question", [skey, sid, gid, b64_data, "lsq", "N", kwargs["title"]])
    return res


def setup_surveys():
    skey = rpc_call(None, "get_session_key", [USERNAME, PASSWORD])
    try:
        existing = rpc_call(skey, "list_surveys", [skey, USERNAME])
        existing_sids = {int(s["sid"]): s for s in existing} if isinstance(existing, list) else {}

        # Si la encuesta 228334 quedó incompleta (inactiva), borrarla primero para recrearla limpia
        if INICIO_SID in existing_sids and existing_sids[INICIO_SID].get("active") != "Y":
            rpc_call(skey, "delete_survey", [skey, INICIO_SID])
            existing_sids.pop(INICIO_SID, None)

        if EGRESO_SID in existing_sids and existing_sids[EGRESO_SID].get("active") != "Y":
            rpc_call(skey, "delete_survey", [skey, EGRESO_SID])
            existing_sids.pop(EGRESO_SID, None)

        # =====================================================================
        # 1. ENCUESTA DE INFORMACIÓN COMPLEMENTARIA DE INICIO (SID 228334)
        # =====================================================================
        if INICIO_SID not in existing_sids:
            sid_inicio = int(rpc_call(skey, "add_survey", [skey, INICIO_SID, "Información Complementaria de Inicio - ESPORA", "es-MX", "G"]))
            print(f"✅ Creada encuesta de Inicio con SID: {sid_inicio}")
            gid1 = int(rpc_call(skey, "add_group", [skey, sid_inicio, "Datos Académicos y Antecedentes Clínicos", "Por favor completa los siguientes datos para tu expediente clínico en el Programa ESPORA."]))

            scale_1_10 = [(f"A{i}", str(i)) for i in range(1, 11)]
            import_q(skey, sid_inicio, gid1, title="folio", qtype="S", order=1,
                     question_text="Folio de registro ESPORA o Número de cuenta UNAM",
                     help_text="Si entraste desde el enlace enviado a tu correo, confirma tu número de cuenta o folio.")
            import_q(skey, sid_inicio, gid1, title="edad", qtype="N", order=2,
                     question_text="Edad (años cumplidos)")
            import_q(skey, sid_inicio, gid1, title="ciclo_ingreso", qtype="S", order=3,
                     question_text="Ciclo escolar de ingreso al nivel de estudios en el que te encuentras actualmente",
                     help_text="Ejemplo: 2024-1")
            import_q(skey, sid_inicio, gid1, title="semestre_actual", qtype="S", order=4,
                     question_text="Año o semestre que cursas actualmente")
            import_q(skey, sid_inicio, gid1, title="materias_adeuda", qtype="N", order=5,
                     question_text="Número de materias adeudadas (coloca 0 si no adeudas ninguna)")
            import_q(skey, sid_inicio, gid1, title="discapacidad", qtype="S", order=6, mandatory="N",
                     question_text="¿Vives con alguna discapacidad? (En caso afirmativo especifica cuál; si no, déjalo en blanco o escribe No)")
            import_q(skey, sid_inicio, gid1, title="atencion_psico", qtype="L", order=7,
                     question_text="¿Anteriormente habías asistido a algún espacio de atención psicológica?",
                     answers=[("SI", "Sí"), ("NO", "No")])
            import_q(skey, sid_inicio, gid1, title="atencion_psiq", qtype="L", order=8,
                     question_text="¿Anteriormente habías asistido a atención psiquiátrica?",
                     answers=[("SI", "Sí"), ("NO", "No")])
            import_q(skey, sid_inicio, gid1, title="areas_afectadas", qtype="M", order=9,
                     question_text="¿Cuáles de las siguientes áreas se han visto afectadas en tu vida en relación con tu motivo de consulta?",
                     subquestions=[
                         ("ESC", "Escolar"), ("FAM", "Familiar"), ("SOC", "Social"),
                         ("LAB", "Laboral"), ("PAR", "Pareja"), ("SEX", "Sexual"),
                         ("EMO", "Emocional"), ("OTR", "Otra")
                     ])
            import_q(skey, sid_inicio, gid1, title="malestar_1_10", qtype="L", order=10,
                     question_text="Del 1 al 10, ¿cómo te sientes actualmente? (1 = Muy mal, 10 = Muy bien)",
                     answers=scale_1_10)
            import_q(skey, sid_inicio, gid1, title="tiempo_malestar", qtype="L", order=11,
                     question_text="¿Desde cuándo empezaste a sentir el malestar actual?",
                     answers=[
                         ("T1", "Hace 2 semanas"), ("T2", "Hace 1 mes"), ("T3", "Hace tres meses"),
                         ("T4", "Hace 6 meses"), ("T5", "Hace 1 año"), ("T6", "Hace 2 años"),
                         ("T7", "Hace 3 años"), ("T8", "Hace más de 3 años")
                     ])
            act_res = rpc_call(skey, "activate_survey", [skey, sid_inicio])
            print(f"✅ Encuesta de Inicio ({sid_inicio}) activada:", act_res)
        else:
            print(f"ℹ️ Encuesta de Inicio ({INICIO_SID}) ya existe y está activa.")

        # =====================================================================
        # 2. ENCUESTA DE FORMATO DE EGRESO + ESCALA CRES-4 (SID 338334)
        # =====================================================================
        if EGRESO_SID not in existing_sids:
            sid_egreso = int(rpc_call(skey, "add_survey", [skey, EGRESO_SID, "Formato de Egreso y Satisfacción (CRES-4) - ESPORA", "es-MX", "G"]))
            print(f"✅ Creada encuesta de Egreso con SID: {sid_egreso}")
            gid_eg1 = int(rpc_call(skey, "add_group", [skey, sid_egreso, "Evaluación de tu Proceso en ESPORA",
                                                       "¡Hola! Queremos conocer tu opinión sobre el Programa ESPORA y sobre la atención que recibiste durante estas semanas con el objetivo de seguir mejorando."]))
            gid_eg2 = int(rpc_call(skey, "add_group", [skey, sid_egreso, "Escala de Satisfacción con el Tratamiento (CRES-4)",
                                                       "Finalmente, cuatro últimas preguntas parte de una escala para poder evaluar mejor nuestros resultados como programa."]))

            scale_1_10 = [(f"{i}", str(i)) for i in range(1, 11)]

            import_q(skey, sid_egreso, gid_eg1, title="folio", qtype="S", order=1,
                     question_text="Folio de registro ESPORA o Número de cuenta UNAM")
            import_q(skey, sid_egreso, gid_eg1, title="motivo_breve", qtype="S", order=2,
                     question_text="1. Brevemente, ¿cuál fue tu motivo de consulta?",
                     help_text="Máximo 100 caracteres.")
            import_q(skey, sid_egreso, gid_eg1, title="areas_mejoria", qtype="M", order=3,
                     question_text="2. ¿Cuáles son las áreas en las que notaste una mejoría?",
                     subquestions=[
                         ("A1", "1: Escolar"), ("A2", "2: Familiar"), ("A3", "3: Social"),
                         ("A4", "4: Laboral"), ("A5", "5: Pareja"), ("A6", "6: Sexual"),
                         ("A7", "7: Emocional"), ("A8", "8: Otra"), ("A9", "9: Ninguna")
                     ])
            import_q(skey, sid_egreso, gid_eg1, title="calif_atencion", qtype="L", order=4,
                     question_text="3. En una escala del 1 al 10, ¿Cómo calificarías la atención recibida?",
                     answers=scale_1_10)
            import_q(skey, sid_egreso, gid_eg1, title="calif_porque", qtype="T", order=5,
                     relevance='!is_empty(calif_atencion.NAOK) and (calif_atencion.NAOK == "1" or calif_atencion.NAOK == "2" or calif_atencion.NAOK == "3" or calif_atencion.NAOK == "4" or calif_atencion.NAOK == "5" or calif_atencion.NAOK == "6" or calif_atencion.NAOK == "7" or calif_atencion.NAOK == "8")',
                     question_text="3b. ¿Por qué calificaste con 8 o menos la atención recibida?")
            import_q(skey, sid_egreso, gid_eg1, title="prob_recomendar", qtype="L", order=6,
                     question_text="4. En una escala del 1 al 10, ¿qué tan probable es que recomiendes ESPORA a un amigo/a o compañero/a?",
                     answers=scale_1_10)
            import_q(skey, sid_egreso, gid_eg1, title="recom_porque", qtype="T", order=7,
                     relevance='!is_empty(prob_recomendar.NAOK) and (prob_recomendar.NAOK == "1" or prob_recomendar.NAOK == "2" or prob_recomendar.NAOK == "3" or prob_recomendar.NAOK == "4" or prob_recomendar.NAOK == "5" or prob_recomendar.NAOK == "6" or prob_recomendar.NAOK == "7" or prob_recomendar.NAOK == "8")',
                     question_text="4b. ¿Por qué asignaste ese puntaje a tu probabilidad de recomendar ESPORA?")
            import_q(skey, sid_egreso, gid_eg1, title="p5_estado_actual", qtype="L", order=8,
                     question_text="5. Del 1 al 10, ¿Cómo te sientes actualmente?",
                     answers=scale_1_10)
            import_q(skey, sid_egreso, gid_eg1, title="p6_comprension", qtype="L", order=9,
                     question_text="6. Del 1 al 10, ¿Qué tanto te ayudó el proceso a comprender de dónde proviene tu malestar?",
                     answers=scale_1_10)
            import_q(skey, sid_egreso, gid_eg1, title="p7_cambios", qtype="L", order=10,
                     question_text="7. Del 1 al 10, ¿Qué tanto sientes que hubo cambios dentro de ti después del tratamiento?",
                     answers=scale_1_10)
            import_q(skey, sid_egreso, gid_eg1, title="p8_alivio", qtype="L", order=11,
                     question_text="8. Del 1 al 10, ¿Qué tanto te generó alivio emocional el hablar en las sesiones?",
                     answers=scale_1_10)
            import_q(skey, sid_egreso, gid_eg1, title="p9_decisiones", qtype="L", order=12,
                     question_text="9. Del 1 al 10, ¿Qué tanto te ayudó el proceso a tomar decisiones para estar mejor?",
                     answers=scale_1_10)
            import_q(skey, sid_egreso, gid_eg1, title="p10_escuchado", qtype="L", order=13,
                     question_text="10. Del 1 al 10, ¿Qué tan escuchado/a te sentiste en las sesiones?",
                     answers=scale_1_10)
            import_q(skey, sid_egreso, gid_eg1, title="p11_espacio_seg", qtype="L", order=14,
                     question_text="11. Del 1 al 10, ¿Qué tanto sentiste que en este espacio puedes hablar de cosas que no puedes decir en otros lugares de tu entorno?",
                     answers=scale_1_10)

            # Grupo 2: Escala CRES-4
            import_q(skey, sid_egreso, gid_eg2, title="cres1_satisfac", qtype="L", order=1,
                     question_text="1. En general, ¿qué tan satisfecho/a estás con la forma en la que tu terapeuta ha tratado el problema por el que pediste la atención?",
                     answers=[
                         ("0", "a. Completamente insatisfecho/a (0)"),
                         ("1", "b. Muy insatisfecho/a (1)"),
                         ("2", "c. Algo insatisfecho/a (2)"),
                         ("3", "d. Bastante satisfecho/a (3)"),
                         ("4", "e. Muy satisfecho/a (4)"),
                         ("5", "f. Completamente satisfecho/a (5)")
                     ])
            import_q(skey, sid_egreso, gid_eg2, title="cres2_ayuda", qtype="L", order=2,
                     question_text="2. ¿En qué medida te ha ayudado el tratamiento en relación al problema específico que te llevó a pedir la atención?",
                     answers=[
                         ("A", "a. No estoy seguro/a"),
                         ("B", "b. Hizo que las cosas empeoraran bastante"),
                         ("C", "c. Hizo que las cosas empeoraran un poco"),
                         ("D", "d. No ha habido cambios"),
                         ("E", "e. Hizo que las cosas mejoraran algo"),
                         ("F", "f. Hizo que las cosas mejoraran mucho")
                     ])
            import_q(skey, sid_egreso, gid_eg2, title="cres3_emo_inicio", qtype="L", order=3,
                     question_text="3. ¿Cuál era tu estado emocional general cuando empezó el tratamiento?",
                     answers=[
                         ("A", "a. Estaba muy mal, apenas lograba hacer frente a las cosas"),
                         ("B", "b. Estaba bastante mal, la vida me resultaba a menudo muy dura"),
                         ("C", "c. Regular, tenía mis altibajos"),
                         ("D", "d. Estaba bastante bien, no tenía problemas graves"),
                         ("E", "e. Estaba muy bien, me gustaba mucho la vida que llevaba")
                     ])
            import_q(skey, sid_egreso, gid_eg2, title="cres4_emo_actual", qtype="L", order=4,
                     question_text="4. ¿Cuál es tu estado emocional en este momento?",
                     answers=[
                         ("A", "a. Estoy muy mal, apenas logro hacer frente a las cosas"),
                         ("B", "b. Estoy bastante mal, la vida es por lo general muy dura para mí"),
                         ("C", "c. Regular, tengo mis altibajos"),
                         ("D", "d. Estoy bastante bien, no tengo problemas graves"),
                         ("E", "e. Estoy muy bien, me gusta mucho la vida que llevo")
                     ])

            act_eg = rpc_call(skey, "activate_survey", [skey, sid_egreso])
            print(f"✅ Encuesta de Egreso ({sid_egreso}) activada:", act_eg)
        else:
            print(f"ℹ️ Encuesta de Egreso ({EGRESO_SID}) ya existe y está activa.")

    finally:
        rpc_call(skey, "release_session_key", [skey])


if __name__ == "__main__":
    setup_surveys()
