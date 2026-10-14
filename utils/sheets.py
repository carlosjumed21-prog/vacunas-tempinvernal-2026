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

def _obtener_worksheet_jornada(spreadsheet):
    """
    Detecta automáticamente la pestaña correcta basándose en los parámetros 
    de la URL de Streamlit (ej. unidad, jornada y fecha).
    """
    params = st.query_params
    sigla_url = params.get("unidad", "").upper()
    jornada_url = params.get("jornada", "I").upper()
    fecha_url_str = params.get("fecha", "")

    # Mapeo de la letra de la jornada a la nomenclatura de las pestañas
    mod_map = {"I": "INTRA", "E": "EXTRA", "M": "MOV"}
    tipo_str = mod_map.get(jornada_url, "INTRA")

    # Formatear la fecha de YYYY-MM-DD a DDMMYY (ej. 2026-10-14 -> 141026)
    fecha_sufijo = ""
    if fecha_url_str:
        try:
            parts = fecha_url_str.split("-")
            if len(parts) == 3:
                anio, mes, dia = parts
                fecha_sufijo = f"{dia}{mes}{anio[2:]}"
        except Exception:
            pass

    # Lista de posibles nombres exactos de pestañas a buscar en orden de prioridad
    candidatos = []
    if sigla_url and tipo_str and fecha_sufijo:
        candidatos.append(f"{sigla_url}_{tipo_str}_{fecha_sufijo}")
    
    # Intentar buscar entre las pestañas existentes del documento la que coincida
    try:
        hojas_existentes = [ws.title for ws in spreadsheet.worksheets()]
        
        # 1. Buscar coincidencia exacta con el nombre construido
        for candidato in candidatos:
            if candidato in hojas_existentes:
                return spreadsheet.worksheet(candidato)
                
        # 2. Buscar coincidencia parcial por Unidad y Fecha si se pasaron en URL
        if sigla_url and fecha_sufijo:
            for hoja in hojas_existentes:
                if sigla_url in hoja and fecha_sufijo in hoja:
                    return spreadsheet.worksheet(hoja)
                    
        # 3. Si se pasó una unidad pero no fecha exacta, buscar la más reciente de esa unidad
        if sigla_url:
            for hoja in hojas_existentes:
                if hoja.startswith(sigla_url):
                    return spreadsheet.worksheet(hoja)
    except Exception:
        pass

    # Fallback de respaldo a la primera pestaña si no encuentra ninguna coincidencia
    return spreadsheet.get_worksheet(0)

def guardar_registro_censal(sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente):
    """
    Guarda el registro censal de forma nativa en la pestaña correcta de la jornada.
    """
    client = obtener_cliente_gspread()
    
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    except Exception as e:
        raise Exception(f"No se pudo abrir el documento de Google Sheets (Verifica el ID o permisos): {e}")
    
    # Obtener la pestaña dinámica correcta según la URL actual
    try:
        worksheet = _obtener_worksheet_jornada(spreadsheet)
    except Exception as e:
        raise Exception(f"No se pudo acceder a la pestaña operativa de la jornada: {e}")

    try:
        filas_existentes = worksheet.get_all_values()
    except Exception as e:
        raise Exception(f"Error al leer los valores de la hoja (Posible bloqueo de API o respuesta vacía): {e}")
      
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
    Verifica si una CURP ya se encuentra registrada en la pestaña activa de la jornada.
    """
    client = obtener_cliente_gspread()
    
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    except Exception as e:
        raise Exception(f"No se pudo abrir el documento para verificar duplicados: {e}")
    
    try:
        worksheet = _obtener_worksheet_jornada(spreadsheet)
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
