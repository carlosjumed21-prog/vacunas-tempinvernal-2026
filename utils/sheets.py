import datetime
import json
from google.oauth2 import service_account
import gspread
import streamlit as st
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID


def guardar_registro_censal(
    sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente
):
    try:
        fecha_str_hoja = val_fecha_app.strftime("%d%m%y")
        tipo_texto_jornada = "INTRA" if tipo_jornada == "I" else "EXTRA"
        nombre_hoja_destino = (
            f"{sigla_url}_{tipo_texto_jornada}{sufijo_js}_{fecha_str_hoja}"
        )

        scope = GOOGLE_SCOPES
        creds_dict = None
        try:
            if "GOOGLE_CREDENTIALS" in st.secrets:
                raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
                creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
            elif "gpex" in st.secrets:
                creds_dict = dict(st.secrets["gpex"])
            elif len(st.secrets.keys()) > 0:
                primera_llave = list(st.secrets.keys())[0]
                creds_dict = dict(st.secrets[primera_llave])
        except Exception:
            pass

        if not creds_dict:
            raise KeyError("No se encontraron credenciales válidas configuradas en st.secrets.")

        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scope
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        try:
            worksheet = spreadsheet.worksheet(nombre_hoja_destino)
        except:
            worksheet = spreadsheet.worksheet("CENSO NOMINAL")

        if worksheet.col_count < 49:
            worksheet.resize(cols=50)

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
        vacuna_interes = datos_paciente["vacuna_interes"]
        planes_o_embarazo = datos_paciente["planes_o_embarazo"]
        comorbilidades = datos_paciente.get("comorbilidades", {})
        
        antecedente_influenza = datos_paciente.get("antecedente_influenza", "")
        antecedente_covid = datos_paciente.get("antecedente_covid", "")

        responsable_brigada = datos_paciente.get("responsable", "")

        dia_n = str(fecha_nacimiento.day).zfill(2)
        mes_n = str(fecha_nacimiento.month).zfill(2)
        anio_n = str(fecha_nacimiento.year)
        anos_str = str(calc_anos)
        meses_str = str(calc_meses)
        sexo_letra = "H" if sexo == "HOMBRE" else "M"
        
        fecha_app_str = val_fecha_app.strftime("%d/%m/%Y")
        fecha_registro_str = datetime.date.today().strftime("%d/%m/%Y")

        calle_str = calle.upper()
        num_str = numero.upper()
        col_str = colonia.upper()

        marca_inf = "X" if vacuna_interes in ["INFLUENZA", "AMBAS"] else ""
        marca_cov = "X" if vacuna_interes in ["COVID-19", "AMBAS"] else ""
        marca_amb = "X" if vacuna_interes == "AMBAS" else ""

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
                "range": f"A{f_actual}:A{f_siguiente}",
                "values": [[siguiente_num], [siguiente_num]],
            },
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
                "range": f"AQ{f_actual}:AQ{f_siguiente}",
                "values": [[cuenta_derechohabiencia], [cuenta_derechohabiencia]],
            },
            {
                "range": f"AR{f_actual}:AR{f_siguiente}",
                "values": [[antecedente_influenza], [antecedente_influenza]],
            },
            {
                "range": f"AS{f_actual}:AS{f_siguiente}",
                "values": [[antecedente_covid], [antecedente_covid]],
            },
            {
                "range": f"AT{f_actual}:AT{f_siguiente}",
                "values": [[marca_inf], [marca_inf]],
            },
            {
                "range": f"AU{f_actual}:AU{f_siguiente}",
                "values": [[marca_cov], [marca_cov]],
            },
            {
                "range": f"AV{f_actual}:AV{f_siguiente}",
                "values": [[marca_amb], [marca_amb]],
            },
            {
                "range": f"AW{f_actual}:AW{f_siguiente}",
                "values": [[fecha_registro_str], [fecha_registro_str]],
            },
        ]

        tiene_dosis_aplicada = (
            datos_paciente.get("inf_1ra") or 
            datos_paciente.get("inf_2da") or 
            datos_paciente.get("inf_anual") or 
            datos_paciente.get("cov_1ra") or 
            datos_paciente.get("cov_2da") or 
            datos_paciente.get("cov_anual")
        )

        if datos_paciente.get("inf_1ra"):
            datos_a_actualizar.append({"range": f"AG{f_actual}:AG{f_siguiente}", "values": [["X"], ["X"]]})
        if datos_paciente.get("inf_2da"):
            datos_a_actualizar.append({"range": f"AH{f_actual}:AH{f_siguiente}", "values": [["X"], ["X"]]})
        if datos_paciente.get("inf_anual"):
            datos_a_actualizar.append({"range": f"AI{f_actual}:AI{f_siguiente}", "values": [["X"], ["X"]]})
        
        if datos_paciente.get("lote_inf"):
            lote_i = datos_paciente.get("lote_inf").upper()
            datos_a_actualizar.append({"range": f"AJ{f_actual}:AJ{f_siguiente}", "values": [[lote_i], [lote_i]]})
        if datos_paciente.get("cad_inf"):
            cad_i = datos_paciente.get("cad_inf")
            cad_i_str = cad_i.strftime("%d/%m/%Y") if hasattr(cad_i, "strftime") else str(cad_i)
            datos_a_actualizar.append({"range": f"AK{f_actual}:AK{f_siguiente}", "values": [[cad_i_str], [cad_i_str]]})

        if datos_paciente.get("cov_1ra"):
            datos_a_actualizar.append({"range": f"AL{f_actual}:AL{f_siguiente}", "values": [["X"], ["X"]]})
        if datos_paciente.get("cov_2da"):
            datos_a_actualizar.append({"range": f"AM{f_actual}:AM{f_siguiente}", "values": [["X"], ["X"]]})
        if datos_paciente.get("cov_anual"):
            datos_a_actualizar.append({"range": f"AN{f_actual}:AN{f_siguiente}", "values": [["X"], ["X"]]})
        
        if datos_paciente.get("lote_cov"):
            lote_c = datos_paciente.get("lote_cov").upper()
            datos_a_actualizar.append({"range": f"AO{f_actual}:AO{f_siguiente}", "values": [[lote_c], [lote_c]]})
        if datos_paciente.get("cad_cov"):
            cad_c = datos_paciente.get("cad_cov")
            cad_c_str = cad_c.strftime("%d/%m/%Y") if hasattr(cad_c, "strftime") else str(cad_c)
            datos_a_actualizar.append({"range": f"AP{f_actual}:AP{f_siguiente}", "values": [[cad_c_str], [cad_c_str]]})

        edad_total_meses = (calc_anos * 12) + calc_meses
        
        if 6 <= edad_total_meses <= 59:
            datos_a_actualizar.append({"range": f"P{f_actual}:P{f_siguiente}", "values": [["X"], ["X"]]})
        elif calc_anos >= 60:
            datos_a_actualizar.append({"range": f"Q{f_actual}:Q{f_siguiente}", "values": [["X"], ["X"]]})

        if comorbilidades.get("personas_embarazadas") or planes_o_embarazo == "SÍ":
            datos_a_actualizar.append({"range": f"R{f_actual}:R{f_siguiente}", "values": [["X"], ["X"]]})
        if comorbilidades.get("personal_salud_riesgo"):
            datos_a_actualizar.append({"range": f"S{f_actual}:S{f_siguiente}", "values": [["X"], ["X"]]})

        mapa_comorb_cols = {
            "vih": "T",
            "diabetes": "U",
            "obesidad": "V",
            "cardiopatias": "W",
            "enfermedad_pulmonar": "X",
            "cancer": "Y",
            "cardiacas_congenitas": "Z",
            "insuficiencia_renal": "AA",
            "inmunosupresion": "AB",
            "discapacidades": "AC",
            "fibrosis_quistica": "AD",
            "hipertension": "AE"
        }

        for clave_c, col_c in mapa_comorb_cols.items():
            if comorbilidades.get(clave_c, False):
                datos_a_actualizar.append({"range": f"{col_c}{f_actual}:{col_c}{f_siguiente}", "values": [["X"], ["X"]]})

        if comorbilidades.get("otro", False):
            texto_o = comorbilidades.get("texto_otro", "").upper()
            if texto_o:
                datos_a_actualizar.append({"range": f"AF{f_actual}:AF{f_siguiente}", "values": [[texto_o], [texto_o]]})

        worksheet.batch_update(datos_a_actualizar)

        color_fondo = (
            {"red": 0.831, "green": 0.929, "blue": 0.855} if tiene_dosis_aplicada 
            else {"red": 1.0, "green": 1.0, "blue": 1.0}
        )

        peticion_color_fila = {
            "repeatCell": {
                "range": {
                    "sheetId": worksheet.id,
                    "startRowIndex": f_actual - 1,      
                    "endRowIndex": f_siguiente,       
                    "startColumnIndex": 0,            
                    "endColumnIndex": 49              
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": color_fondo
                    }
                },
                "fields": "userEnteredFormat.backgroundColor"
            }
        }
        worksheet.spreadsheet.batch_update({"requests": [peticion_color_fila]})

        return folio_asignado

    except Exception as e:
        raise e


def guardar_registro_censal_20_nov(datos_paciente):
    try:
        scope = GOOGLE_SCOPES
        creds_dict = None
        try:
            if "GOOGLE_CREDENTIALS" in st.secrets:
                raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
                creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
            elif "gpex" in st.secrets:
                creds_dict = dict(st.secrets["gpex"])
            elif len(st.secrets.keys()) > 0:
                primera_llave = list(st.secrets.keys())[0]
                creds_dict = dict(st.secrets[primera_llave])
        except Exception:
            pass

        if not creds_dict:
            raise KeyError("No se encontraron credenciales válidas configuradas en st.secrets.")

        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scope
        )
        client = gspread.authorize(creds)
        
        sheet_id_20n = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"
        spreadsheet = client.open_by_key(sheet_id_20n)

        val_fecha_app = datos_paciente.get("val_fecha_app", datetime.date.today())
        tipo_jornada = datos_paciente.get("tipo_jornada", "I")
        fecha_str_hoja = val_fecha_app.strftime("%d%m%y")
        tipo_texto_jornada = "INTRA" if tipo_jornada == "I" else "EXTRA"
        
        nombre_hoja_nominal = f"20N_{tipo_texto_jornada}_{fecha_str_hoja}_NOMINAL"

        try:
            ws_nominal = spreadsheet.worksheet(nombre_hoja_nominal)
        except:
            plantilla_1 = spreadsheet.worksheet("CENSO NOMINAL")
            ws_nominal = spreadsheet.duplicate_sheet(
                plantilla_1.id, 
                insert_sheet_index=len(spreadsheet.worksheets()), 
                new_sheet_name=nombre_hoja_nominal
            )

        if ws_nominal.col_count < 49:
            ws_nominal.resize(cols=50)

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
        siglas_unidad = st.session_state.get("siglas_unidad", "20N")
        folio_asignado = f"{aammmdd}-{tipo_jornada}{siglas_unidad}-{str(num_nom).zfill(3)}"

        updates_hoja1 = [
            {"range": "D7", "values": [["CDMX"]]},
            {"range": "M7", "values": [["ISSSTE"]]},
            {"range": "T7", "values": [["Delegación Sur"]]},
            {"range": "AB7", "values": [["CDMX"]]},
            {"range": "D8", "values": [["CDMX"]]},
            {"range": "D9", "values": [[st.session_state.get("nombre_unidad", "CMN 20 DE NOVIEMBRE")]]},
            {"range": "AB9", "values": [[val_fecha_app.strftime("%d/%m/%Y")]]},
            {"range": f"A{fila_nom}:A{fila_nom+1}", "values": [[num_nom], [num_nom]]},
            {"range": f"B{fila_nom}:B{fila_nom+1}", "values": [[folio_asignado], [folio_asignado]]},
            {"range": f"C{fila_nom}", "values": [[datos_paciente['paterno'].upper()]]},
            {"range": f"D{fila_nom}", "values": [[datos_paciente['materno'].upper() if datos_paciente['materno'] else ""]]},
            {"range": f"E{fila_nom}", "values": [[datos_paciente['nombre'].upper()]]},
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
            {"range": f"C{fila_nom+1}", "values": [[datos_paciente.get('curp','')]]},
            {"range": f"AQ{fila_nom}:AQ{fila_nom+1}", "values": [[datos_paciente['dh']], [datos_paciente['dh']]]},
            {"range": f"AW{fila_nom}:AW{fila_nom+1}", "values": [[datetime.date.today().strftime("%d/%m/%Y")], [datetime.date.today().strftime("%d/%m/%Y")]]},
        ]
        
        ws_nominal.batch_update(updates_hoja1)

        peticion_blanco = {
            "repeatCell": {
                "range": {
                    "sheetId": ws_nominal.id,
                    "startRowIndex": fila_nom - 1,
                    "endRowIndex": fila_nom + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 49
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}
                    }
                },
                "fields": "userEnteredFormat.backgroundColor"
            }
        }
        ws_nominal.spreadsheet.batch_update({"requests": [peticion_blanco]})

        return folio_asignado

    except Exception as e:
        raise e
