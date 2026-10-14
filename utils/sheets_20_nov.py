import datetime
import requests
import streamlit as st
from utils.sheets import obtener_token_acceso, obtener_cliente_gspread

def guardar_registro_censal_20_nov(datos_paciente):
    """
    Guarda el registro censal específico del CMN '20 de Noviembre'
    en la hoja nominal de la jornada y realiza la migración conjunta y simultánea
    hacia la hoja maestra 'CENSO' general de manera robusta.
    """
    try:
        client = obtener_cliente_gspread()
        sheet_id_20n = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"
        spreadsheet = client.open_by_key(sheet_id_20n)

        val_fecha_app = datos_paciente.get("val_fecha_app", datetime.date.today())
        tipo_jornada = datos_paciente.get("tipo_jornada", "I")
        fecha_str_hoja = val_fecha_app.strftime("%d%m%y")
        tipo_texto_jornada = "INTRA" if tipo_jornada == "I" else "EXTRA"
        
        siglas_unidad = st.session_state.get("siglas_unidad", "20N")
        sufijo_js = st.session_state.get("sufijo_js", "")
        nombre_hoja_nominal = f"{siglas_unidad}_{tipo_texto_jornada}{sufijo_js}_{fecha_str_hoja}_NOMINAL"
        nombre_hoja_nominal_esc = f"'{nombre_hoja_nominal}'"
        nombre_censo_esc = "'CENSO'"

        # --- 1. PREPARAR HOJA NOMINAL DINÁMICA DE LA JORNADA ---
        try:
            ws_nominal = spreadsheet.worksheet(nombre_hoja_nominal)
        except:
            try:
                plantilla_1 = spreadsheet.worksheet("CENSO NOMINAL")
            except:
                plantilla_1 = spreadsheet.worksheet("CENSO")
            ws_nominal = spreadsheet.duplicate_sheet(
                plantilla_1.id, 
                insert_sheet_index=len(spreadsheet.worksheets()), 
                new_sheet_name=nombre_hoja_nominal
            )

        col_b_nom = ws_nominal.col_values(2)
        fila_nom = 14
        idx_n = 13
        while idx_n < len(col_b_nom):
            val_a = str(col_b_nom[idx_n]).strip()
            if val_a == "" or "POR ASIGNAR" in val_a.upper():
                fila_nom = idx_n + 1
                break
            idx_n += 2
        else:
            fila_nom = max(14, len(col_b_nom) + 1)
            if (fila_nom - 14) % 2 != 0:
                fila_nom += 1

        num_nom = ((fila_nom - 14) // 2) + 1
        aammmdd = val_fecha_app.strftime("%y%m%d")
        sigla_url = siglas_unidad
        folio_asignado = f"{aammmdd}-{tipo_jornada}{sigla_url}-{str(num_nom).zfill(3)}"

        # --- 2. OBTENER FILA EXACTA EN HOJA MAESTRA "CENSO" ---
        try:
            ws_censo_general = spreadsheet.worksheet("CENSO")
        except:
            ws_censo_general = ws_nominal

        # Determinamos la fila basándonos en el total de filas de la hoja CENSO (mínimo fila 14)
        valores_censo_total = ws_censo_general.get_all_values()
        fila_censo = max(14, len(valores_censo_total) + 1)
        consecutivo_censo = fila_censo - 13

        # Datos del paciente
        comorb = datos_paciente.get("comorbilidades", {})
        ant_inf_val = datos_paciente.get("antecedente_influenza", "")
        ant_cov_val = datos_paciente.get("antecedente_covid", "")
        vacuna_int = datos_paciente.get("vacuna_interes", "").upper()
        
        ps_val = "SÍ" if datos_paciente.get("personal_salud") == "SÍ" else "NO"
        emb_val = "SÍ" if datos_paciente.get("embarazo") == "SÍ" else "NO"

        # --- 3. CONSTRUCCIÓN DE LA LISTA DE ACTUALIZACIONES CONJUNTAS ---
        fecha_app_fmt = val_fecha_app.strftime("%d/%m/%Y")
        f_actual = fila_nom
        f_siguiente = fila_nom + 1

        updates_conjuntos = [
            # Encabezados generales en hoja nominal
            {"range": f"{nombre_hoja_nominal_esc}!D7", "values": [["CDMX"]]},
            {"range": f"{nombre_hoja_nominal_esc}!M7", "values": [["ISSSTE"]]},
            {"range": f"{nombre_hoja_nominal_esc}!T7", "values": [["Delegación Sur"]]},
            {"range": f"{nombre_hoja_nominal_esc}!AB7", "values": [["CDMX"]]},
            {"range": f"{nombre_hoja_nominal_esc}!D8", "values": [["CDMX"]]},
            {"range": f"{nombre_hoja_nominal_esc}!D9", "values": [[st.session_state.get("nombre_unidad", "CMN 20 DE NOVIEMBRE")]]},
            {"range": f"{nombre_hoja_nominal_esc}!AB9", "values": [[fecha_app_fmt]]},
            
            # Datos principales en Hoja Nominal
            {"range": f"{nombre_hoja_nominal_esc}!B{f_actual}:B{f_siguiente}", "values": [[folio_asignado], [folio_asignado]]},
            {"range": f"{nombre_hoja_nominal_esc}!C{f_actual}", "values": [[datos_paciente['paterno'].upper()]]},
            {"range": f"{nombre_hoja_nominal_esc}!D{f_actual}", "values": [[datos_paciente['materno'].upper() if datos_paciente.get('materno') else ""]]},
            {"range": f"{nombre_hoja_nominal_esc}!E{f_actual}", "values": [[datos_paciente['nombres'].upper()]]},
            {"range": f"{nombre_hoja_nominal_esc}!F{f_actual}:F{f_siguiente}", "values": [[datos_paciente['fn_dia']], [datos_paciente['fn_dia']]]},
            {"range": f"{nombre_hoja_nominal_esc}!G{f_actual}:G{f_siguiente}", "values": [[datos_paciente['fn_mes']], [datos_paciente['fn_mes']]]},
            {"range": f"{nombre_hoja_nominal_esc}!H{f_actual}:H{f_siguiente}", "values": [[datos_paciente['fn_ano']], [datos_paciente['fn_ano']]]},
            {"range": f"{nombre_hoja_nominal_esc}!I{f_actual}:I{f_siguiente}", "values": [[str(datos_paciente['anos'])], [str(datos_paciente['anos'])]]},
            {"range": f"{nombre_hoja_nominal_esc}!J{f_actual}:J{f_siguiente}", "values": [[str(datos_paciente['meses'])], [str(datos_paciente['meses'])]]},
            {"range": f"{nombre_hoja_nominal_esc}!K{f_actual}:K{f_siguiente}", "values": [["H" if datos_paciente['sexo']=="HOMBRE" else "M"], ["H" if datos_paciente['sexo']=="HOMBRE" else "M"]]},
            {"range": f"{nombre_hoja_nominal_esc}!L{f_actual}:L{f_siguiente}", "values": [[fecha_app_fmt], [fecha_app_fmt]]},
            {"range": f"{nombre_hoja_nominal_esc}!M{f_actual}:M{f_siguiente}", "values": [[datos_paciente.get('calle','').upper()], [datos_paciente.get('calle','').upper()]]},
            {"range": f"{nombre_hoja_nominal_esc}!N{f_actual}:N{f_siguiente}", "values": [[datos_paciente.get('numero','').upper()], [datos_paciente.get('numero','').upper()]]},
            {"range": f"{nombre_hoja_nominal_esc}!O{f_actual}:O{f_siguiente}", "values": [[datos_paciente.get('colonia','').upper()], [datos_paciente.get('colonia','').upper()]]},
            {"range": f"{nombre_hoja_nominal_esc}!C{f_actual+1}", "values": [[datos_paciente.get('curp_con_nacimiento','')]]},
            
            {"range": f"{nombre_hoja_nominal_esc}!AQ{f_actual}:AQ{f_siguiente}", "values": [[datos_paciente.get('cuenta_derechohabiencia', 'SÍ')], [datos_paciente.get('cuenta_derechohabiencia', 'SÍ')]]},
            {"range": f"{nombre_hoja_nominal_esc}!AR{f_actual}:AR{f_siguiente}", "values": [[ant_inf_val], [ant_inf_val]]},
            {"range": f"{nombre_hoja_nominal_esc}!AS{f_actual}:AS{f_siguiente}", "values": [[ant_cov_val], [ant_cov_val]]},
            {"range": f"{nombre_hoja_nominal_esc}!AW{f_actual}:AW{f_siguiente}", "values": [[datetime.date.today().strftime("%d/%m/%Y")], [datetime.date.today().strftime("%d/%m/%Y")]]},
            {"range": f"{nombre_hoja_nominal_esc}!AX{f_actual}:AX{f_siguiente}", "values": [[datos_paciente.get('correo_paciente', '')], [datos_paciente.get('correo_paciente', '')]]},

            # --- MIGRACIÓN CONJUNTA A LA HOJA MAESTRA "CENSO" (A hasta X) ---
            {"range": f"{nombre_censo_esc}!A{fila_censo}", "values": [[consecutivo_censo]]},
            {"range": f"{nombre_censo_esc}!B{fila_censo}", "values": [[folio_asignado]]},
            {"range": f"{nombre_censo_esc}!C{fila_censo}", "values": [[datos_paciente.get("rfc", "")]]},
            {"range": f"{nombre_censo_esc}!D{fila_censo}", "values": [[datos_paciente.get("cuenta_derechohabiencia", "SÍ")]]},
            {"range": f"{nombre_censo_esc}!E{fila_censo}", "values": [[datos_paciente.get("tipo_dh", "TRABAJADOR ACTIVO")]]},
            {"range": f"{nombre_censo_esc}!F{fila_censo}", "values": [[datos_paciente.get("trabaja_cmn", "SÍ")]]},
            {"range": f"{nombre_censo_esc}!G{fila_censo}", "values": [[datos_paciente.get("num_trabajador", "")]]},
            {"range": f"{nombre_censo_esc}!H{fila_censo}", "values": [[ps_val]]},
            {"range": f"{nombre_censo_esc}!I{fila_censo}", "values": [[datos_paciente.get("categoria", "")]]},
            {"range": f"{nombre_censo_esc}!J{fila_censo}", "values": [[datos_paciente.get("servicio", "")]]},
            {"range": f"{nombre_censo_esc}!K{fila_censo}", "values": [[datos_paciente.get("coordinacion", "")]]},
            {"range": f"{nombre_censo_esc}!L{fila_censo}", "values": [[datos_paciente.get("turno", "")]]},
            {"range": f"{nombre_censo_esc}!M{fila_censo}", "values": [[datos_paciente["nombres"].upper()]]},
            {"range": f"{nombre_censo_esc}!N{fila_censo}", "values": [[datos_paciente["paterno"].upper()]]},
            {"range": f"{nombre_censo_esc}!O{fila_censo}", "values": [[datos_paciente["materno"].upper() if datos_paciente.get("materno") else ""]]},
            {"range": f"{nombre_censo_esc}!P{fila_censo}", "values": [[datos_paciente.get("edo_nac", "CDMX")]]},
            {"range": f"{nombre_censo_esc}!Q{fila_censo}", "values": [[datos_paciente.get("muni_nac", "")]]},
            {"range": f"{nombre_censo_esc}!R{fila_censo}", "values": [[datos_paciente["fn_dia"]]]},
            {"range": f"{nombre_censo_esc}!S{fila_censo}", "values": [[datos_paciente["fn_mes"]]]},
            {"range": f"{nombre_censo_esc}!T{fila_censo}", "values": [[datos_paciente["fn_ano"]]]},
            {"range": f"{nombre_censo_esc}!U{fila_censo}", "values": [[str(datos_paciente["anos"])]]},
            {"range": f"{nombre_censo_esc}!V{fila_censo}", "values": [[str(datos_paciente["meses"])]]},
            {"range": f"{nombre_censo_esc}!W{fila_censo}", "values": [[datos_paciente["sexo"]]]},
            {"range": f"{nombre_censo_esc}!X{fila_censo}", "values": [[emb_val]]},
        ]

        # Vacunas de interés en hoja nominal y censo general
        if vacuna_int in ["INFLUENZA", "AMBAS"]:
            updates_conjuntos.append({"range": f"{nombre_hoja_nominal_esc}!AT{f_actual}:AT{f_siguiente}", "values": [["X"], ["X"]]})
            updates_conjuntos.append({"range": f"{nombre_censo_esc}!Y{fila_censo}", "values": [["X"]]})
        if vacuna_int in ["COVID-19", "AMBAS"]:
            updates_conjuntos.append({"range": f"{nombre_hoja_nominal_esc}!AU{f_actual}:AU{f_siguiente}", "values": [["X"], ["X"]]})
            updates_conjuntos.append({"range": f"{nombre_censo_esc}!AD{fila_censo}", "values": [["X"]]})
        if vacuna_int == "AMBAS":
            updates_conjuntos.append({"range": f"{nombre_hoja_nominal_esc}!AV{f_actual}:AV{f_siguiente}", "values": [["X"], ["X"]]})

        # Comorbilidades
        if int(datos_paciente['anos']) < 5:
            updates_conjuntos.append({"range": f"{nombre_hoja_nominal_esc}!P{f_actual}:P{f_siguiente}", "values": [["X"], ["X"]]})
        elif int(datos_paciente['anos']) >= 60:
            updates_conjuntos.append({"range": f"{nombre_hoja_nominal_esc}!Q{f_actual}:Q{f_siguiente}", "values": [["X"], ["X"]]})

        if datos_paciente.get('embarazo') == "SÍ":
            updates_conjuntos.append({"range": f"{nombre_hoja_nominal_esc}!R{f_actual}:R{f_siguiente}", "values": [["X"], ["X"]]})
        if datos_paciente.get('personal_salud') == "SÍ":
            updates_conjuntos.append({"range": f"{nombre_hoja_nominal_esc}!S{f_actual}:S{f_siguiente}", "values": [["X"], ["X"]]})

        map_comorb_h1 = {
            "vih": "T", "diabetes": "U", "obesidad": "V", "cardiopatias": "W",
            "enfermedad_pulmonar": "X", "cancer": "Y", "cardiacas_congenitas": "Z",
            "insuficiencia_renal": "AA", "inmunosupresion": "AB", "discapacidades": "AC",
            "fibrosis_quistica": "AD", "hipertension": "AE"
        }
        for k_c, col_c in map_comorb_h1.items():
            if comorb.get(k_c, False):
                updates_conjuntos.append({"range": f"{nombre_hoja_nominal_esc}!{col_c}{f_actual}:{col_c}{f_siguiente}", "values": [["X"], ["X"]]})

        # --- 4. EJECUTAR LA PETICIÓN REST API v4 ---
        token = obtener_token_acceso()
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id_20n}/values:batchUpdate"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": updates_conjuntos
        }
        
        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise Exception(f"Error en Google Sheets API: {resp.text}")

        return folio_asignado

    except Exception as e:
        raise Exception(f"Error al guardar el registro en Google Sheets: {e}")
