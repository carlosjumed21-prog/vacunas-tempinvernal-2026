import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID

def obtener_cliente_gspread():
    """
    Autentica y retorna el cliente de gspread utilizando los secretos de Streamlit
    o un archivo local de respaldo.
    """
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Cargar credenciales desde st.secrets de manera segura
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        else:
            # Fallback a archivo local si no está en st.secrets
            creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    except Exception:
        # Fallback de emergencia a archivo local
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        
    client = gspread.authorize(creds)
    return client

def obtener_token_acceso():
    """
    Retorna las credenciales o el objeto de autorización para mantener 
    compatibilidad con módulos externos.
    """
    client = obtener_cliente_gspread()
    return client.auth

def guardar_registro_censal(sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente):
    """
    Guarda el registro censal de forma nativa en Google Sheets utilizando gspread,
    evitando conflictos con celdas o encabezados vacíos y controlando errores de API.
    """
    client = obtener_cliente_gspread()
    
    # Abrir la hoja de cálculo nativa por su ID configurado
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    except Exception as e:
        raise Exception(f"No se pudo abrir el documento de Google Sheets (Verifica el ID o permisos de la cuenta de servicio): {e}")
    
    # Seleccionar la pestaña activa o la hoja correspondiente
    try:
        worksheet = spreadsheet.worksheet("CENSO NOMINAL")
    except gspread.exceptions.WorksheetNotFound:
        try:
            worksheet = spreadsheet.get_worksheet(0) # Fallback a la primera pestaña
        except Exception as e:
            raise Exception(f"No se pudo acceder a ninguna pestaña válida en el documento: {e}")

    # Obtener todas las filas como valores planos para evitar errores de encabezados vacíos
    try:
        filas_existentes = worksheet.get_all_values()
    except Exception as e:
        raise Exception(f"Error al leer los valores de la hoja de Google Sheets (Posible bloqueo de API o respuesta vacía): {e}")
      
    # El conteo actual considera el total de filas actuales (incluyendo cabecera)
    conteo_actual = len(filas_existentes)
    
    fecha_str = val_fecha_app.strftime("%Y%m%d")
    sufijo_unidad = f"-{sufijo_js}" if sufijo_js else ""
    folio_asignado = f"{fecha_str}-{tipo_jornada}-{sigla_url}{sufijo_unidad}-{conteo_actual:04d}"

    # Estructura de datos a insertar en la fila de Google Sheets
    fila_a_insertar = [
        conteo_actual,
        folio_asignado,
        datos_paciente.get("paterno", "").upper(),
        datos_paciente.get("materno", "").upper(),
        datos_paciente.get("nombres", "").upper(),
        datos_paciente.get("correo_paciente", "")
    ]

    # Insertar la fila de manera nativa
    try:
        worksheet.append_row(fila_a_insertar)
    except Exception as e:
        raise Exception(f"Error al insertar el registro en Google Sheets: {e}")

    return folio_asignado, False, None

def verificar_curp_duplicada(curp_con_nacimiento, sigla, sufijo, tipo_jornada, fecha_aplicacion):
    """
    Verifica si una CURP ya se encuentra registrada en la hoja de cálculo de forma nativa.
    """
    client = obtener_cliente_gspread()
    
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    except Exception as e:
        raise Exception(f"No se pudo abrir el documento para verificar duplicados: {e}")
    
    try:
        worksheet = spreadsheet.worksheet("CENSO NOMINAL")
    except gspread.exceptions.WorksheetNotFound:
        try:
            worksheet = spreadsheet.get_worksheet(0)
        except Exception as e:
            raise Exception(f"No se pudo acceder a la pestaña para validar duplicados: {e}")

    try:
        registros = worksheet.get_all_values()
    except Exception as e:
        raise Exception(f"Error al leer los registros existentes: {e}")
    
    # Búsqueda de duplicados recorriendo las filas de la hoja nativa
    for fila in registros[1:]: # Omitir cabecera
        if len(fila) > 1 and curp_con_nacimiento in str(fila):
            folio_previo = fila[1] if len(fila) > 1 else "S/N"
            return True, folio_previo

    return False, None
