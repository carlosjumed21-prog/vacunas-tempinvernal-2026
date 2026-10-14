import datetime
import streamlit as st
import gspread
from utils.logica_registro import obtener_cliente_gspread_seguro

def guardar_registro_censal_20_nov(datos_paciente):
    """
    Guarda el registro censal específico del CMN '20 de Noviembre'
    en la hoja nominal de la jornada y realiza de forma conjunta la migración
    exacta hacia la hoja maestra 'CENSO' general respetando el mapeo de columnas (B a AH).
    """
    try:
        client = obtener_cliente_gspread_seguro()
        sheet_id_20n = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"
        spreadsheet = client.open_by_key(sheet_id_20n)

        val_fecha_app = datos_paciente.get("val_fecha_app", datetime.date.today())
        tipo_jornada = datos_paciente.get("tipo_jornada", "I")
        fecha_str_hoja = val_fecha_app.strftime("%d%m%y")
        tipo_texto_jornada = "INTRA" if tipo_jornada == "I" else "EXTRA"
        
        siglas_unidad = st.session_state.get("siglas_unidad", "20N")
        sufijo_js = st.session_state.get("sufijo_js", "")
        nombre_hoja_nominal = f"{siglas_unidad}_{tipo_texto_jornada}{sufijo_js}_{fecha_str_hoja}_NOMINAL"

        # --- 1. HOJA NOMINAL DINÁMICA DE LA JORNADA ---
        try:
            ws_nominal = spreadsheet.worksheet(nombre_hoja_nominal)
        except Exception:
            try:
                plantilla_1 = spreadsheet.worksheet("CENSO NOMINAL")
            except Exception:
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
        folio_asignado = f"{aammmdd}-{tipo_jornada}{siglas_unidad}-{str(num_nom).zfill(3)}"

        # --- 2. HOJA MAESTRA GENERAL "CENSO" ---
        try:
            ws_censo_general = spreadsheet.worksheet("CENSO")
        except Exception:
            ws_censo_general = ws_nominal

        col_b_censo = ws_censo_general.col_values(2)
        fila_censo = max(14, len(col_b_censo) + 1)
        consecutivo_censo = fila_censo - 13

        # Datos del paciente
        comorb = datos_paciente.get("comorbilidades", {})
        ant_inf_val = datos_paciente.get("antecedente_influenza", "")
        ant_cov_val = datos_paciente.get("antecedente_covid", "")
        vacuna_int = datos_paciente.get("vacuna_interes", "").upper()
        
        ps_val = "SÍ" if datos_paciente.get("personal_salud") == "SÍ" else "NO"
        emb_val = "SÍ" if datos_paciente.get("embarazo") == "SÍ" else "NO"
        fecha_app_fmt = val_fecha_app.strftime("%d/%m/%Y")

        # --- 3. ACTUALIZACIÓN EN HOJA NOMINAL (JORNADA) ---
        f_actual = fila_nom
        f_siguiente = fila_nom + 1

        updates_nominal = [
            {"range": "D7", "values": [["CDMX"]]},
            {"range": "M7", "values": [["ISSSTE"]]},
            {"range": "T7", "values": [["Delegación Sur"]]},
            {"range": "AB7", "values": [["CDMX"]]},
            {"range": "D8", "values": [["CDMX"]]},
            {"range": "D9", "values": [[st.session_state.get("nombre_unidad", "CMN 20 DE NOVIEMBRE")]]},
            {"range": "AB9", "values": [[fecha_app_fmt]]},
            {"range": f"B{f_actual}:B{f_siguiente}", "values": [[folio_asignado], [folio_asignado]]},
            {"range": f"C{f_actual}", "values": [[datos_paciente['paterno'].upper()]]},
            {"range": f"D{f_actual}", "values": [[datos_paciente['materno'].upper() if datos_paciente.get('materno') else ""]]},
            {"range": f"E{f_actual}", "values": [[datos_paciente['nombres'].upper()]]},
            {"range": f"F{f_actual}:F{f_siguiente}", "values": [[datos_paciente['fn_dia']], [datos_paciente['fn_dia']]]},
            {"range": f"G{f_actual}:G{f_siguiente}", "values": [[datos_paciente['fn_mes']], [datos_paciente['fn_mes']]]},
            {"range": f"H{f_actual}:H{f_siguiente}", "values": [[datos_paciente['fn_ano']], [datos_paciente['fn_ano']]]},
            {"range": f"I{f_actual}:I{f_siguiente}", "values": [[str(datos_paciente['anos'])], [str(datos_paciente['anos'])]]},
            {"range": f"J{f_actual}:J{f_siguiente}", "values": [[str(datos_paciente['meses'])], [str(datos_paciente['meses'])]]},
            {"range": f"K{f_actual}:K{f_siguiente}", "values": [["H" if datos_paciente['sexo']=="HOMBRE" else "M"], ["H" if datos_paciente['sexo']=="HOMBRE" else "M"]]},
            {"range": f"L{f_actual}:L{f_siguiente}", "values": [[fecha_app_fmt], [fecha_app_fmt]]},
            {"range": f"M{f_actual}:M{f_siguiente}", "values": [[datos_paciente.get('calle','').upper()], [datos_paciente.get('calle','').upper()]]},
            {"range": f"N{f_actual}:N{f_siguiente}", "values": [[datos_paciente.get('numero','').upper()], [datos_paciente.get('numero','').upper()]]},
            {"range": f"O{f_actual}:O{f_siguiente}", "values": [[datos_paciente.get('colonia','').upper()], [datos_paciente.get('colonia','').upper()]]},
            {"range": f"C{f_actual+1}", "values": [[datos_paciente.get('curp_con_nacimiento','')]]},
            {"range": f"AQ{f_actual}:AQ{f_siguiente}", "values": [[datos_paciente.get('cuenta_derechohabiencia', 'SÍ')], [datos_paciente.get('cuenta_derechohabiencia', 'SÍ')]]},
            {"range": f"AR{f_actual}:AR{f_siguiente}", "values": [[ant_inf_val], [ant_inf_val]]},
            {"range": f"AS{f_actual}:AS{f_siguiente}", "values": [[ant_cov_val], [ant_cov_val]]},
            {"range": f"AW{f_actual}:AW{f_siguiente}", "values": [[datetime.date.today().strftime("%d/%m/%Y")], [datetime.date.today().strftime("%d/%m/%Y")]]},
            {"range": f"AX{f_actual}:AX{f_siguiente}", "values": [[datos_paciente.get('correo_paciente', '')], [datos_paciente.get('correo_paciente', '')]]},
        ]

        if vacuna_int in ["INFLUENZA", "AMBAS"]:
            updates_nominal.append({"range": f"AT{f_actual}:AT{f_siguiente}", "values": [["X"], ["X"]]})
        if vacuna_int in ["COVID-19", "AMBAS"]:
            updates_nominal.append({"range": f"AU{f_actual}:AU{f_siguiente}", "values": [["X"], ["X"]]})
        if vacuna_int == "AMBAS":
            updates_nominal.append({"range": f"AV{f_actual}:AV{f_siguiente}", "values": [["X"], ["X"]]})

        if int(datos_paciente['anos']) < 5:
            updates_nominal.append({"range": f"P{f_actual}:P{f_siguiente}", "values": [["X"], ["X"]]})
        elif int(datos_paciente['anos']) >= 60:
            updates_nominal.append({"range": f"Q{f_actual}:Q{f_siguiente}", "values": [["X"], ["X"]]})

        if datos_paciente.get('embarazo') == "SÍ":
            updates_nominal.append({"range": f"R{f_actual}:R{f_siguiente}", "values": [["X"], ["X"]]})
        if datos_paciente.get('personal_salud') == "SÍ":
            updates_nominal.append({"range": f"S{f_actual}:S{f_siguiente}", "values": [["X"], ["X"]]})

        map_comorb_h1 = {
            "vih": "T", "diabetes": "U", "obesidad": "V", "cardiopatias": "W",
            "enfermedad_pulmonar": "X", "cancer": "Y", "cardiacas_congenitas": "Z",
            "insuficiencia_renal": "AA", "inmunosupresion": "AB", "discapacidades": "AC",
            "fibrosis_quistica": "AD", "hipertension": "AE"
        }
        for k_c, col_c in map_comorb_h1.items():
            if comorb.get(k_c, False):
                updates_nominal.append({"range": f"{col_c}{f_actual}:{col_c}{f_siguiente}", "values": [["X"], ["X"]]})

        ws_nominal.batch_update(updates_nominal)

        # --- 4. ACTUALIZACIÓN CONJUNTA EN LA HOJA MAESTRA "CENSO" (B hasta AH) ---
        updates_censo = [
            {"range": f"A{fila_censo}", "values": [[consecutivo_censo]]},
            {"range": f"B{fila_censo}", "values": [[folio_asignado]]},
            {"range": f"C{fila_censo}", "values": [[datos_paciente.get("rfc", "")]]},
            {"range": f"D{fila_censo}", "values": [[datos_paciente.get("cuenta_derechohabiencia", "SÍ")]]},
            {"range": f"E{fila_censo}", "values": [[datos_paciente.get("tipo_dh", "TRABAJADOR ACTIVO")]]},
            {"range": f"F{fila_censo}", "values": [[datos_paciente.get("trabaja_cmn", "SÍ")]]},
            {"range": f"G{fila_censo}", "values": [[datos_paciente.get("num_trabajador", "")]]},
            {"range": f"H{fila_censo}", "values": [[ps_val]]},
            {"range": f"I{fila_censo}", "values": [[datos_paciente.get("categoria", "")]]},
            {"range": f"J{fila_censo}", "values": [[datos_paciente.get("servicio", "")]]},
            {"range": f"K{fila_censo}", "values": [[datos_paciente.get("coordinacion", "")]]},
            {"range": f"L{fila_censo}", "values": [[datos_paciente.get("turno", "")]]},
            {"range": f"M{fila_censo}", "values": [[datos_paciente["nombres"].upper()]]},
            {"range": f"N{fila_censo}", "values": [[datos_paciente["paterno"].upper()]]},
            {"range": f"O{fila_censo}", "values": [[datos_paciente["materno"].upper() if datos_paciente.get("materno"] else ""]]},
            {"range": f"P{fila_censo}", "values": [[datos_paciente.get("edo_nac", "CDMX")]]},
            {"range": f"Q{fila_censo}", "values": [[datos_paciente.get("muni_nac", "")]]},
            {"range": f"R{fila_censo}", "values": [[datos_paciente["fn_dia"]]]},
            {"range": f"S{fila_censo}", "values": [[datos_paciente["fn_mes"]]]},
            {"range": f"T{fila_censo}", "values": [[datos_paciente["fn_ano"]]]},
            {"range": f"U{fila_censo}", "values": [[str(datos_paciente["anos"])]]},
            {"range": f"V{fila_censo}", "values": [[str(datos_paciente["meses"])]]},
            {"range": f"W{fila_censo}", "values": [[datos_paciente["sexo"]]]},
            {"range": f"X{fila_censo}", "values": [[emb_val]]},
        ]

        # Mapeo de vacunas de interés en la hoja CENSO general según tus columnas exactas:
        # Y: 1ra dosis Influenza, Z: 2da dosis Influenza, AA: Dosis anual Influenza
        # AD: 1ra dosis COVID, AE: 2da dosis COVID, AF: Dosis anual COVID
        if vacuna_int in ["INFLUENZA", "AMBAS"]:
            updates_censo.append({"range": f"Y{fila_censo}", "values": [["X"]]})
        if vacuna_int in ["COVID-19", "AMBAS"]:
            updates_censo.append({"range": f"AD{fila_censo}", "values": [["X"]]})

        ws_censo_general.batch_update(updates_censo)

        return folio_asignado

    except Exception as e:
        raise Exception(f"Error al guardar el registro en Google Sheets: {e}")
