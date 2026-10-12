import datetime
import streamlit as st
from utils.sheets import obtener_cliente_gspread

# ID de la hoja de cálculo exclusiva para el CMN 20 de Noviembre
SHEET_ID_20_NOV = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"

def guardar_registro_censal_20_nov(datos_paciente):
    """
    Función exclusiva para registrar los datos censales del CMN 20 de Noviembre
    en su propia hoja de Google Sheets, asignando su folio correspondiente.
    """
    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(SHEET_ID_20_NOV)
    
    sigla_url = st.session_state.get("siglas_unidad", "20N")
    sufijo_js = st.query_params.get("js", "")
    nombre_hoja = f"{sigla_url}_{sufijo_js}" if sufijo_js else sigla_url
    
    try:
        ws = spreadsheet.worksheet(nombre_hoja)
    except Exception:
        ws = spreadsheet.sheet1

    valores = ws.get_all_values()
    
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
    
    if fila_dest <= len(valores):
        ws.insert_row(fila_a_insertar, fila_dest)
    else:
        ws.append_row(fila_a_insertar)
        
    return folio_asignado
