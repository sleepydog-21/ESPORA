import sys
import os
import math
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database import SessionLocal
import models
import auth

def is_nan(val):
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    if str(val).strip() == "" or str(val).lower() == "nan":
        return True
    return False

def run_import():
    file_path = "/app/bases_de_datos/base de datos 1.xlsx"
    if not os.path.exists(file_path):
        print(f"File {file_path} not found inside container.")
        return
        
    print(f"Reading {file_path}...")
    df = pd.read_excel(file_path)
    
    # Identify dynamic fields from column 3 to 9 (D to J)
    # The user mentioned columns "a D la J" (D to J) which is usually col index 3 to 9
    dynamic_column_names = df.columns[3:10].tolist()
    print("Found dynamic columns:", dynamic_column_names)
    
    db = SessionLocal()
    
    try:
        # 1. Register new FieldDefinitions if they don't exist
        field_defs_map = {}
        for col_name in dynamic_column_names:
            safe_name = str(col_name).strip().lower().replace(" ", "_").replace(".", "")
            db_field = db.query(models.FieldDefinition).filter_by(name=safe_name).first()
            if not db_field:
                db_field = models.FieldDefinition(
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
            # The Name is in the second column (index 1)
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
                existing_val = db.query(models.FieldValue).filter_by(
                    participant_id=participant.id,
                    field_definition_id=field_def.id
                ).first()
                
                if existing_val:
                    if existing_val.value != val_str:
                        existing_val.value = val_str
                        existing_val.updated_by_id = admin_id
                else:
                    new_val = models.FieldValue(
                        participant_id=participant.id,
                        field_definition_id=field_def.id,
                        value=val_str,
                        updated_by_id=admin_id
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
