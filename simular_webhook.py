import requests
import json
import time

URL = "http://localhost:8000/webhooks/limesurvey"
HEADERS = {
    "Content-Type": "application/json",
    "X-LimeSurvey-Token": "supersecret123"
}

# 1. Simular que el paciente llena la Ficha de Ingreso
ingreso_payload = {
  "form_name": "Ficha de Ingreso",
  "full_name": "Ana Sofia López Vega",
  "student_account": "415123456",
  "email": "anasofia.lopez@alumno.unam.mx",
  "phone": "5512349876",
  "faculty_site_name": "Facultad de Odontología",
  "career": "Cirujano Dentista",
  "gender": "Femenino",
  
  "materias_adeudadas": "0",
  "horarios": "Martes y Jueves de 9:00am a 2:00pm",
  "atencion_previa": "No",
  "motivo_consulta": "Últimamente me he sentido con mucha ansiedad cuando atiendo pacientes en la clínica, me sudan las manos y no puedo dormir una noche antes.",
  "areas_afectadas": "Escolar, Emocional",
  "estado_actual": "Mal"
}

print("Enviando Ficha de Ingreso...")
res1 = requests.post(URL, json=ingreso_payload, headers=HEADERS)
print("Respuesta:", res1.status_code, res1.text)

time.sleep(2)

# 2. Simular un cuestionario de seguimiento unas semanas después
seguimiento_payload = {
  "form_name": "Cuestionario de Seguimiento",
  "full_name": "Ana Sofia López Vega",
  "student_account": "415123456",
  "faculty_site_name": "Facultad de Odontología",
  
  "ansiedad_nivel_actual": "3",
  "horas_sueno": "7 horas",
  "comentarios_avance": "Me he sentido mucho mejor en la clínica, ya no me sudan las manos."
}

print("\nEnviando Cuestionario de Seguimiento...")
res2 = requests.post(URL, json=seguimiento_payload, headers=HEADERS)
print("Respuesta:", res2.status_code, res2.text)

print("\n¡Listo! Revisa la plataforma.")
