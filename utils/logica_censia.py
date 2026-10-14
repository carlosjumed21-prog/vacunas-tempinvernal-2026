# utils/logica_censia.py
import datetime
import urllib.parse
import requests
import streamlit as st
from utils.sheets import obtener_token_acceso
from config import GOOGLE_SHEET_ID

# ID de la hoja de cálculo exclusiva para el CMN 20 de Noviembre
SHEET_ID_20_NOV = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"


def procesar_guardado_aplicacion(
    worksheet_activa,
    fila_idx,
    todos_los_datos,
    inf_1ra, inf_2da, inf_anual,
    cov_1ra, cov_2da, cov_anual,
    lote_inf_input, cad_inf_input,
    lote_cov_input, cad_cov_input,
    biologico_covid_elegido,
    habilitar_edicion,
    ed_paterno, ed_materno, ed_nombres,
    ed_d, ed_m, ed_y, ed_sexo, ed_curp,
    paterno_p, materno_p, nombres_p,
    fecha_aplicacion_hoja,
    sheet_id_objetivo=GOOGLE_SHEET_ID
):
    """
    Ejecuta las validaciones, actualiza los datos de manera dual (CENSO NOMINAL y CENSO general)
    respetando el mapeo exacto de columnas de cada hoja mediante cliente gspread nativo.
    """
    influenza_seleccionada = inf_1ra or inf_2da or inf_anual
    covid_seleccionada = cov_1ra or cov_2da or cov_anual

    error_validacion = False

    if influenza_seleccionada:
        if not lote_inf_input.strip():
            st.error("⚠️ **Error:** Seleccionó al menos una dosis de **Influenza**, pero falta ingresar el número de lote.")
            error_validacion = True
        if not cad_inf_input.strip():
            st.error("⚠️ **Error:** Seleccionó al menos una dosis de **Influenza**, pero falta indicar la fecha de caducidad.")
            error_validacion = True

    if covid_seleccionada:
        if not lote_cov_input.strip():
            st.error(f"⚠️ **Error:** Seleccionó al menos una dosis de **{biologico_covid_elegido}**, pero falta ingresar el número de lote.")
            error_validacion = True
        if not cad_cov_input.strip():
            st.error(f"⚠️ **Error:** Seleccionó al menos una dosis de **{biologico_covid_elegido}**, pero falta indicar la fecha de caducidad.")
            error_validacion = True

    if not influenza_seleccionada and not covid_seleccionada:
        st.warning("⚠️ Debe seleccionar al menos una dosis a aplicar antes de guardar.")
        error_validacion = True

    if error_validacion:
        return False

    try:
        if lote_inf_input:
            st.session_state.lote_influenza_memoria = lote_inf_input.upper()
        if lote_cov_input:
            st.session_state.lote_covid_memoria = lote_cov_input.upper()

        f_actual = fila_idx
        f_siguiente = fila_idx + 1
        fila_curp_idx = fila_idx  

        dosis_aplicadas_lista = []
        updates_data = []

        cad_i_str = cad_inf_input.strip()
        cad_c_str = cad_cov_input.strip()
        
        nombre_hoja_escapado = f"'{worksheet_activa.title}'"

        if habilitar_edicion:
            updates_data.extend([
                {"range": f"{nombre_hoja_escapado}!C{f_actual}:C{f_siguiente}", "values": [[ed_paterno.upper()], [ed_paterno.upper()]]},
                {"range": f"{nombre_hoja_escapado}!D{f_actual}:D{f_siguiente}", "values": [[ed_materno.upper()], [ed_materno.upper()]]},
                {"range": f"{nombre_hoja_escapado}!E{f_actual}:E{f_siguiente}", "values": [[ed_nombres.upper()], [ed_nombres.upper()]]},
                {"range": f"{nombre_hoja_escapado}!F{f_actual}:F{f_siguiente}", "values": [[ed_d.strip()], [ed_d.strip()]]},
                {"range": f"{nombre_hoja_escapado}!G{f_actual}:G{f_siguiente}", "values": [[ed_m.strip()], [ed_m.strip()]]},
                {"range": f"{nombre_hoja_escapado}!H{f_actual}:H{f_siguiente}", "values": [[ed_y.strip()], [ed_y.strip()]]},
                {"range": f"{nombre_hoja_escapado}!K{f_actual}:K{f_siguiente}", "values": [[ed_sexo.upper()], [ed_sexo.upper()]]},
                {"range": f"{nombre_hoja_escapado}!C{fila_curp_idx}", "values": [[ed_curp.upper()]]}
            ])
            nombre_completo = f"{ed_paterno.upper()} {ed_materno.upper()}, {ed_nombres.upper()}"
        else:
            nombre_completo = f"{paterno_p} {materno_p}, {nombres_p}"

        # --- 1. ACTUALIZACIÓN EN LA HOJA ACTIVA (CENSO NOMINAL DE JORNADA) ---
        if inf_1ra:
            updates_data.append({"range": f"{nombre_hoja_escapado}!AG{f_actual}:AG{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append("Influenza (1ra Dosis)")
        if inf_2da:
            updates_data.append({"range": f"{nombre_hoja_escapado}!AH{f_actual}:AH{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append("Influenza (2da Dosis)")
        if inf_anual:
            updates_data.append({"range": f"{nombre_hoja_escapado}!AI{f_actual}:AI{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append("Influenza (Dosis Anual)")

        if lote_inf_input:
            lote_i = lote_inf_input.upper()
            updates_data.append({"range": f"{nombre_hoja_escapado}!AJ{f_actual}:AJ{f_siguiente}", "values": [[lote_i], [lote_i]]})
        if cad_inf_input:
            updates_data.append({"range": f"{nombre_hoja_escapado}!AK{f_actual}:AK{f_siguiente}", "values": [[cad_i_str], [cad_i_str]]})

        if cov_1ra:
            updates_data.append({"range": f"{nombre_hoja_escapado}!AL{f_actual}:AL{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append(f"{biologico_covid_elegido} (1ra Dosis)")
        if cov_2da:
            updates_data.append({"range": f"{nombre_hoja_escapado}!AM{f_actual}:AM{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append(f"{biologico_covid_elegido} (2da Dosis)")
        if cov_anual:
            updates_data.append({"range": f"{nombre_hoja_escapado}!AN{f_actual}:AN{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append(f"{biologico_covid_elegido} (Dosis Anual)")

        if lote_cov_input:
            lote_c = lote_cov_input.upper()
            updates_data.append({"range": f"{nombre_hoja_escapado}!AO{f_actual}:AO{f_siguiente}", "values": [[lote_c], [lote_c]]})
        if cad_cov_input:
            updates_data.append({"range": f"{nombre_hoja_escapado}!AP{f_actual}:AP{f_siguiente}", "values": [[cad_c_str], [cad_c_str]]})

        # --- 2. MIGRACIÓN DUAL AUTOMÁTICA HACIA LA HOJA "CENSO" GENERAL (MAPEO Y-AH) ---
        if sheet_id_objetivo == SHEET_ID_20_NOV:
            try:
                import json
                import gspread
                from config import GOOGLE_SCOPES

                # Autenticación limpia mediante gspread service_account desde los secrets
                if "GOOGLE_CREDENTIALS" in st.secrets:
                    raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
                    creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
                elif "gcp_service_account" in st.secrets:
                    creds_dict = dict(st.secrets["gcp_service_account"])
                else:
                    primera_llave = list(st.secrets.keys())[0]
                    creds_dict = dict(st.secrets[primera_llave])

                if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
                    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

                client_gspread = gspread.service_account_from_dict(creds_dict, scopes=GOOGLE_SCOPES)
                spreadsheet_20n = client_gspread.open_by_key(SHEET_ID_20_NOV)
                hoja_censia_general = spreadsheet_20n.worksheet("CENSO")
                nombre_censo_escapado = "'CENSO'"
                
                # Obtener el folio del paciente actual (Columna B / índice 1)
                folio_paciente_actual = todos_los_datos[fila_idx - 1][1].strip() if len(todos_los_datos[fila_idx - 1]) > 1 else ""
                
                if folio_paciente_actual:
                    valores_censo_general = hoja_censia_general.get_all_values()
                    fila_en_censo = None
                    
                    for idx_cg, row_cg in enumerate(valores_censo_general[13:], start=14):
                        if len(row_cg) > 1 and row_cg[1].strip() == folio_paciente_actual:
                            fila_en_censo = idx_cg
                            break
                    
                    if fila_en_censo:
                        fc_actual = fila_en_censo
                        fc_siguiente = fila_en_censo + 1

                        # Inyección respetando el mapeo exacto de la hoja CENSO (Y hasta AH)
                        if inf_1ra:
                            updates_data.append({"range": f"{nombre_censo_escapado}!Y{fc_actual}:Y{fc_siguiente}", "values": [["X"], ["X"]]})
                        if inf_2da:
                            updates_data.append({"range": f"{nombre_censo_escapado}!Z{fc_actual}:Z{fc_siguiente}", "values": [["X"], ["X"]]})
                        if inf_anual:
                            updates_data.append({"range": f"{nombre_censo_escapado}!AA{fc_actual}:AA{fc_siguiente}", "values": [["X"], ["X"]]})
                        if lote_inf_input:
                            updates_data.append({"range": f"{nombre_censo_escapado}!AB{fc_actual}:AB{fc_siguiente}", "values": [[lote_i], [lote_i]]})
                        if cad_inf_input:
                            updates_data.append({"range": f"{nombre_censo_escapado}!AC{fc_actual}:AC{fc_siguiente}", "values": [[cad_i_str], [cad_i_str]]})

                        if cov_1ra:
                            updates_data.append({"range": f"{nombre_censo_escapado}!AD{fc_actual}:AD{fc_siguiente}", "values": [["X"], ["X"]]})
                        if cov_2da:
                            updates_data.append({"range": f"{nombre_censo_escapado}!AE{fc_actual}:AE{fc_siguiente}", "values": [["X"], ["X"]]})
                        if cov_anual:
                            updates_data.append({"range": f"{nombre_censo_escapado}!AF{fc_actual}:AF{fc_siguiente}", "values": [["X"], ["X"]]})
                        if lote_cov_input:
                            updates_data.append({"range": f"{nombre_censo_escapado}!AG{fc_actual}:AG{fc_siguiente}", "values": [[lote_c], [lote_c]]})
                        if cad_cov_input:
                            updates_data.append({"range": f"{nombre_censo_escapado}!AH{fc_actual}:AH{fc_siguiente}", "values": [[cad_c_str], [cad_c_str]]})
            except Exception as e_migracion:
                st.error(f"⚠️ Error al migrar a la hoja CENSO general: {e_migracion}")
                return False

        token = obtener_token_acceso()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Petición batchUpdate para actualizar ambas hojas simultáneamente
        url_values = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id_objetivo}/values:batchUpdate"
        body_values = {
            "valueInputOption": "USER_ENTERED",
            "data": updates_data
        }
        resp_val = requests.post(url_values, headers=headers, json=body_values)
        if resp_val.status_code != 200:
            raise Exception(f"Error en Google Sheets API (Values): {resp_val.text}")

        # Formato visual verde en la hoja activa
        url_spreadsheet = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id_objetivo}:batchUpdate"
        body_format = {
            "requests": [
                {
                    "updateCells": {
                        "range": {
                            "sheetId": worksheet_activa.id,
                            "startRowIndex": f_actual - 1,
                            "endRowIndex": f_siguiente,
                            "startColumnIndex": 0,
                            "endColumnIndex": 50
                        },
                        "rows": [
                            {
                                "values": [
                                    {
                                        "userEnteredFormat": {
                                            "backgroundColor": {
                                                "red": 0.831,
                                                "green": 0.929,
                                                "blue": 0.855
                                            }
                                        }
                                    } for _ in range(50)
                                ]
                            } for _ in range(2)
                        ],
                        "fields": "userEnteredFormat.backgroundColor"
                    }
                }
            ]
        }
        requests.post(url_spreadsheet, headers=headers, json=body_format)

        st.cache_data.clear()

        lote_final_partes = []
        if lote_inf_input:
            lote_final_partes.append(f"Inf: {lote_inf_input.upper()} (Cad: {cad_i_str})")
        if lote_cov_input:
            lote_final_partes.append(f"Cov: {lote_cov_input.upper()} (Cad: {cad_c_str})")
        lote_final_str = " / ".join(lote_final_partes) if lote_final_partes else "N/A"

        dosis_str = ", ".join(dosis_aplicadas_lista) if dosis_aplicadas_lista else "Ninguna seleccionada"
        folio_p = todos_los_datos[fila_idx - 1][1] if len(todos_los_datos[fila_idx - 1]) > 1 else ""

        st.session_state.reiniciar_busqueda = True
        st.session_state.ultimo_comprobante_vacunacion = {
            "nombre": nombre_completo,
            "folio": folio_p,
            "dosis_str": dosis_str,
            "lotes_str": lote_final_str,
            "fecha_aplicacion": fecha_aplicacion_hoja
        }
        return True

    except Exception as e:
        st.error(f"Error al actualizar la base de datos en Google Sheets: {e}")
        return False
