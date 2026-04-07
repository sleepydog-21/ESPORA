import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])

try:
    import pandas as pd
except ImportError:
    install("pandas")
    import pandas as pd

try:
    import docx
except ImportError:
    install("python-docx")
    import docx

try:
    import PyPDF2
except ImportError:
    install("PyPDF2")
    import PyPDF2

try:
    import openpyxl
except ImportError:
    install("openpyxl")
    import openpyxl

import os

base_dir = "referencias"

output = open("referencias_dump.txt", "w")

# process docx
docx_path = os.path.join(base_dir, "Correo respuesta 1er contacto.docx")
try:
    doc = docx.Document(docx_path)
    output.write("--- Correo respuesta 1er contacto.docx ---\n")
    for para in doc.paragraphs:
        output.write(para.text + "\n")
    output.write("\n\n")
except Exception as e:
    output.write(f"Error reading docx: {e}\n\n")

# process pdfs
for pdf_file in ["Formato de Ingreso 2021.pdf", "Formato de egreso 2021.pdf"]:
    pdf_path = os.path.join(base_dir, pdf_file)
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        output.write(f"--- {pdf_file} ---\n")
        for i, page in enumerate(reader.pages):
            output.write(page.extract_text() + "\n")
        output.write("\n\n")
    except Exception as e:
        output.write(f"Error reading {pdf_file}: {e}\n\n")

# process xlsx columns (not full data, just sheets and columns)
for xlsx_file in ["Conglomerado de información semestral ESPORA .xlsx", "NUEVA BASE DE DATOS PREPAS.xlsx"]:
    xlsx_path = os.path.join(base_dir, xlsx_file)
    try:
        output.write(f"--- {xlsx_file} ---\n")
        xl = pd.ExcelFile(xlsx_path)
        for sheet_name in xl.sheet_names:
            df = xl.parse(sheet_name)
            output.write(f"Sheet: {sheet_name}\n")
            output.write("Columns: " + ", ".join(map(str, df.columns.tolist()[:50])) + "\n")
            # dump first row to see examples
            if len(df) > 0:
                output.write("Sample row: \n" + str(df.iloc[0].to_dict())[:1000] + "\n")
        output.write("\n\n")
    except Exception as e:
        output.write(f"Error reading {xlsx_file}: {e}\n\n")

output.close()
print("Dumping finished.")
