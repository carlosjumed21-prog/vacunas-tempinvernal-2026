import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID

def obtener_cliente_gspread():
    """
    Autentica y retorna el cliente de gspread manejando correctamente 
    los secretos y los saltos de línea de la clave privada.
    """
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        if "GOOGLE_CREDENTIALS" in st.secrets:
            raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
            creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else dict(raw_creds)
        elif "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            primera_llave = list(st.secrets.keys())[0]
            creds_dict = dict(st.secrets[primera_llave])

        # Corrección crucial para los saltos de línea de la private key
        if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\\\n", "\n").replace("\\n", "\n")

        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    except Exception:
        # Fallback a archivo local si no está en st.secrets
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        
    client = gspread.authorize(creds)
    return client

def obtener_token_acceso():
    client = obtener_cliente_gspread()
    return client.auth

def _obtener_worksheet_jornada(spreadsheet):
    """
    Detecta automáticamente la pestaña correcta basándose en los parámetros 
    de la URL de Streamlit (ej. unidad=TLA, jornada=E, fecha=2026-10-14).
    """
    params = st.query_params
    sigla_url = params.get("unidad", "").upper()
    jornada_url = params.get("jornada", "I").upper()
    fecha_url_str = params.get("fecha", "")

    mod_map = {"I": "INTRA", "E": "EXTRA", "M": "MOV"}
    tipo_str = mod_map.get(jornada_url, "INTRA")

    fecha_sufijo = ""
    if fecha_url_str:
        try:
            parts = fecha_url_str.split("-")
            if len(parts) == 3:
                anio, mes, dia = parts
                fecha_sufijo = f"{dia}{mes}{anio[2:]}"
        except Exception:
            pass

    try:
        hojas_existentes = [ws.title for ws in spreadsheet.worksheets()]
        
        # 1. Buscar coincidencia exacta (Ej: TLA_EXTRA_141026)
        candidato_exacto = f"{sigla_url}_{tipo_str}_{fecha_sufijo}"
        if candidato_exacto in hojas_existentes:
            return spreadsheet.worksheet(candidato_exacto)
                
        # 2. Buscar coincidencia parcial por Unidad y Fecha
        if sigla_url and fecha_sufijo:
            for hoja in hojas_existentes:
                if sigla_url in hoja and fecha_sufijo in hoja:
                    return spreadsheet.worksheet(hoja)
                    
        # 3. Buscar por Unidad si existe
        if sigla_url:
            for hoja in hojas_existentes:
                if hoja.startswith(sigla_url):
                    return spreadsheet.worksheet(hoja)
    except Exception:
        pass

    # Respaldo a la primera pestaña si no encuentra ninguna
    return spreadsheet.get_worksheet(0)

def guardar_registro_censal(sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente):
    client = obtener_cliente_gspread()
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    except Exception as e:
        raise Exception(f"No se pudo abrir el documento de Google Sheets: {e}")
    
    try:
        worksheet = _obtener_worksheet_jornada(spreadsheet)
    except Exception as e:
        raise Exception(f"No se pudo acceder a la pestaña operativa: {e}")

    try:
        filas_existentes = worksheet.get_all_values()
    except Exception as e:
        raise Exception(f"Error al leer los valores de la hoja (Respuesta vacía o error de API): {e}")
      
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
    
    for fila in registros[1:]: 
        if len(fila) > 1 and curp_con_nacimiento in str(fila):
            folio_previo = fila[1] if len(fila) > 1 else "S/N"
            return True, folio_previo

    return False, None
