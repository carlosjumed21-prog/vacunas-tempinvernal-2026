
import datetime
import gspread
from google.oauth2.service_account import Credentials

# Configuración de credenciales de Google Sheets (puedes ajustar según tu inicialización existente)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def obtener_conexion_sheets():
    # Ajusta esto según cómo cargues tus credenciales en el proyecto (ej. st.secrets)
    import streamlit as st
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    return None

def guardar_registro_censal_20_nov(datos):
    """
    Función exclusiva para registrar los datos censales del CMN 20 de Noviembre
    en su propia hoja o pestaña de Google Sheets, sin afectar a otras unidades.
    """
    client = obtener_conexion_sheets()
    if not client:
        raise Exception("No se pudo establecer la conexión con Google Sheets.")
    
    # Aquí defines la hoja de cálculo y la pestaña específica para el 20 de Noviembre
    # Puedes usar el ID de tu Google Sheet institucional o un nombre de archivo
    # Ejemplo: spreadsheet_id = st.secrets["SHEET_ID_20_NOV"] o abrir por título:
    sheet_url = "ID_O_NOMBRE_DE_TU_GOOGLE_SHEET_DEL_20_NOV" # Reemplaza con tu Sheet ID o título
    
    try:
        # Si prefieres abrir por clave de secreto o URL directa:
        # spreadsheet = client.open_by_key(st.secrets["SHEET_ID_20_NOV"])
        # worksheet = spreadsheet.worksheet("Censo_20_Nov")
        
        # Ejemplo genérico adaptado a tu flujo:
        # (Asegúrate de cambiar esto por la lógica exacta que usabas en el sheets.py general pero apuntando al 20 de Nov)
        
        # Generar un folio único basado en timestamp o contador
        folio = f"20N-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Preparar la fila con los datos recibidos en el diccionario 'datos'
        fila = [
            folio,
            datos.get("rfc", ""),
            datos.get("curp", ""),
            datos.get("paterno", ""),
            datos.get("materno", ""),
            datos.get("nombre", ""),
            datos.get("sexo", ""),
            datos.get("anos", 0),
            datos.get("meses", 0),
            datos.get("vacuna_interes", ""),
            str(datos.get("val_fecha_app", ""))
        ]
        
        # worksheet.append_row(fila)
        
        return folio
    except Exception as e:
        raise Exception(f"Error al guardar en Google Sheets (20 de Nov): {e}")
