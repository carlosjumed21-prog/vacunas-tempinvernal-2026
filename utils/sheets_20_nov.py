import datetime
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
from config import GOOGLE_SHEET_ID

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def obtener_cliente_gspread():
    """Conecta con Google Sheets usando los secretos configurados en Streamlit."""
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    else:
        raise Exception("No se encontraron las credenciales 'gcp_service_account' en los st.secrets.")

def guardar_registro_censal_20_nov(datos_paciente):
    """
    Función exclusiva para registrar los datos censales del CMN 20 de Noviembre
    en su respectiva pestaña de Google Sheets, asignando su folio correspondiente.
    """
    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    
    sigla_url = st.session_state.get("siglas_unidad", "20N")
    sufijo_js = st.query_params.get("js", "")
    nombre_hoja = f"{sigla_url}_{sufijo_js}" if sufijo_js else sigla_url
    
    try:
        ws = spreadsheet.worksheet(nombre_hoja)
    except Exception:
        # Si la pestaña no existe, se crea o se usa la principal por defecto
        ws = spreadsheet.sheet1

    valores = ws.get_all_values()
    
    # Determinar la fila de destino respetando la estructura de censo nominal
    fila_dest = 14
    if len(valores) >= 14:
        idx_t = 13
        while idx_t < len(valores):
            if idx_t >= len(valores) or not any(valores[idx_t]) or not valores[idx_t][1]:
                fila_dest = idx_t + 1
                break
            idx_t += 2
        else:
            fila_dest = len(valores) + 1
            if (fila_dest - 14) % 2 != 0:
                fila_dest += 1
                
    consecutivo = ((fila_dest - 14) // 2) + 1
    val_fecha_app = datos_paciente.get("val_fecha_app", datetime.date.today())
    f_str = val_fecha_app.strftime("%Y%m%d")
    m_str = "INT" if datos_paciente.get("modalidad", "INTRAMUROS") == "INTRAMUROS" else "EXT"
    s_3 = sigla_url[:3].upper().ljust(3, 'X')
    
    folio_asignado = f"{f_str}-{m_str}-{s_3}-{str(consecutivo).zfill(4)}"
    
    # Extraer comorbilidades y datos del diccionario
    com = datos_paciente.get("comorbilidades", {})
    
    # Aquí puedes estructurar la fila exactamente como lo requiere tu plantilla de Google Sheets
    fila_a_insertar = [
        str(consecutivo),
        folio_asignado,
        datos_paciente.get("paterno", "").upper(),
        datos_paciente.get("materno", "").upper(),
        datos_paciente.get("nombres", "").upper(),
        datos_paciente.get("curp_con_nacimiento", ""),
        datos_paciente.get("rfc", ""),
        str(datos_paciente.get("calc_anos", 0)),
        str(datos_paciente.get("calc_meses", 0)),
        datos_paciente.get("sexo", ""),
        datos_paciente.get("correo_paciente", ""),
        datos_paciente.get("vacuna_interes", ""),
        datos_paciente.get("grupo_sugerido", ""),
        val_fecha_app.strftime("%d/%m/%Y")
    ]
    
    # Insertar o actualizar la fila en la hoja de cálculo
    if fila_dest <= len(valores):
        ws.insert_row(fila_a_insertar, fila_dest)
    else:
        ws.append_row(fila_a_insertar)
        
    return folio_asignado
