import streamlit as str_lib
import pandas as pd
import gspread
import datetime
from google.oauth2 import service_account
from utils.sheets import obtener_cliente_gspread
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID

SHEET_ID_20_NOVIEMBRE = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"

def obtener_sheet_id_activo(hoja_activa, unidad_param=""):
    """Determina si la hoja pertenece al CMN 20 de Noviembre o al Sheet general."""
    if hoja_activa.upper().startswith("20N") or "20 DE NOVIEMBRE" in hoja_activa.upper() or "20_NOVIEMBRE" in unidad_param.upper() or "20 DE NOVIEMBRE" in unidad_param.upper():
        return SHEET_ID_20_NOVIEMBRE
    return GOOGLE_SHEET_ID

def get_creds_from_secrets():
    import json
    creds_dict = None
    if "GOOGLE_CREDENTIALS" in str_lib.secrets:
        raw = str_lib.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw) if isinstance(raw, str) else raw
    else:
        for k in str_lib.secrets:
            if k != "GOOGLE_SHEET_ID":
                creds_dict = dict(str_lib.secrets[k])
                break
    if not creds_dict:
        raise KeyError("No se encontraron credenciales de servicio válidas en st.secrets.")
    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    return service_account.Credentials.from_service_account_info(creds_dict, scopes=GOOGLE_SCOPES)

# --- SIN SPINNER MOLESTO ---
@str_lib.cache_data(ttl=300, show_spinner=False)
def load_sheet_minimal_cached(spreadsheet_id, worksheet_name):
    try:
        client_c = obtener_cliente_gspread()
        spreadsheet_c = client_c.open_by_key(spreadsheet_id)
        
        nombres_hojas = [w.title for w in spreadsheet_c.worksheets()]
        if worksheet_name not in nombres_hojas:
            return [], [], [], None, f"❌ La pestaña '{worksheet_name}' no existe en el libro consultado."

        worksheet = spreadsheet_c.worksheet(worksheet_name)
        all_rows = worksheet.get_all_values()
        
        if len(all_rows) < 14:
            return [], [], [], worksheet.id, None

        header1 = all_rows[11] if len(all_rows) > 11 else []
        header2 = all_rows[12] if len(all_rows) > 12 else []
        data_rows = all_rows[13:] if len(all_rows) > 13 else []

        return header1, header2, data_rows, worksheet.id, None

    except Exception as e:
        return [], [], [], None, str(e)

def construir_dataset_y_metricas(filas_tabla, header1, header2):
    encabezados_combinados = []
    conteo_nombres = {}
    max_cols = max(len(header1), len(header2), 50)

    for idx in range(max_cols):
        val1 = header1[idx].strip() if idx < len(header1) else ""
        val2 = header2[idx].strip() if idx < len(header2) else ""

        if val1 and val2 and val1 != val2:
            col_str = f"{val1} - {val2}"
        elif val2:
            col_str = val2
        elif val1:
            col_str = val1
        else:
            col_str = f"Col_{idx+1}"

        if col_str in conteo_nombres:
            conteo_nombres[col_str] += 1
            col_str = f"{col_str}_{conteo_nombres[col_str]}"
        else:
            conteo_nombres[col_str] = 0

        encabezados_combinados.append(col_str)

    filas_procesadas = []
    mapeo_indices_pares = []
    indices_filas_verdes = set()

    total_censo_registros = 0
    total_preregistros = 0
    registros_nuevos_hoy = 0
    total_aplicaciones = 0
    total_sin_aplicar = 0
    total_dosis_influenza = 0
    total_dosis_covid = 0
    total_simultaneas = 0
    fecha_hoy_str = datetime.datetime.now().strftime("%d/%m/%Y")

    for i in range(0, len(filas_tabla), 2):
        f1 = filas_tabla[i] if i < len(filas_tabla) else []
        f2 = filas_tabla[i + 1] if i + 1 < len(filas_tabla) else []
        
        f1_adj = f1 + [""] * max(0, len(encabezados_combinados) - len(f1))
        f2_adj = f2 + [""] * max(0, len(encabezados_combinados) - len(f2))

        if len(f1_adj) > 0 and str(f1_adj[0]).strip() != "":
            total_censo_registros += 1

            fecha_fila = f1_adj[48].strip() if len(f1_adj) > 48 else ""
            if fecha_fila == fecha_hoy_str:
                registros_nuevos_hoy += 1
            else:
                total_preregistros += 1

            tiene_aplicacion = any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(43, len(f1_adj))))
            if tiene_aplicacion:
                total_aplicaciones += 1
            else:
                total_sin_aplicar += 1

            tiene_influenza = any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(35, len(f1_adj))))
            tiene_covid = any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(37, min(40, len(f1_adj)))) if len(f1_adj) > 37 else False

            if tiene_influenza and not tiene_covid:
                total_dosis_influenza += 1
            elif tiene_covid and not tiene_influenza:
                total_dosis_covid += 1
            elif tiene_influenza and tiene_covid:
                total_simultaneas += 1

        if any(str(f1_adj[col_idx]).strip().upper() == "X" for col_idx in range(32, min(43, len(f1_adj)))):
            indices_filas_verdes.add(len(filas_procesadas))
            indices_filas_verdes.add(len(filas_procesadas) + 1)

        indices_deseados = list(range(0, 12)) + list(range(32, 43))

        f1_filtrado = [f1_adj[idx] if idx < len(f1_adj) else "" for idx in indices_deseados]
        f2_filtrado = [f2_adj[idx] if idx < len(f2_adj) else "" for idx in indices_deseados]

        fila_v1 = [False] + f1_filtrado
        fila_v2 = [None] + f2_filtrado

        filas_procesadas.append(fila_v1)
        filas_procesadas.append(fila_v2)
        mapeo_indices_pares.append(i)

    indices_deseados = list(range(0, 12)) + list(range(32, 43))
    encabezados_filtrados = [encabezados_combinados[idx] for idx in indices_deseados if idx < len(encabezados_combinados)]

    metricas = {
        "total_censo_registros": total_censo_registros,
        "total_preregistros": total_preregistros,
        "registros_nuevos_hoy": registros_nuevos_hoy,
        "total_aplicaciones": total_aplicaciones,
        "total_sin_aplicar": total_sin_aplicar,
        "total_dosis_influenza": total_dosis_influenza,
        "total_dosis_covid": total_dosis_covid,
        "total_simultaneas": total_simultaneas,
    }

    return encabezados_filtrados, filas_procesadas, mapeo_indices_pares, indices_filas_verdes, metricas

def eliminar_pacientes_seleccionados(sheet_id, hoja_activa, indices_marcados, mapeo_indices_pares, filas_tabla, key_estado_filas):
    pacientes_a_eliminar = {idx // 2 for idx in indices_marcados}
    pacientes_sorted = sorted(pacientes_a_eliminar, reverse=True)
    filas_actualizadas = list(filas_tabla)
    filas_gs_a_borrar = []
    
    for paciente_idx in pacientes_sorted:
        if paciente_idx < len(mapeo_indices_pares):
            idx_par_real = mapeo_indices_pares[paciente_idx]
            filas_gs_a_borrar.extend([idx_par_real + 14, idx_par_real + 15])
            del filas_actualizadas[idx_par_real:idx_par_real + 2]

    # Actualización inmediata en memoria local para respuesta visual instantánea
    str_lib.session_state[key_estado_filas] = filas_actualizadas

    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(sheet_id)
    ws = spreadsheet.worksheet(hoja_activa)

    filas_gs_a_borrar = sorted(set(filas_gs_a_borrar), reverse=True)
    for fila_gs in filas_gs_a_borrar:
        try:
            ws.delete_rows(fila_gs)
        except Exception:
            pass

    datos_actualizados = ws.get_all_values()
    if len(datos_actualizados) >= 14:
        filas_actuales = datos_actualizados[13:]
        contador = 1
        updates = []
        for i in range(0, len(filas_actuales), 2):
            row = filas_actuales[i]
            if len(row) > 0 and row[0].strip() != "":
                a1 = gspread.utils.rowcol_to_a1(i + 14, 1)
                updates.append({"range": a1, "values": [[str(contador)]]})
                contador += 1
        if updates:
            try:
                ws.batch_update(updates)
            except Exception:
                pass
