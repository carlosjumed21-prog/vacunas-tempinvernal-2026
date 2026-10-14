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
    
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    except Exception:
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

def _obtener_worksheet_dinamica(spreadsheet, sigla_url, tipo_jornada, val_fecha_app):
    """
    Intenta localizar la pestaña correspondiente a la jornada actual 
    (ej. TLA_EXTRA_141026, DVN_INTRA_121026, etc.) o recurre a 'CENSO NOMINAL'.
    """
    # Construir el sufijo de modalidad (Ej: INTRA, EXTRA, MOVIL)
    mod_map = {"I": "INTRA", "E": "EXTRA", "M": "MOV"}
    tipo_str = mod_map.get(tipo_jornada.upper(), "INTRA")
    fecha_sufijo = val_fecha_app.strftime("%d%m%y")
    
    # Nombres posibles de pestañas basados en tu estructura operativa
    nombres_candidatos = [
        f"{sigla_url.upper()}_{tipo_str}_{fecha_sufijo}",
        f"{sigla_url.upper()}_EXTRA_{fecha_sufijo}",
        f"{sigla_url.upper()}_INTRA_{fecha_sufijo}",
        "CENSO NOMINAL"
    ]
    
    for nombre in nombres_candidatos:
        try:
            return spreadsheet.worksheet(nombre)
        except gspread.exceptions.WorksheetNotFound:
            continue
            
    # Si ninguna de las anteriores existe, regresa la primera pestaña disponible
    return spreadsheet.get_worksheet(0)

def guardar_registro_censal(sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente):
    """
    Guarda el registro censal en la pestaña dinámica correspondiente a la unidad y fecha.
    """
    client = obtener_cliente_gspread()
    
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    except Exception as e:
        raise Exception(f"No se pudo abrir el documento de Google Sheets (Verifica el ID o permisos): {e}")
    
    # Seleccionar la pestaña de forma dinámica según la jornada/fecha
    try:
        worksheet = _obtener_worksheet_dinamica(spreadsheet, sigla_url, tipo_jornada, val_fecha_app)
    except Exception as e:
        raise Exception(f"No se pudo acceder a la pestaña de registro: {e}")

    try:
        filas_existentes = worksheet.get_all_values()
    except Exception as e:
        raise Exception(f"Error al leer los valores de la hoja de Google Sheets: {e}")
      
    conteo_actual = len(filas_existentes)
    
    fecha_str = val_fecha_app.strftime("%Y%m%d")
    sufijo_unidad = f"-{sufijo_js}" if sufijo_js else ""
    folio_asignado = f"{fecha_str}-{tipo_jornada}-{sigla_url}{sufijo_unidad}-{conteo_actual:04d}"

    fila_a_insertar = [
        conteo_actual,
        folio_asignado,
        datos_paciente.get("paterno", "").upper(),
        datos_paciente.get("materno", "").upper(),
        datos_paciente.get("nombres", "").upper(),
        datos_paciente.get("correo_paciente", "")
    ]

    try:
        worksheet.append_row(fila_a_insertar)
    except Exception as e:
        raise Exception(f"Error al insertar el registro en Google Sheets: {e}")

    return folio_asignado, False, None

def verificar_curp_duplicada(curp_con_nacimiento, sigla, sufijo, tipo_jornada, fecha_aplicacion):
    """
    Verifica duplicados consultando la pestaña dinámica activa de la jornada.
    """
    client = obtener_cliente_gspread()
    
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    except Exception as e:
        raise Exception(f"No se pudo abrir el documento para verificar duplicados: {e}")
    
    try:
        worksheet = _obtener_worksheet_dinamica(spreadsheet, sig, tipo_jornada if 'tipo_jornada' in locals() else "I", fecha_aplicacion)
    except Exception as e:
        raise Exception(f"No se pudo acceder a la pestaña para validar duplicados: {e}")

    try:
        registros = worksheet.get_all_values()
    except Exception as e:
        raise Exception(f"Error al leer los registros existentes: {e}")
    
    for fila in registros[1:]: # Omitir cabecera
        if len(fila) > 1 and curp_con_nacimiento in str(fila):
            folio_previo = fila[1] if len(fila) > 1 else "S/N"
            return True, folio_previo

    return False, None
