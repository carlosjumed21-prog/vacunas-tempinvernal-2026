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
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

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
        grupo_sugerido = datos_paciente["grupo_sugerido"]
        planes_o_embarazo = datos_paciente["planes_o_embarazo"]
        ocupacion = datos_paciente["ocupacion"]
        comorbilidades = datos_paciente["comorbilidades"]
        
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

        # Mapeo exacto de cabecera con tus coordenadas específicas (D7, M7, T7, AB7, D8, D9, M9, S9, AB9, E10)
        datos_a_actualizar = [
            {"range": "D7", "values": [["CDMX"]]},                  # Entidad Federativa (7D)
            {"range": "M7", "values": [["ISSSTE"]]},                 # Institución (7M)
            {"range": "T7", "values": [["Delegación Sur"]]},       # Jurisdicción / Delegación (7T)
            {"range": "AB7", "values": [["CDMX"]]},                # Municipio (7AB)
            {"range": "D8", "values": [["CDMX"]]},                  # Localidad (8D)
            {"range": "D9", "values": [[nombre_unidad_completo]]},  # Unidad de Salud (9D)
            {"range": "M9", "values": [[""]]},                      # AGEB (blanco) (9M)
            {"range": "S9", "values": [[""]]},                      # Sector (blanco) (9S)
            {"range": "AB9", "values": [[fecha_app_str]]},          # Fecha de aplicación (9AB)
            {"range": "E10", "values": [[responsable_brigada]]},    # Nombre del responsable de vacunación (10E)
            
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

        if grupo_sugerido == "6 A 59 MESES":
            datos_a_actualizar.append(
                {"range": f"P{f_actual}:P{f_siguiente}", "values": [["X"], ["X"]]}
            )
        elif grupo_sugerido == "60 Y MÁS":
            datos_a_actualizar.append(
                {"range": f"Q{f_actual}:Q{f_siguiente}", "values": [["X"], ["X"]]}
            )

        if planes_o_embarazo == "SÍ":
            datos_a_actualizar.append(
                {"range": f"R{f_actual}:R{f_siguiente}", "values": [["X"], ["X"]]}
            )
        if ocupacion == "PERSONAL DE SALUD":
            datos_a_actualizar.append(
                {"range": f"S{f_actual}:S{f_siguiente}", "values": [["X"], ["X"]]}
            )

        mapa_comorbilidades = {
            "vih": "T",
            "diabetes": "U",
            "obesidad": "V",
            "cardiopatias": "W",
            "cancer": "Y",
            "insuficiencia_renal": "AA",
            "discapacidades": "AC",
            "fibrosis_quistica": "AD",
            "hipertension": "AE",
        }

        for key, col in mapa_comorbilidades.items():
            if comorbilidades.get(key, False):
                datos_a_actualizar.append(
                    {
                        "range": f"{col}{f_actual}:{col}{f_siguiente}",
                        "values": [["X"], ["X"]],
                    }
                )

        worksheet.batch_update(datos_a_actualizar)
        return folio_asignado

    except Exception as e:
        raise e


def guardar_registro_censal_20_nov(datos_paciente):
    """Guarda el registro censal específico del CMN '20 de Noviembre'
    en la hoja de Google Sheets duplicada correspondiente (Hoja 1 / NOMINAL).
    """
    try:
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
        client = gspread.authorize(creds)
        
        sheet_id_20n = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"
        spreadsheet = client.open_by_key(sheet_id_20n)

        val_fecha_app = datos_paciente.get("val_fecha_app", datetime.date.today())
        tipo_jornada = datos_paciente.get("tipo_jornada", "I")
        fecha_str_hoja = val_fecha_app.strftime("%d%m%y")
        tipo_texto_jornada = "INTRA" if tipo_jornada == "I" else "EXTRA"
        
        nombre_hoja_nominal = f"20N_{tipo_texto_jornada}_{fecha_str_hoja}_NOMINAL"

        try:
            worksheet = spreadsheet.worksheet(nombre_hoja_nominal)
        except:
            plantilla_1 = spreadsheet.worksheet("CENSO NOMINAL")
            worksheet = spreadsheet.duplicate_sheet(
                plantilla_1.id, 
                insert_sheet_index=len(spreadsheet.worksheets()), 
                new_sheet_name=nombre_hoja_nominal
            )

        columna_a = worksheet.col_values(1)
        fila_inicio_destino = 2
        for idx in range(1, len(columna_a)):
            val = str(columna_a[idx]).strip()
            if val == "" or not val.isdigit():
                fila_inicio_destino = idx + 1
                break
        else:
            fila_inicio_destino = max(2, len(columna_a) + 1)

        siguiente_num = fila_inicio_destino - 1

        rfc = datos_paciente["rfc"]
        dh = datos_paciente["dh"]
        tipo_dh = datos_paciente["tipo_dh"]
        trabaja_cmn = datos_paciente["trabaja_cmn"]
        num_trabajador = datos_paciente["num_trabajador"]
        personal_salud = datos_paciente["personal_salud"]
        categoria = datos_paciente["categoria"]
        servicio = datos_paciente["servicio"]
        coordinacion = datos_paciente["coordinacion"]
        turno = datos_paciente["turno"]
        nombre = datos_paciente["nombre"]
        paterno = datos_paciente["paterno"]
        materno = datos_paciente["materno"]
        edo_nac = datos_paciente["edo_nac"]
        muni_nac = datos_paciente["muni_nac"]
        fn_dia = datos_paciente["fn_dia"]
        fn_mes = datos_paciente["fn_mes"]
        fn_ano = datos_paciente["fn_ano"]
        anos = datos_paciente["anos"]
        meses = datos_paciente["meses"]
        sexo = datos_paciente["sexo"]
        embarazo = datos_paciente["embarazo"]

        fila_actual = fila_inicio_destino
        datos_a_actualizar = [
            {"range": f"A{fila_actual}", "values": [[siguiente_num]]},
            {"range": f"B{fila_actual}", "values": [[rfc]]},
            {"range": f"C{fila_actual}", "values": [[dh]]},
            {"range": f"D{fila_actual}", "values": [[tipo_dh]]},
            {"range": f"E{fila_actual}", "values": [[trabaja_cmn]]},
            {"range": f"F{fila_actual}", "values": [[num_trabajador]]},
            {"range": f"G{fila_actual}", "values": [[personal_salud]]},
            {"range": f"H{fila_actual}", "values": [[categoria]]},
            {"range": f"I{fila_actual}", "values": [[servicio]]},
            {"range": f"J{fila_actual}", "values": [[coordinacion]]},
            {"range": f"K{fila_actual}", "values": [[turno]]},
            {"range": f"L{fila_actual}", "values": [[nombre]]},
            {"range": f"M{fila_actual}", "values": [[paterno]]},
            {"range": f"N{fila_actual}", "values": [[materno]]},
            {"range": f"O{fila_actual}", "values": [[edo_nac]]},
            {"range": f"P{fila_actual}", "values": [[muni_nac]]},
            {"range": f"Q{fila_actual}", "values": [[fn_dia]]},
            {"range": f"R{fila_actual}", "values": [[fn_mes]]},
            {"range": f"S{fila_actual}", "values": [[fn_ano]]},
            {"range": f"T{fila_actual}", "values": [[anos]]},
            {"range": f"U{fila_actual}", "values": [[meses]]},
            {"range": f"V{fila_actual}", "values": [[sexo]]},
            {"range": f"W{fila_actual}", "values": [[embarazo]]},
        ]

        worksheet.batch_update(datos_a_actualizar)
        return siguiente_num

    except Exception as e:
        raise e
