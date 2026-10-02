import datetime
import json
from google.oauth2 import service_account
import gspread
import streamlit as st
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID


def guardar_registro_censal(
    sigla_url, sufijo_js, tipo_jornada, val_fecha_app, nombre_unidad_completo, datos_paciente
):
    """Maneja la conexión con Google Sheets, clona el bloque de la plantilla (14-15)

    e inserta los datos del paciente de forma consecutiva.
    """
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

        # --- LLENADO DE ENCABEZADOS GENERALES ---
        worksheet.update("D7", [["CDMX"]])
        worksheet.update("M7", [["ISSSTE"]])
        worksheet.update("T7", [["Delegación Sur"]])
        worksheet.update("AB7", [["CDMX"]])
        worksheet.update("D8", [["CDMX"]])
        worksheet.update("D9", [[nombre_unidad_completo]])
        worksheet.update("AB9", [[val_fecha_app.strftime("%d/%m/%Y")]])
        worksheet.update("E10", [[""]])

        # --- CÁLCULO DE LA SIGUIENTE FILA LIBRE ---
        todas_las_filas = worksheet.get_all_values()
        ultima_fila = len(todas_las_filas)
        fila_inicio_destino = max(16, ultima_fila + 1)
        if (fila_inicio_destino - 14) % 2 != 0:
            fila_inicio_destino += 1

        siguiente_num = ((fila_inicio_destino - 14) // 2) + 1
        aammmdd = val_fecha_app.strftime("%y%m%d")
        folio_asignado = f"{aammmdd}-{tipo_jornada}{sigla_url}-{str(siguiente_num).zfill(3)}"

        f_actual = fila_inicio_destino
        f_siguiente = fila_inicio_destino + 1

        # --- CLONAR LA PLANTILLA FIJA (FILAS 14-15) USANDO GRIDRANGE CORRECTO ---
        body_formato = {
            "requests": [
                {
                    "copyPaste": {
                        "source": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 13,  # Fila 14 (Index 13)
                            "endIndex": 15,       # Fila 15 (Index 15)
                            "startColumnIndex": 0,  # Columna A
                            "endColumnIndex": 39,   # Columna AM
                        },
                        "destination": {
                            "sheetId": worksheet.id,
                            "startRowIndex": f_actual - 1,
                            "endIndex": f_siguiente,
                            "startColumnIndex": 0,
                            "endColumnIndex": 39,
                        },
                        "pasteType": "PASTE_NORMAL",
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": worksheet.id,
                            "dimension": "ROWS",
                            "startIndex": f_actual - 1,
                            "endIndex": f_siguiente,
                        },
                        "properties": {"pixelSize": 55},
                        "fields": "pixelSize",
                    }
                },
            ]
        }
        spreadsheet.batch_update(body_formato)

        # --- EXTRACCIÓN DE DATOS DEL PACIENTE ---
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

        # Grupos objetivo y comorbilidades
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
