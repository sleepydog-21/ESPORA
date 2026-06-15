import sys
import os
import math
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database import SessionLocal
import models

def is_nan(val):
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    if str(val).strip() == "" or str(val).lower() == "nan":
        return True
    return False

def run_import():
    file_path = "/app/datos/historicos/registro_historico_prepas.xlsx"
    if not os.path.exists(file_path):
        print(f"File {file_path} not found inside container.")
        return
        
    print(f"Reading {file_path}...")
    df = pd.read_excel(file_path)
    
    # Identify dynamic fields from column 3 to 9 (D to J)
    dynamic_column_names = df.columns[3:10].tolist()
    print("Found dynamic columns:", dynamic_column_names)
    
    db = SessionLocal()
    
    try:
        # 1. Register new FormTemplate if it doesn't exist
        template_name = "Ficha de Ingreso Histórica (Excel)"
        template = db.query(models.FormTemplate).filter_by(name=template_name).first()
        if not template:
            template = models.FormTemplate(
                name=template_name,
                description="Plantilla de cuestionario autogenerada para almacenar importaciones del Excel histórico de prepas.",
                is_active=True
            )
            db.add(template)
            db.commit()
            db.refresh(template)
            
        print(f"Template '{template_name}' ready.")

        # 2. Register FormFields for dynamic columns if they don't exist
        field_defs_map = {}
        for col_name in dynamic_column_names:
            safe_name = str(col_name).strip().lower().replace(" ", "_").replace(".", "")
            db_field = db.query(models.FormField).filter_by(
                form_template_id=template.id,
                name=safe_name
            ).first()
            if not db_field:
                db_field = models.FormField(
                    form_template_id=template.id,
                    name=safe_name,
                    label=str(col_name).strip(),
                    field_type=models.FieldTypeEnum.STRING
                )
                db.add(db_field)
                db.commit()
                db.refresh(db_field)
            field_defs_map[str(col_name)] = db_field
            
        print("Dynamic fields mapped in DB.")

        # Admin user to link updates to
        admin_user = db.query(models.User).filter_by(role=models.RoleEnum.ADMIN).first()
        admin_id = admin_user.id if admin_user else None
        
        # We need a fallback site in case we create new participants
        fallback_site = db.query(models.Site).first()

        participants_created = 0
        rubros_inserted = 0

        # Iterating the rows
        for index, row in df.iterrows():
            name_val = row.iloc[1]
            if str(name_val).strip() == "paterno materno nombre (s)":
                continue
                
            if is_nan(name_val):
                identifier = f"Paciente_Historico_{index}"
            else:
                identifier = str(name_val).strip()
            
            # Find participant by student_account or name
            participant = db.query(models.Participant).filter(
                (models.Participant.student_account == identifier) | 
                (models.Participant.full_name == identifier)
            ).first()
            
            if not participant:
                # Create dummy participant to store the data
                student_acc = f"IMP-{index}"
                name = identifier
                participant = models.Participant(
                    full_name=name,
                    student_account=student_acc,
                    email=f"imported_{index}@example.com",
                    site_id=fallback_site.id if fallback_site else 1
                )
                db.add(participant)
                db.commit()
                db.refresh(participant)
                participants_created += 1
                
            # Create a FormSubmission for this participant
            submission = db.query(models.FormSubmission).filter_by(
                form_template_id=template.id,
                participant_id=participant.id
            ).first()
            if not submission:
                submission = models.FormSubmission(
                    form_template_id=template.id,
                    participant_id=participant.id,
                    submitted_by_id=admin_id
                )
                db.add(submission)
                db.flush()
                
            # Process dynamic columns
            for col_name in dynamic_column_names:
                cell_value = row[col_name]
                if is_nan(cell_value):
                    continue
                    
                field_def = field_defs_map.get(str(col_name))
                if not field_def:
                    continue
                    
                val_str = str(cell_value).strip()
                
                # Check if exists
                existing_val = db.query(models.FormFieldValue).filter_by(
                    form_submission_id=submission.id,
                    form_field_id=field_def.id
                ).first()
                
                if existing_val:
                    if existing_val.value_text != val_str:
                        existing_val.value_text = val_str
                else:
                    new_val = models.FormFieldValue(
                        form_submission_id=submission.id,
                        form_field_id=field_def.id,
                        value_text=val_str
                    )
                    db.add(new_val)
                    rubros_inserted += 1

        db.commit()
        print(f"Success! Created {participants_created} missing participants.")
        print(f"Imported {rubros_inserted} field values from Excel.")

    except Exception as e:
        print(f"Error during import: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_import()
