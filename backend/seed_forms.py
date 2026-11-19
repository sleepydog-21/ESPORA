import os
import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from models import FormTemplate, FormField, FieldTypeEnum

def seed_forms():
    db = SessionLocal()
    
    # Ficha de Ingreso
    ingreso_template = db.query(FormTemplate).filter_by(name="Ficha de Ingreso").first()
    if not ingreso_template:
        ingreso_template = FormTemplate(name="Ficha de Ingreso", description="Formato inicial de captura clínica y demográfica.")
        db.add(ingreso_template)
        db.commit()
        db.refresh(ingreso_template)
        
        fields_ingreso = [
            {"name": "materias_adeudadas", "label": "Número de materias adeudadas", "type": FieldTypeEnum.INTEGER},
            {"name": "horarios", "label": "¿Cuáles son tus horarios disponibles para asistir a las sesiones?", "type": FieldTypeEnum.TEXT},
            {"name": "atencion_previa", "label": "¿Anteriormente habías asistido a algún espacio de atención psicológica?", "type": FieldTypeEnum.BOOLEAN},
            {"name": "motivo_consulta", "label": "¿Cuáles son tus motivos de consulta?", "type": FieldTypeEnum.TEXT},
            {
                "name": "areas_afectadas", 
                "label": "¿Cuáles de las siguientes áreas se han visto afectadas en tu vida en relación con tu motivo de consulta?", 
                "type": FieldTypeEnum.STRING,
                "options": ["Escolar", "Familiar", "Social", "Laboral", "Pareja", "Sexual", "Emocional", "Otra"]
            },
            {
                "name": "estado_actual",
                "label": "¿Cómo te sientes actualmente?",
                "type": FieldTypeEnum.STRING,
                "options": ["Muy mal", "Mal", "Regular", "Bien", "Muy bien"]
            }
        ]
        
        for f in fields_ingreso:
            db.add(FormField(
                form_template_id=ingreso_template.id,
                name=f["name"],
                label=f["label"],
                field_type=f["type"],
                options=f.get("options", None)
            ))
            
        print("Ficha de Ingreso sembrada correctamente.")
    else:
        print("Ficha de Ingreso ya existía.")

    # Ficha de Egreso
    egreso_template = db.query(FormTemplate).filter_by(name="Ficha de Egreso").first()
    if not egreso_template:
        egreso_template = FormTemplate(name="Ficha de Egreso", description="Formato de cierre de tratamiento.")
        db.add(egreso_template)
        db.commit()
        db.refresh(egreso_template)
        
        fields_egreso = [
            {
                "name": "ayuda_tratamiento",
                "label": "¿Qué tanto te ayudó el tratamiento en relación a tu motivo de consulta?",
                "type": FieldTypeEnum.STRING,
                "options": ["No me ayudó", "Me ayudó poco", "Me ayudó moderadamente", "Me ayudó mucho", "Me ayudó totalmente"]
            },
            {
                "name": "areas_mejoria",
                "label": "Si piensas que el tratamiento te ayudó, ¿cuáles fueron las áreas en las que notaste una mejoría?",
                "type": FieldTypeEnum.STRING,
                "options": ["Escolar", "Familiar", "Social", "Laboral", "Pareja", "Sexual", "Emocional", "Otra"]
            },
            {
                "name": "estado_actual_egreso",
                "label": "¿Cómo te sientes actualmente?",
                "type": FieldTypeEnum.STRING,
                "options": ["Muy mal", "Mal", "Regular", "Bien", "Muy bien"]
            },
            {
                "name": "calidad_atencion",
                "label": "¿Del 1 al 10 cómo calificarías la calidad de la atención recibida?",
                "type": FieldTypeEnum.INTEGER
            },
            {
                "name": "recomendacion",
                "label": "¿Qué tanto recomendarías el servicio a otros estudiantes?",
                "type": FieldTypeEnum.STRING,
                "options": ["Nada", "Poco", "Medio", "Mucho", "Completamente"]
            },
            {
                "name": "mas_agrado",
                "label": "¿Qué es lo que más te agradó de este servicio?",
                "type": FieldTypeEnum.TEXT
            },
            {
                "name": "menos_agrado",
                "label": "¿Qué es lo que menos te agradó de este servicio?",
                "type": FieldTypeEnum.TEXT
            }
        ]
        
        for f in fields_egreso:
            db.add(FormField(
                form_template_id=egreso_template.id,
                name=f["name"],
                label=f["label"],
                field_type=f["type"],
                options=f.get("options", None)
            ))
            
        print("Ficha de Egreso sembrada correctamente.")
    else:
        print("Ficha de Egreso ya existía.")

    db.commit()
    db.close()

if __name__ == "__main__":
    seed_forms()
