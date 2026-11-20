import os
import base64
import json
import httpx
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

import models
from config import settings

class LimeSurveyService:
    def __init__(self):
        self.api_url = settings.limesurvey_api_url.rstrip("/")
        self.api_key = settings.limesurvey_api_key
        self.rpc_url = settings.limesurvey_rpc_url
        self.username = settings.limesurvey_username
        self.password = settings.limesurvey_password
        self.default_sid = settings.limesurvey_default_sid
        self.access_token: Optional[str] = None
        self.use_direct_rpc_fallback: bool = False
        self.risk_keywords = [
            # Ideación / Riesgo suicida
            "suicidio", "suicida", "suicidarme", "morir", "morirme", "muerte", "matarme", "quitarme la vida", "no quiero vivir",
            # Autolesiones
            "autolesión", "autolesion", "autolesiones", "cortar", "cortarme", "lastimar", "lastimarme", "hacerme daño",
            # Violencias (intrafamiliar, género, pareja, criminal, sexual)
            "violencia", "maltrato", "golpes", "abuso", "acoso", "violación", "violacion", "agresión", "agresion", "amenaza",
            # Alucinaciones / Crisis / Psiquiatría
            "alucinación", "alucinacion", "alucinaciones", "delirio", "crisis", "emergencia", "urgencia", "internamiento", "psiquiatría", "psiquiatria",
            # Trastornos en la alimentación
            "anorexia", "bulimia", "atracón", "atracon", "vomitar", "trastorno alimenticio", "alimentación", "alimentacion",
            # Consumo problemático de sustancias
            "consumo", "sustancias", "adicción", "adiccion", "droga", "drogas", "alcohol", "marihuana", "opioides", "heroína", "heroina", "solventes", "cristal",
            # Estado afectivo y problemáticas clínicas
            "depresión", "depresion", "ansiedad", "pánico", "panico", "desesperanza", "vacío", "vacio", "tristeza", "soledad", "duelo", "pérdida", "perdida",
        ]
        self.entity_code_map = {
            "A1": "Facultad de Ciencias, UNAM",
            "A2": "Facultad de Ciencias Políticas y Sociales, UNAM",
            "A3": "Facultad de Economía, UNAM",
            "A4": "Facultad de Enfermería y Obstetricia, UNAM",
            "A5": "Facultad de Filosofía y Letras, UNAM",
            "A6": "Facultad de Ingeniería, UNAM",
            "A7": "Escuela Nacional de Artes Cinematográficas, UNAM",
            "A8": "Escuela Nacional de Ciencias de la Tierra, UNAM",
            "A9": "Escuela Nacional de Ciencias Forenses, UNAM",
            "A10": "Escuela Nacional de Trabajo Social, UNAM",
            "A11": "Colegio de Ciencias y Humanidades, Plantel Oriente",
            "A12": "Colegio de Ciencias y Humanidades, Plantel Vallejo",
            "A13": "Colegio de Ciencias y Humanidades, Plantel Sur",
            "A14": "Colegio de Ciencias y Humanidades, Plantel Naucalpan",
            "A15": "Colegio de Ciencias y Humanidades, Plantel Azcapotzalco",
            "A16": "Escuela Nacional Preparatoria, Plantel 1",
            "A17": "Escuela Nacional Preparatoria, Plantel 2",
            "A18": "Escuela Nacional Preparatoria, Plantel 3",
            "A19": "Escuela Nacional Preparatoria, Plantel 4",
            "A20": "Escuela Nacional Preparatoria, Plantel 5",
            "A21": "Escuela Nacional Preparatoria, Plantel 6",
            "A22": "Escuela Nacional Preparatoria, Plantel 7",
            "A23": "Escuela Nacional Preparatoria, Plantel 8",
            "A24": "Escuela Nacional Preparatoria, Plantel 9",
            "A25": "Instituto de Ecología, UNAM",
            "A26": "Instituto de Fisiología Celular, UNAM",
            "A27": "Instituto de Ingeniería, UNAM",
            "A28": "Instituto de Neurobiología, en Querétaro, UNAM",
            "A29": "Campus Morelos, UNAM",
            "A30": "Coordinación de Difusión y Cultura, UNAM",
            "A31": "Coordinación General de Estudios de Posgrado, UNAM",
            "A32": "Facultad de Odontología, UNAM",
        }

    def _get_api_key_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    def _rpc_call(self, method: str, params: List[Any]) -> Any:
        res = httpx.post(
            self.rpc_url,
            json={"method": method, "params": params, "id": 1},
            timeout=15,
            verify=False
        )
        res.raise_for_status()
        data = res.json()
        if data.get("error"):
            raise RuntimeError(f"RPC Error en {method}: {data['error']}")
        return data.get("result")

    def open_session(self, password: Optional[str] = None, username: Optional[str] = None, rpc_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Abre una sesión remota contra el host de LimeSurvey usando POST /v1/limesurvey/sessions
        con el header X-Api-Key y guarda el Bearer accessToken devuelto.
        Si el conector aún no tiene el host en su allowlist (LIMESURVEY_URL_NOT_ALLOWED),
        abre sesión vía JSON-RPC directo contra el servidor LimeSurvey.
        """
        pwd = password or self.password
        usr = username or self.username
        url = rpc_url or self.rpc_url

        if not pwd:
            raise ValueError("Falta configurar LIMESURVEY_PASSWORD para abrir sesión en LimeSurvey.")

        session_url = f"{self.api_url}/v1/limesurvey/sessions"
        payload = {
            "url": url,
            "username": usr,
            "password": pwd
        }
        res = httpx.post(session_url, json=payload, headers=self._get_api_key_headers(), timeout=15, verify=False)
        if res.status_code in [200, 201]:
            data = res.json()
            self.access_token = data.get("accessToken")
            self.use_direct_rpc_fallback = False
            return data

        # Fallback automático si lsapi aún no tiene ls-test.c3.unam.mx en su allowlist
        if res.status_code == 400 and "LIMESURVEY_URL_NOT_ALLOWED" in res.text:
            skey = self._rpc_call("get_session_key", [usr, pwd])
            if isinstance(skey, dict) and "status" in skey:
                raise RuntimeError(f"Error de credenciales en RPC directo: {skey}")
            self.access_token = skey
            self.use_direct_rpc_fallback = True
            return {
                "accessToken": skey,
                "tokenType": "RPC-SessionKey",
                "mode": "direct_rpc_fallback",
                "note": "lsapi devolvió LIMESURVEY_URL_NOT_ALLOWED para ls-test.c3.unam.mx; usando RPC directo + traducción vía lsapi."
            }

        raise RuntimeError(f"Error al abrir sesión en LimeSurvey ({res.status_code}): {res.text}")

    def _get_bearer_headers(self, force_refresh: bool = False) -> Dict[str, str]:
        if force_refresh or not self.access_token:
            self.open_session()
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

    def check_health(self) -> Dict[str, Any]:
        """
        Verifica el estado del microservicio limesurvey-connector en la infraestructura del C3
        y valida la autenticación por X-Api-Key en /v1/contract.
        """
        try:
            health_url = f"{self.api_url}/health"
            res = httpx.get(health_url, timeout=5, verify=False)
            contract_url = f"{self.api_url}/v1/contract"
            res_contract = httpx.get(contract_url, headers=self._get_api_key_headers(), timeout=5, verify=False)

            session_ready = bool(self.password)
            return {
                "connected": res.status_code == 200,
                "service_url": self.api_url,
                "rpc_url": self.rpc_url,
                "username": self.username,
                "api_key_valid": res_contract.status_code == 200,
                "password_configured": session_ready,
                "status_code": res.status_code,
                "contract": res_contract.json() if res_contract.status_code == 200 else res_contract.text[:200]
            }
        except Exception as e:
            return {
                "connected": False,
                "service_url": self.api_url,
                "error": str(e)
            }

    def list_surveys(self, refresh: bool = False) -> Any:
        """
        Lista las encuestas visibles para la cuenta de LimeSurvey usando el Bearer token
        (o RPC directo si lsapi aún bloquea el host de prueba).
        """
        if not self.access_token:
            self.open_session()

        if self.use_direct_rpc_fallback:
            skey = self._rpc_call("get_session_key", [self.username, self.password])
            try:
                return self._rpc_call("list_surveys", [skey, self.username])
            finally:
                self._rpc_call("release_session_key", [skey])

        url = f"{self.api_url}/v1/limesurvey/surveys"
        params = {"refresh": refresh}
        res = httpx.get(url, headers=self._get_bearer_headers(), params=params, timeout=15, verify=False)
        if res.status_code == 401:
            res = httpx.get(url, headers=self._get_bearer_headers(force_refresh=True), params=params, timeout=15, verify=False)
        if res.status_code != 200:
            raise RuntimeError(f"Error al listar encuestas ({res.status_code}): {res.text}")
        return res.json()

    def fetch_translated_responses(self, survey_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene las respuestas traducidas de una encuesta desde el microservicio usando el Bearer token
        (o exportándolas vía RPC directo cuando el host aún no está en la allowlist de lsapi).
        """
        sid = survey_id or self.default_sid
        if not sid:
            raise ValueError("No se especificó survey_id y LIMESURVEY_DEFAULT_SID no está configurado.")

        if not self.access_token:
            self.open_session()

        if self.use_direct_rpc_fallback:
            skey = self._rpc_call("get_session_key", [self.username, self.password])
            try:
                exported = self._rpc_call("export_responses", [skey, int(sid), "json", None, "all", "code", "long"])
                if isinstance(exported, dict) and "status" in exported:
                    # Por ejemplo: "No Data, survey table does not exist" (encuesta inactiva) o "No Responses found"
                    return []
                decoded = base64.b64decode(exported).decode("utf-8")
                parsed = json.loads(decoded)
                responses = parsed.get("responses", [])
                normalized = []
                for item in responses:
                    if isinstance(item, dict) and len(item) == 1 and isinstance(next(iter(item.values())), dict):
                        normalized.append(next(iter(item.values())))
                    elif isinstance(item, dict):
                        normalized.append(item)
                return normalized
            finally:
                self._rpc_call("release_session_key", [skey])

        url = f"{self.api_url}/v1/limesurvey/surveys/{sid}/responses/translated"
        headers = self._get_bearer_headers()
        res = httpx.get(url, headers=headers, timeout=20, verify=False)
        if res.status_code == 401:
            headers = self._get_bearer_headers(force_refresh=True)
            res = httpx.get(url, headers=headers, timeout=20, verify=False)

        if res.status_code != 200:
            # Fallback a endpoint estándar de respuestas si no está habilitado /translated
            fallback_url = f"{self.api_url}/v1/limesurvey/surveys/{sid}/responses"
            res_fallback = httpx.get(fallback_url, headers=headers, timeout=20, verify=False)
            if res_fallback.status_code == 200:
                data = res_fallback.json()
                return data if isinstance(data, list) else data.get("responses", data.get("records", []))
            raise RuntimeError(f"Error al obtener respuestas de LimeSurvey ({res.status_code}): {res.text}")

        data = res.json()
        if isinstance(data, list):
            return data
        return data.get("responses") or data.get("records") or []

    def ingest_single_response(self, payload: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Procesa e ingesta una respuesta traducida en la base de datos de ESPORA:
        1. Identifica/Crea el Participante.
        2. Asigna o busca la Sede correspondiente.
        3. Crea el Caso en lista de espera (status='waiting').
        4. Detecta palabras de riesgo clínico.
        5. Almacena la ficha completa en FormSubmission y FormFieldValue.
        """
        data = payload.copy()
        
        # Mapeo flexible de campos de identificación (incluye los códigos de la encuesta 118334: Nombre, cuenta, correo, entidad/facultad, telefono)
        for sys_field in ["id", "submitdate", "lastpage", "startlanguage", "seed", "startdate", "datestamp"]:
            data.pop(sys_field, None)

        full_name = data.pop("full_name", None) or data.pop("nombre_completo", None) or data.pop("nombre", None) or data.pop("Nombre", None)
        student_account = data.pop("student_account", None) or data.pop("matricula", None) or data.pop("cuenta", None) or data.pop("numero_cuenta", None)
        email = data.pop("email", None) or data.pop("correo", None) or data.pop("correo_electronico", None)
        phone = data.pop("phone", None) or data.pop("telefono", None) or data.pop("celular", None)
        faculty_site_name = data.pop("faculty_site_name", None) or data.pop("entidad", None) or data.pop("facultad", None) or data.pop("sede", None)
        if faculty_site_name and str(faculty_site_name).strip() in self.entity_code_map:
            faculty_site_name = self.entity_code_map[str(faculty_site_name).strip()]
        career = data.pop("career", None) or data.pop("carrera", None)
        gender = data.pop("gender", None) or data.pop("genero", "No especificado")
        form_name = data.pop("form_name", None) or "Ficha de Ingreso (LimeSurvey)"

        # Consolidar casillas seleccionadas de la matriz 'horarios[FRANJA_DIA]'
        day_names = {"L": "Lunes", "M": "Martes", "X": "Miércoles", "J": "Jueves", "V": "Viernes", "S": "Sábado"}
        franja_names = {"MAT": "Matutino", "MED": "Mediodía", "VES": "Vespertino"}
        selected_slots = []
        horario_keys = [k for k in list(data.keys()) if k.startswith("horarios[")]
        for hk in horario_keys:
            val = data.pop(hk, None)
            if str(val).strip() in ["1", "Y", "Sí", "Si", "true", "True"]:
                inner = hk.replace("horarios[", "").replace("]", "")
                parts = inner.split("_")
                if len(parts) == 2:
                    f_code, d_code = parts[0], parts[1]
                    selected_slots.append(f"{day_names.get(d_code, d_code)} ({franja_names.get(f_code, f_code)})")
                else:
                    selected_slots.append(inner)
        if selected_slots:
            data["horarios_disponibles"] = ", ".join(selected_slots)

        # Contactos de emergencia (encuesta 118334)
        emergency_name = data.pop("contacto1", None) or data.pop("emergency_contact_name", None)
        emergency_rel = data.pop("contacto2", None) or data.pop("conacto2", None) or data.pop("emergency_contact_relation", None)
        emergency_phone = data.pop("contacto3", None) or data.pop("emergency_contact_phone", None)

        if not full_name:
            full_name = "Aspirante LimeSurvey Sin Nombre"
        if not student_account:
            student_account = f"LS-{int(datetime.utcnow().timestamp())}"
        if not email:
            email = f"{student_account}@alumno.unam.mx"

        # Resolver Entidad / Sede: cada una de las 32 entidades tiene su propio Site en la BD
        site = None
        if faculty_site_name:
            clean_entity = str(faculty_site_name).strip()
            site = db.query(models.Site).filter(models.Site.name.ilike(f"%{clean_entity}%")).first()
            if not site:
                site = models.Site(name=clean_entity)
                db.add(site)
                db.commit()
                db.refresh(site)
        if not site:
            site = db.query(models.Site).first()
            if not site:
                site = models.Site(name="Sede Central ESPORA")
                db.add(site)
                db.commit()
                db.refresh(site)

        # Extraer o construir resumen clínico estructurado del caso (sentimiento, motivo y riesgo; horarios va en su propia columna)
        limesurvey_summary = data.pop("limesurvey_summary", None)
        if not limesurvey_summary:
            ordered_labels = [
                ("sentimiento", "Sentimiento"),
                ("motivo", "Motivo"),
                ("actualmente", "Riesgo actual"),
            ]
            summary_parts = []
            for field_key, label in ordered_labels:
                val = data.get(field_key)
                if val is not None and str(val).strip():
                    summary_parts.append(f"**{label}:** {str(val).strip()}")
            if not summary_parts:
                summary_parts = [f"{k}: {v}" for k, v in data.items() if isinstance(v, str) and v.strip()]
            limesurvey_summary = " | ".join(summary_parts) if summary_parts else "Respuesta procesada desde LimeSurvey"

        # Detectar palabras de riesgo
        found_risks = []
        full_text_to_scan = f"{limesurvey_summary} " + " ".join(str(v) for v in data.values())
        lower_scan = full_text_to_scan.lower()
        for kw in self.risk_keywords:
            if kw in lower_scan:
                found_risks.append(kw.upper())

        metadata_payload = {
            "resumen_caso": limesurvey_summary,
            "horarios_disponibles": data.get("horarios_disponibles", ""),
            "sentimiento": data.get("sentimiento", ""),
            "motivo": data.get("motivo", ""),
            "situacion_riesgo": data.get("actualmente", ""),
            "entidad": site.name,
        }

        # Buscar o crear participante asignado a la base de datos de su Entidad (site.id)
        participant = db.query(models.Participant).filter(models.Participant.student_account == str(student_account).strip()).first()
        is_new_participant = False
        if not participant:
            is_new_participant = True
            participant = models.Participant(
                full_name=str(full_name).strip(),
                student_account=str(student_account).strip(),
                email=str(email).strip(),
                phone=str(phone).strip() if phone else None,
                gender=str(gender).strip(),
                emergency_contact_name=str(emergency_name).strip() if emergency_name else None,
                emergency_contact_relation=str(emergency_rel).strip() if emergency_rel else None,
                emergency_contact_phone=str(emergency_phone).strip() if emergency_phone else None,
                faculty=site.name,
                career=str(career).strip() if career else None,
                site_id=site.id,
                metadata_json=metadata_payload,
                limesurvey_summary=limesurvey_summary
            )
            db.add(participant)
            db.commit()
            db.refresh(participant)

            # Folio anónimo institucional: 2 dígitos de sede + 5 dígitos de participante
            participant.anonymous_folio = f"{site.id:02d}{participant.id:05d}"
            db.commit()
            db.refresh(participant)
        else:
            participant.site_id = site.id
            participant.faculty = site.name
            participant.metadata_json = metadata_payload
            if emergency_name:
                participant.emergency_contact_name = str(emergency_name).strip()
            if emergency_rel:
                participant.emergency_contact_relation = str(emergency_rel).strip()
            if emergency_phone:
                participant.emergency_contact_phone = str(emergency_phone).strip()
            if limesurvey_summary:
                participant.limesurvey_summary = limesurvey_summary
            db.commit()

        # Verificar si ya existe un caso activo o en espera para este participante
        existing_case = db.query(models.Case).filter(
            models.Case.participant_id == participant.id,
            models.Case.status.in_([models.CaseStatusEnum.WAITING, models.CaseStatusEnum.ACTIVE])
        ).first()

        created_case = False
        if not existing_case:
            case = models.Case(
                participant_id=participant.id,
                site_id=site.id,
                status=models.CaseStatusEnum.WAITING,
                intake_source="limesurvey"
            )
            db.add(case)
            db.commit()
            db.refresh(case)
            created_case = True
        else:
            case = existing_case

        # Registrar FormTemplate y FormSubmission para auditoría clínica
        template = db.query(models.FormTemplate).filter(models.FormTemplate.name == form_name).first()
        if not template:
            template = models.FormTemplate(
                name=form_name,
                description="Plantilla autogenerada desde sincronización con LimeSurvey"
            )
            db.add(template)
            db.commit()
            db.refresh(template)

        submission = models.FormSubmission(
            form_template_id=template.id,
            participant_id=participant.id,
            case_id=case.id
        )
        db.add(submission)
        db.flush()

        for key, value in data.items():
            if value is None or str(value).strip() == "":
                continue

            field = db.query(models.FormField).filter(
                models.FormField.form_template_id == template.id,
                models.FormField.name == key
            ).first()

            if not field:
                field = models.FormField(
                    form_template_id=template.id,
                    name=key,
                    label=key.replace('_', ' ').capitalize(),
                    field_type=models.FieldTypeEnum.STRING
                )
                db.add(field)
                db.flush()

            field_val = models.FormFieldValue(
                form_submission_id=submission.id,
                form_field_id=field.id,
                value_text=str(value)
            )
            db.add(field_val)

        db.commit()

        return {
            "case_id": case.id,
            "participant_id": participant.id,
            "folio": participant.anonymous_folio,
            "full_name": participant.full_name,
            "site_id": site.id,
            "site_name": site.name,
            "horarios_disponibles": data.get("horarios_disponibles", ""),
            "is_new_participant": is_new_participant,
            "created_case": created_case,
            "risk_words_found": found_risks,
            "is_high_risk": len(found_risks) >= 2
        }

    def ingest_followup_response(self, payload: Dict[str, Any], form_name: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Vincula una respuesta de las encuestas de seguimiento enviadas por el terapeuta
        (228334: Información Complementaria de Inicio | 338334: Formato de Egreso CRES-4)
        al expediente del paciente mediante su 'folio' o 'student_account' (No. de cuenta).
        """
        data = payload.copy()
        response_id = str(data.pop("id", ""))
        for sys_field in ["submitdate", "lastpage", "startlanguage", "seed", "startdate", "datestamp", "quota_exit"]:
            data.pop(sys_field, None)

        folio_or_account = str(data.pop("folio", "") or data.pop("cuenta", "") or "").strip()
        if not folio_or_account:
            return None

        participant = db.query(models.Participant).filter(
            (models.Participant.anonymous_folio == folio_or_account) |
            (models.Participant.student_account == folio_or_account)
        ).first()
        if not participant:
            return None

        case = db.query(models.Case).filter(models.Case.participant_id == participant.id).order_by(models.Case.id.desc()).first()
        if not case:
            return None

        # Consolidar preguntas de opción múltiple (areas_afectadas[...] o areas_mejoria[...])
        multi_prefixes = {
            "areas_afectadas[": ("areas_afectadas", {
                "ESC": "Escolar", "FAM": "Familiar", "SOC": "Social", "LAB": "Laboral",
                "PAR": "Pareja", "SEX": "Sexual", "EMO": "Emocional", "OTR": "Otra"
            }),
            "areas_mejoria[": ("areas_mejoria", {
                "A1": "Escolar", "A2": "Familiar", "A3": "Social", "A4": "Laboral",
                "A5": "Pareja", "A6": "Sexual", "A7": "Emocional", "A8": "Otra", "A9": "Ninguna"
            })
        }
        for prefix, (target_key, code_map) in multi_prefixes.items():
            matched_keys = [k for k in list(data.keys()) if k.startswith(prefix)]
            selected_items = []
            for mk in matched_keys:
                val = data.pop(mk, None)
                if str(val).strip() in ["1", "Y", "Sí", "Si", "true", "True"]:
                    code = mk.replace(prefix, "").replace("]", "")
                    selected_items.append(code_map.get(code, code))
            if selected_items:
                data[target_key] = ", ".join(selected_items)

        template = db.query(models.FormTemplate).filter(models.FormTemplate.name == form_name).first()
        if not template:
            template = models.FormTemplate(
                name=form_name,
                description=f"Cuestionario sincronizado desde LimeSurvey ({form_name})"
            )
            db.add(template)
            db.commit()
            db.refresh(template)

        # Evitar duplicar la misma respuesta de LimeSurvey si ya fue importada para este caso y plantilla
        if response_id:
            existing_subs = db.query(models.FormSubmission).filter(
                models.FormSubmission.case_id == case.id,
                models.FormSubmission.form_template_id == template.id
            ).all()
            for sub in existing_subs:
                for fv in sub.field_values:
                    if fv.field and fv.field.name == "limesurvey_response_id" and fv.value_text == response_id:
                        return {
                            "case_id": case.id,
                            "participant_id": participant.id,
                            "folio": participant.anonymous_folio,
                            "form_name": form_name,
                            "already_synced": True
                        }
            data["limesurvey_response_id"] = response_id

        submission = models.FormSubmission(
            form_template_id=template.id,
            participant_id=participant.id,
            case_id=case.id
        )
        db.add(submission)
        db.flush()

        for key, value in data.items():
            if value is None or str(value).strip() == "":
                continue
            field = db.query(models.FormField).filter(
                models.FormField.form_template_id == template.id,
                models.FormField.name == key
            ).first()
            if not field:
                field = models.FormField(
                    form_template_id=template.id,
                    name=key,
                    label=key.replace("_", " ").capitalize(),
                    field_type=models.FieldTypeEnum.STRING
                )
                db.add(field)
                db.flush()

            db.add(models.FormFieldValue(
                form_submission_id=submission.id,
                form_field_id=field.id,
                value_text=str(value)
            ))

        # Si es la encuesta de Información de Inicio, autocompletar edad y semestre en CaseProcessData
        if "edad" in data or "ciclo_ingreso" in data:
            proc = db.query(models.CaseProcessData).filter(models.CaseProcessData.case_id == case.id).first()
            if not proc:
                proc = models.CaseProcessData(case_id=case.id)
                db.add(proc)
            try:
                if data.get("edad") and str(data["edad"]).strip().isdigit():
                    proc.edad = int(float(str(data["edad"]).strip()))
            except Exception:
                pass
            if data.get("ciclo_ingreso") and not proc.semestre_inicio:
                proc.semestre_inicio = str(data["ciclo_ingreso"]).strip()

        db.commit()
        return {
            "case_id": case.id,
            "participant_id": participant.id,
            "folio": participant.anonymous_folio,
            "form_name": form_name,
            "already_synced": False
        }

    def sync_responses(self, survey_id: Optional[str], db: Session) -> Dict[str, Any]:
        """
        Ejecuta la sincronización completa de encuestas hacia la base de datos de ESPORA:
        - Encuesta 118334 (Primer contacto -> Lista de Espera por Entidad)
        - Encuesta 228334 (Información Complementaria de Inicio -> Expediente del Paciente)
        - Encuesta 338334 (Formato de Egreso y Satisfacción CRES-4 -> Expediente del Paciente)
        """
        responses = self.fetch_translated_responses(survey_id)
        report = {
            "total_fetched": len(responses),
            "new_cases": 0,
            "updated_cases": 0,
            "new_participants": 0,
            "high_risk_alerts": 0,
            "followup_submissions": 0,
            "details": []
        }

        for item in responses:
            try:
                res = self.ingest_single_response(item, db)
                if res["created_case"]:
                    report["new_cases"] += 1
                else:
                    report["updated_cases"] += 1
                if res["is_new_participant"]:
                    report["new_participants"] += 1
                if res["is_high_risk"]:
                    report["high_risk_alerts"] += 1
                report["details"].append(res)
            except Exception as e:
                report["details"].append({"error": str(e), "raw": item})

        # Sincronizar también las 2 encuestas de seguimiento del perfil (228334 Inicio y 338334 Egreso CRES-4)
        followup_surveys = [
            ("228334", "Información Complementaria de Inicio (LimeSurvey)"),
            ("338334", "Formato de Egreso y Satisfacción CRES-4 (LimeSurvey)")
        ]
        for f_sid, f_name in followup_surveys:
            try:
                f_responses = self.fetch_translated_responses(f_sid)
                for f_item in f_responses:
                    f_res = self.ingest_followup_response(f_item, f_name, db)
                    if f_res and not f_res.get("already_synced"):
                        report["followup_submissions"] += 1
                        report["details"].append(f_res)
            except Exception:
                pass

        return report

limesurvey_service = LimeSurveyService()
