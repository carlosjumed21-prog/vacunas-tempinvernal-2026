import datetime
import urllib.parse
import streamlit as st
from utils.sheets_esquemas import obtener_recomendaciones_paciente


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
    fecha_aplicacion_hoja
):
    """
    Ejecuta las validaciones, actualiza los datos en Google Sheets, da formato a las celdas
    y prepara el diccionario para el comprobante oficial.
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
            st.error(f"⚠️ **Error:** Seleccionó al menos una dosis de **COVID-19 ({biologico_covid_elegido})**, pero falta ingresar el número de lote.")
            error_validacion = True
        if not cad_cov_input.strip():
            st.error(f"⚠️ **Error:** Seleccionó al menos una dosis de **COVID-19 ({biologico_covid_elegido})**, pero falta indicar la fecha de caducidad.")
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
        fila_curp_idx = fila_idx  # La CURP se almacena en la fila principal complementaria

        dosis_aplicadas_lista = []
        datos_a_actualizar = []

        cad_i_str = cad_inf_input.strip()
        cad_c_str = cad_cov_input.strip()

        if habilitar_edicion:
            datos_a_actualizar.extend([
                {"range": f"C{f_actual}:C{f_siguiente}", "values": [[ed_paterno.upper()], [ed_paterno.upper()]]},
                {"range": f"D{f_actual}:D{f_siguiente}", "values": [[ed_materno.upper()], [ed_materno.upper()]]},
                {"range": f"E{f_actual}:E{f_siguiente}", "values": [[ed_nombres.upper()], [ed_nombres.upper()]]},
                {"range": f"F{f_actual}:F{f_siguiente}", "values": [[ed_d.strip()], [ed_d.strip()]]},
                {"range": f"G{f_actual}:G{f_siguiente}", "values": [[ed_m.strip()], [ed_m.strip()]]},
                {"range": f"H{f_actual}:H{f_siguiente}", "values": [[ed_y.strip()], [ed_y.strip()]]},
                {"range": f"K{f_actual}:K{f_siguiente}", "values": [[ed_sexo.upper()], [ed_sexo.upper()]]},
                {"range": f"C{fila_curp_idx}", "values": [[ed_curp.upper()]]}
            ])
            nombre_completo = f"{ed_paterno.upper()} {ed_materno.upper()}, {ed_nombres.upper()}"
        else:
            nombre_completo = f"{paterno_p} {materno_p}, {nombres_p}"

        if inf_1ra:
            datos_a_actualizar.append({"range": f"AG{f_actual}:AG{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append("Influenza (1ra Dosis)")
        if inf_2da:
            datos_a_actualizar.append({"range": f"AH{f_actual}:AH{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append("Influenza (2da Dosis)")
        if inf_anual:
            datos_a_actualizar.append({"range": f"AI{f_actual}:AI{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append("Influenza (Dosis Anual)")

        if lote_inf_input:
            lote_i = lote_inf_input.upper()
            datos_a_actualizar.append({"range": f"AJ{f_actual}:AJ{f_siguiente}", "values": [[lote_i], [lote_i]]})
        if cad_inf_input:
            datos_a_actualizar.append({"range": f"AK{f_actual}:AK{f_siguiente}", "values": [[cad_i_str], [cad_i_str]]})

        if cov_1ra:
            datos_a_actualizar.append({"range": f"AL{f_actual}:AL{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append(f"COVID-19 {biologico_covid_elegido} (1ra Dosis)")
        if cov_2da:
            datos_a_actualizar.append({"range": f"AM{f_actual}:AM{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append(f"COVID-19 {biologico_covid_elegido} (2da Dosis)")
        if cov_anual:
            datos_a_actualizar.append({"range": f"AN{f_actual}:AN{f_siguiente}", "values": [["X"], ["X"]]})
            dosis_aplicadas_lista.append(f"COVID-19 {biologico_covid_elegido} (Dosis Anual)")

        if lote_cov_input:
            lote_c = lote_cov_input.upper()
            datos_a_actualizar.append({"range": f"AO{f_actual}:AO{f_siguiente}", "values": [[lote_c], [lote_c]]})
        if cad_cov_input:
            datos_a_actualizar.append({"range": f"AP{f_actual}:AP{f_siguiente}", "values": [[cad_c_str], [cad_c_str]]})

        peticion_formato_celdas = {
            "repeatCell": {
                "range": {
                    "sheetId": worksheet_activa.id,
                    "startRowIndex": f_actual - 1, 
                    "endRowIndex": f_siguiente,        
                    "startColumnIndex": 0,            
                    "endColumnIndex": 43              
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 0.831,
                            "green": 0.929,
                            "blue": 0.855
                        }
                    }
                },
                "fields": "userEnteredFormat.backgroundColor"
            }
        }

        worksheet_activa.batch_update(datos_a_actualizar)
        worksheet_activa.spreadsheet.batch_update({"requests": [peticion_formato_celdas]})

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
