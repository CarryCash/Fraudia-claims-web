import os
import json
from io import BytesIO
# pyrefly: ignore [missing-import]
import PyPDF2
from google import genai
from google.genai import types

def extract_text_from_pdf(pdf_file) -> str:
    """Extracts text from a PDF file using PyPDF2."""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""

def validate_pdf_with_gemini(pdf_file, claim_data: dict) -> dict:
    """
    Extracts text from the PDF and uses Gemini to cross-validate
    dates, amounts, and names against the provided claim data.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"isValid": False, "inconsistencies": ["Error: GEMINI_API_KEY no configurado."]}

    # Extract text from the PDF
    pdf_text = extract_text_from_pdf(pdf_file)
    if not pdf_text:
        return {"isValid": True, "inconsistencies": ["No se pudo extraer texto del PDF (puede ser una imagen escaneada)."]}
    
    # Cap text length to avoid token limits for very large PDFs
    if len(pdf_text) > 30000:
        pdf_text = pdf_text[:30000]

    system_instruction = """
    Eres un auditor antifraude experto de seguros. 
    Tu tarea es comparar los datos extraídos de un documento PDF con los datos declarados del siniestro en el sistema.
    Debes validar ÚNICAMENTE los siguientes 3 puntos:
    1. Cruce de Fechas: ¿La fecha de emisión o fechas mencionadas en el documento coinciden o son lógicas respecto a la Fecha de Ocurrencia y Fecha de Reporte del sistema? (Ej. Un documento emitido mucho ANTES de la póliza o mucho DESPUÉS es sospechoso).
    2. Cruce de Montos: Si el documento menciona montos (ej. facturas, cotizaciones), ¿coinciden con el Monto Reclamado en el sistema?
    3. Validación de Nombres: ¿El nombre del beneficiario, proveedor o asegurado mencionado en el documento coincide con los del sistema?

    Responde en formato JSON estructurado EXACTAMENTE como esto:
    {
      "isValid": true o false (false si detectas alguna inconsistencia grave),
      "inconsistencies": [
         "Mensaje claro y breve explicando la inconsistencia 1",
         "Mensaje claro y breve explicando la inconsistencia 2"
      ]
    }
    
    Si no detectas inconsistencias graves, o la información no está en el documento para poder cruzarla, devuelve "isValid": true y la lista de "inconsistencies" vacía.
    """

    prompt = f"""
    DATOS DEL SINIESTRO EN EL SISTEMA:
    - Fecha Ocurrencia: {claim_data.get('fecha_ocurrencia', 'No especificada')}
    - Fecha Reporte: {claim_data.get('fecha_reporte', 'No especificada')}
    - Monto Reclamado: {claim_data.get('monto_reclamado', 'No especificado')}
    - Beneficiario/Proveedor: {claim_data.get('beneficiario', 'No especificado')}
    - Asegurado ID: {claim_data.get('id_asegurado', 'No especificado')}
    
    TEXTO EXTRAÍDO DEL DOCUMENTO PDF:
    \"\"\"
    {pdf_text}
    \"\"\"
    
    Verifica las fechas, montos y nombres e indica las inconsistencias en JSON.
    """

    try:
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1, # Low temp for deterministic checks
            response_mime_type="application/json",
        )
        
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite", # Fast and cheap for validation
            contents=prompt,
            config=config
        )
        
        result_text = response.text.strip()
        result_json = json.loads(result_text)
        return result_json
    except Exception as e:
        print(f"Error validating with Gemini: {e}")
        return {"isValid": False, "inconsistencies": [f"Error al analizar con IA: {str(e)}"]}
