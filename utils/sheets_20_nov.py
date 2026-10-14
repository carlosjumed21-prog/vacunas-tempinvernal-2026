import datetime
import json
from google.oauth2 import service_account
import gspread
import streamlit as st
from config import GOOGLE_SCOPES

def obtener_cliente_gspread():
    """Autentica y retorna el cliente de gspread utilizando los secretos del proyecto."""
    scope = GOOGLE_SCOPES
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = (
            json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
        )
    elif "gpex" in st.secrets:
        creds_dict = dict(st.secrets["gpex"])
    else:
        primera_llave = list(st.secrets.keys())[0]
        creds_dict = dict(st.secrets[primera_llave])

    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=scope
    )
    return gspread.authorize(creds)

def guardar_registro_censal(
    sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente
):
    try:
        fecha_str_hoja = val_fecha_app.strftime("%d%m%y")
        tipo_texto_jornada = "INTRA" if tipo_jornada == "I" else "EXTRA"
        nombre_hoja_destino = (
            f"{sigla_url}_{tipo_texto_jornada}{sufijo_js}_{fecha_str_hoja}"
        )

        client = obtener_cliente_gspread()
        sheet_id_20n = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"
        spreadsheet = client.open_by_key(sheet_id_20n)

        try:
            worksheet = spreadsheet.worksheet(nombre_hoja_destino)
        except:
            worksheet = spreadsheet.worksheet("CENSO NOMINAL")

        columna_b = worksheet.col_values(2)
        fila_inicio_destino = 14
        
        idx = 13
        while idx < len(columna_b):
            val_actual = str(columna_b[idx]).strip()
            if val_actual == "" or "POR ASIGNAR" in val_actual.upper():
                fila_inicio_destino = idx + 1
                break
            idx += 2
        else:
            fila_inicio_destino = max(14, len(columna_b) + 1)
            if (fila_inicio_destino - 14) % 2 != 0:
                fila_inicio_destino += 1

        siguiente_num = ((fila_inicio_destino - 14) // 2) + 1
        aammmdd = val_fecha_app.strftime("%y%m%d")
        folio_asignado = f"{aammmdd}-{tipo_jornada}{sigla_url}-{str(siguiente_num).zfill(3)}"

        f_actual = fila_inicio_destino
        f_siguiente = fila_inicio_destino + 1

        paterno = datos_paciente["paterno"]
        materno = datos_paciente["materno"]
        nombres = datos_paciente["nombres"]
        fecha_nacimiento = datos_paciente["fecha_nacimiento"]
        calc_anos = datos_paciente["calc_anos"]
        calc_meses = datos_paciente["calc_meses"]
        sexo = datos_paciente["sexo"]
        calle = datos_paciente["calle"]
        numero = datos_paciente["numero"]
        colonia = datos_paciente["colonia"]
        curp_con_nacimiento = datos_paciente["curp_con_nacimiento"]
        cuenta_derechohabiencia = datos_paciente["cuenta_derechohabiencia"]
        responsable_brigada = datos_paciente.get("responsable", "")

        dia_n = str(fecha_nacimiento.day).zfill(2)
        mes_n = str(fecha_nacimiento.month).zfill(2)
        anio_n = str(fecha_nacimiento.year)
        anos_str = str(calc_anos)
        meses_str = str(calc_meses)
        sexo_letra = "H" if sexo == "HOMBRE" else "M"
        fecha_app_str = val_fecha_app.strftime("%d/%m/%Y")
        calle_str = calle.upper()
        num_str = numero.upper()
        col_str = colonia.upper()

        datos_a_actualizar = [
            {"range": "D7", "values": [["CDMX"]]},
            {"range": "M7", "values": [["ISSSTE"]]},
            {"range": "T7", "values": [["Delegación Sur"]]},
            {"range": "AB7", "values": [["CDMX"]]},
            {"range": "D8", "values": [["CDMX"]]},
            {"range": "D9", "values": [[nombre_unidad_completo]]},
            {"range": "M9", "values": [[""]]},
            {"range": "S9", "values": [[""]]},
            {"range": "AB9", "values": [[fecha_app_str]]},
            {"range": "E10", "values": [[responsable_brigada]]},
            
            {
                "range": f"B{f_actual}:B{f_siguiente}",
                "values": [[folio_asignado], [folio_asignado]],
            },
            {"range": f"C{f_actual}", "values": [[paterno.upper()]]},
            {
                "range": f"D{f_actual}",
                "values": [[materno.upper() if materno else ""]],
            },
            {"range": f"E{f_actual}", "values": [[nombres.upper()]]},
            {
                "range": f"F{f_actual}:F{f_siguiente}",
                "values": [[dia_n], [dia_n]],
            },
            {
                "range": f"G{f_actual}:G{f_siguiente}",
                "values": [[mes_n], [mes_n]],
            },
            {
                "range": f"H{f_actual}:H{f_siguiente}",
                "values": [[anio_n], [anio_n]],
            },
            {
                "range": f"I{f_actual}:I{f_siguiente}",
                "values": [[anos_str], [anos_str]],
            },
            {
                "range": f"J{f_actual}:J{f_siguiente}",
                "values": [[meses_str], [meses_str]],
            },
            {
                "range": f"K{f_actual}:K{f_siguiente}",
                "values": [[sexo_letra], [sexo_letra]],
            },
            {
                "range": f"L{f_actual}:L{f_siguiente}",
                "values": [[fecha_app_str], [fecha_app_str]],
            },
            {
                "range": f"M{f_actual}:M{f_siguiente}",
                "values": [[calle_str], [calle_str]],
            },
            {
                "range": f"N{f_actual}:N{f_siguiente}",
                "values": [[num_str], [num_str]],
            },
            {
                "range": f"O{f_actual}:O{f_siguiente}",
                "values": [[col_str], [col_str]],
            },
            {"range": f"C{f_siguiente}", "values": [[curp_con_nacimiento]]},
            {
                "range": f"AN{f_actual}:AN{f_siguiente}",
                "values": [
                    [cuenta_derechohabiencia],
                    [cuenta_derechohabiencia],
                ],
            },
        ]

        worksheet.batch_update(datos_a_actualizar)
        return folio_asignado

    except Exception as e:
        raise e


def guardar_registro_censal_20_nov(datos_paciente):
    """Guarda el registro censal específico del CMN '20 de Noviembre'
    en la hoja nominal duplicada y en la hoja de censo correspondiente,
    mapeando todos los campos laborales, derechohabiencia, comorbilidades y antecedentes.
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

        # --- 1. ESCRITURA EN LA HOJA NOMINAL DINÁMICA (DUPLICADA) ---
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

        comorb = datos_paciente.get("comorbilidades", {})
        
        # Extracción de antecedentes vacunales y vacuna de interés
        ant_inf_val = datos_paciente.get("antecedente_influenza", "")
        ant_cov_val = datos_paciente.get("antecedente_covid", "")
        vacuna_int = datos_paciente.get("vacuna_interes", "").upper()

        updates_hoja1 = [
            {"range": "D7", "values": [["CDMX"]]},
            {"range": "M7", "values": [["ISSSTE"]]},
            {"range": "T7", "values": [["Delegación Sur"]]},
            {"range": "AB7", "values": [["CDMX"]]},
            {"range": "D8", "values": [["CDMX"]]},
            {"range": "D9", "values": [[st.session_state.get("nombre_unidad", "CMN 20 DE NOVIEMBRE")]]},
            {"range": "AB9", "values": [[val_fecha_app.strftime("%d/%m/%Y")]]},
            {"range": f"B{fila_nom}:B{fila_nom+1}", "values": [[folio_asignado], [folio_asignado]]},
            {"range": f"C{fila_nom}", "values": [[datos_paciente['paterno'].upper()]]},
            {"range": f"D{fila_nom}", "values": [[datos_paciente['materno'].upper() if datos_paciente.get('materno') else ""]]},
            {"range": f"E{fila_nom}", "values": [[datos_paciente['nombres'].upper()]]},
            {"range": f"F{fila_nom}:F{fila_nom+1}", "values": [[datos_paciente['fn_dia']], [datos_paciente['fn_dia']]]},
            {"range": f"G{fila_nom}:G{fila_nom+1}", "values": [[datos_paciente['fn_mes']], [datos_paciente['fn_mes']]]},
            {"range": f"H{fila_nom}:H{fila_nom+1}", "values": [[datos_paciente['fn_ano']], [datos_paciente['fn_ano']]]},
            {"range": f"I{fila_nom}:I{fila_nom+1}", "values": [[str(datos_paciente['anos'])], [str(datos_paciente['anos'])]]},
            {"range": f"J{fila_nom}:J{fila_nom+1}", "values": [[str(datos_paciente['meses'])], [str(datos_paciente['meses'])]]},
            {"range": f"K{fila_nom}:K{fila_nom+1}", "values": [["H" if datos_paciente['sexo']=="HOMBRE" else "M"], ["H" if datos_paciente['sexo']=="HOMBRE" else "M"]]},
            {"range": f"L{fila_nom}:L{fila_nom+1}", "values": [[val_fecha_app.strftime("%d/%m/%Y")], [val_fecha_app.strftime("%d/%m/%Y")]]},
            {"range": f"M{fila_nom}:M{fila_nom+1}", "values": [[datos_paciente.get('calle','').upper()], [datos_paciente.get('calle','').upper()]]},
            {"range": f"N{fila_nom}:N{fila_nom+1}", "values": [[datos_paciente.get('numero','').upper()], [datos_paciente.get('numero','').upper()]]},
            {"range": f"O{fila_nom}:O{fila_nom+1}", "values": [[datos_paciente.get('colonia','').upper()], [datos_paciente.get('colonia','').upper()]]},
            {"range": f"C{fila_nom+1}", "values": [[datos_paciente.get('curp_con_nacimiento','')]]},
            
            # --- Mapeos solicitados (AQ, AR, AS, AT, AU, AV, AW, AX) ---
            {"range": f"AQ{fila_nom}:AQ{fila_nom+1}", "values": [[datos_paciente.get('cuenta_derechohabiencia', 'SÍ')], [datos_paciente.get('cuenta_derechohabiencia', 'SÍ')]]},
            {"range": f"AR{fila_nom}:AR{fila_nom+1}", "values": [[ant_inf_val], [ant_inf_val]]},
            {"range": f"AS{fila_nom}:AS{fila_nom+1}", "values": [[ant_cov_val], [ant_cov_val]]},
            {"range": f"AW{fila_nom}:AW{fila_nom+1}", "values": [[datetime.date.today().strftime("%d/%m/%Y")], [datetime.date.today().strftime("%d/%m/%Y")]]},
            {"range": f"AX{fila_nom}:AX{fila_nom+1}", "values": [[datos_paciente.get('correo_paciente', '')], [datos_paciente.get('correo_paciente', '')]]},
        ]
        
        # Mapeo condicional para Vacuna de Interés (AT, AU, AV)
        if vacuna_int in ["INFLUENZA", "AMBAS"]:
            updates_hoja1.append({"range": f"AT{fila_nom}:AT{fila_nom+1}", "values": [["X"], ["X"]]})
        if vacuna_int in ["COVID-19", "AMBAS"]:
            updates_hoja1.append({"range": f"AU{fila_nom}:AU{fila_nom+1}", "values": [["X"], ["X"]]})
        if vacuna_int == "AMBAS":
            updates_hoja1.append({"range": f"AV{fila_nom}:AV{fila_nom+1}", "values": [["X"], ["X"]]})

        if int(datos_paciente['anos']) < 5:
            updates_hoja1.append({"range": f"P{fila_nom}:P{fila_nom+1}", "values": [["X"], ["X"]]})
        elif int(datos_paciente['anos']) >= 60:
            updates_hoja1.append({"range": f"Q{fila_nom}:Q{fila_nom+1}", "values": [["X"], ["X"]]})

        if datos_paciente.get('embarazo') == "SÍ":
            updates_hoja1.append({"range": f"R{fila_nom}:R{fila_nom+1}", "values": [["X"], ["X"]]})
        if datos_paciente.get('personal_salud') == "SÍ":
            updates_hoja1.append({"range": f"S{fila_nom}:S{fila_nom+1}", "values": [["X"], ["X"]]})

        map_comorb_h1 = {
            "vih": "T", "diabetes": "U", "obesidad": "V", "cardiopatias": "W",
            "enfermedad_pulmonar": "X", "cancer": "Y", "cardiacas_congenitas": "Z",
            "insuficiencia_renal": "AA", "inmunosupresion": "AB", "discapacidades": "AC",
            "fibrosis_quistica": "AD", "hipertension": "AE"
        }
        for k_c, col_c in map_comorb_h1.items():
            if comorb.get(k_c, False):
                updates_hoja1.append({"range": f"{col_c}{fila_nom}:{col_c}{fila_nom+1}", "values": [["X"], ["X"]]})

        ws_nominal.batch_update(updates_hoja1)

        # --- 2. ESCRITURA EN LA HOJA DE CENSO TABULAR ---
        nombre_hoja_censo = f"{siglas_unidad}_{tipo_texto_jornada}{sufijo_js}_{fecha_str_hoja}_CENSO"
        try:
            ws_censo = spreadsheet.worksheet(nombre_hoja_censo)
        except:
            try:
                ws_censo = spreadsheet.worksheet("CENSO")
            except:
                try:
                    plantilla_censo = spreadsheet.worksheet("CENSO NOMINAL")
                except:
                    plantilla_censo = ws_nominal
                ws_censo = spreadsheet.duplicate_sheet(
                    plantilla_censo.id, 
                    insert_sheet_index=len(spreadsheet.worksheets()), 
                    new_sheet_name=nombre_hoja_censo
                )

        col_a_censo = ws_censo.col_values(1)
        fila_censo = 14
        for idx_c in range(13, len(col_a_censo)):
            val_c = str(col_a_censo[idx_c]).strip()
            if val_c == "" or not val_c.isdigit():
                fila_censo = idx_c + 1
                break
        else:
            fila_censo = max(14, len(col_a_censo) + 1)

        consecutivo_censo = fila_censo - 13

        ps_val = "SÍ" if datos_paciente.get("personal_salud") == "SÍ" else "NO"
        emb_val = "SÍ" if datos_paciente.get("embarazo") == "SÍ" else "NO"

        updates_censo = [
            {"range": f"A{fila_censo}", "values": [[consecutivo_censo]]},
            {"range": f"B{fila_censo}", "values": [[folio_asignado]]},
            {"range": f"C{fila_censo}", "values": [[datos_paciente.get("rfc", "")]]},
            {"range": f"D{fila_censo}", "values": [[datos_paciente.get("cuenta_derechohabiencia", "SÍ")]]},
            {"range": f"E{fila_censo}", "values": [[datos_paciente.get("tipo_dh", "TRABAJADOR")]]},
            {"range": f"F{fila_censo}", "values": [[datos_paciente.get("trabaja_cmn", "SÍ")]]},
            {"range": f"G{fila_censo}", "values": [[datos_paciente.get("num_trabajador", "")]]},
            {"range": f"H{fila_censo}", "values": [[ps_val]]},
            {"range": f"I{fila_censo}", "values": [[datos_paciente.get("categoria", "")]]},
            {"range": f"J{fila_censo}", "values": [[datos_paciente.get("servicio", "")]]},
            {"range": f"K{fila_censo}", "values": [[datos_paciente.get("coordinacion", "")]]},
            {"range": f"L{fila_censo}", "values": [[datos_paciente.get("turno", "")]]},
            {"range": f"M{fila_censo}", "values": [[datos_paciente["nombres"].upper()]]},
            {"range": f"N{fila_censo}", "values": [[datos_paciente["paterno"].upper()]]},
            {"range": f"O{fila_censo}", "values": [[datos_paciente["materno"].upper() if datos_paciente.get("materno") else ""]] },
            {"range": f"P{fila_censo}", "values": [[datos_paciente.get("estado_nacimiento", "CDMX")]]},
            {"range": f"Q{fila_censo}", "values": [[datos_paciente.get("muni_nac", "CDMX")]]},
            {"range": f"R{fila_censo}", "values": [[datos_paciente["fn_dia"]]]},
            {"range": f"S{fila_censo}", "values": [[datos_paciente["fn_mes"]]]},
            {"range": f"T{fila_censo}", "values": [[datos_paciente["fn_ano"]]]},
            {"range": f"U{fila_censo}", "values": [[str(datos_paciente["anos"])]]},
            {"range": f"V{fila_censo}", "values": [[str(datos_paciente["meses"])]]},
            {"range": f"W{fila_censo}", "values": [[datos_paciente["sexo"]]]},
            {"range": f"X{fila_censo}", "values": [[emb_val]]},
        ]

        ws_censo.batch_update(updates_censo)
        return folio_asignado

    except Exception as e:
        raise e
