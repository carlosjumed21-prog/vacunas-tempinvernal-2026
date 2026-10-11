import streamlit as st
import json
import datetime
from google.oauth2 import service_account
import gspread
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID


def obtener_cliente_gspread():
    """Autentica y retorna el cliente de gspread usando los secretos de Streamlit."""
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
        creds_dict, scopes=GOOGLE_SCOPES
    )
    return gspread.authorize(creds)


def guardar_registro_censal(
    sigla_url,
    sufijo_js,
    tipo_jornada,
    val_fecha_app,
    nombre_unidad_completo,
    datos_paciente,
):
    """Registra los datos del paciente mapeando exactamente las columnas

    del Censo Nominal y escribiendo la CURP en la Fila 15, Columna C.
    """
    try:
        client = obtener_cliente_gspread()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        # Definir el nombre de la hoja según la unidad o jornada activa
        nombre_hoja = sigla_url
        if sufijo_js:
            nombre_hoja = f"{sigla_url}_{sufijo_js}"

        # Búsqueda precisa de la worksheet o creación automática si no existe
        ws = None
        try:
            ws = spreadsheet.worksheet(nombre_hoja)
        except Exception:
            hojas_disponibles = spreadsheet.worksheets()
            for h in hojas_disponibles:
                if sigla_url.upper() in h.title.upper():
                    ws = h
                    break
            if ws is None:
                ws = spreadsheet.add_worksheet(title=nombre_hoja, rows=1000, cols=50)

        # Obtener todos los valores para calcular la fila exacta y el consecutivo
        todos_los_valores = ws.get_all_values()
        
        # Encontrar la primera fila vacía a partir de la fila 14 (índice 13 en Python)
        fila_destino = 14
        consecutivo = 1

        if len(todos_los_valores) >= 14:
            for idx in range(13, len(todos_los_valores)):
                if not any(todos_los_valores[idx]) or not todos_los_valores[idx][1]:
                    fila_destino = idx + 1
                    break
            else:
                fila_destino = len(todos_los_valores) + 1

        consecutivo = fila_destino - 13 if fila_destino >= 14 else 1

        folio_asignado = (
            f"VIGILE-{sigla_url}-{datetime.datetime.now().strftime('%Y%m%d')}-{consecutivo:04d}"
        )

        p = datos_paciente
        com = p.get("comorbilidades", {})
        fn = p.get("fecha_nacimiento")

        fn_dia = str(fn.day).zfill(2) if fn else ""
        fn_mes = str(fn.month).zfill(2) if fn else ""
        fn_anio = str(fn.year) if fn else ""

        edad_anos = str(p.get("calc_anos", 0))
        edad_meses = str(p.get("calc_meses", 0))

        es_menor_59m = (p.get("calc_anos", 0) * 12) + p.get("calc_meses", 0) <= 59
        es_mayor_60 = p.get("calc_anos", 0) >= 60

        marca_6_59m = "X" if es_menor_59m else ""
        marca_60_mas = "X" if es_mayor_60 else ""
        vacuna_interes = p.get("vacuna_interes", "")

        # Mapeo exacto columna por columna para la Fila Principal (Ej. Fila 14)
        fila_registro_14 = [
            str(consecutivo),                                   # Col A: Número consecutivo
            folio_asignado,                                     # Col B: Fila 14-15B (Folio)
            p.get("paterno", "").upper(),                       # Col C: Fila 14-15C (Paterno)
            p.get("materno", "").upper(),                       # Col D: Fila 14-15D (Materno)
            p.get("nombres", "").upper(),                       # Col E: Fila 14-15E (Nombres)
            fn_dia,                                             # Col F: dd
            fn_mes,                                             # Col G: mm
            fn_anio,                                            # Col H: yyyy
            edad_anos,                                          # Col I: Años (A)
            edad_meses,                                         # Col J: Meses (M)
            p.get("sexo", ""),                                  # Col K: Sexo*
            val_fecha_app.strftime("%d/%m/%Y") if isinstance(val_fecha_app, datetime.date) else str(val_fecha_app), # Col L: Fecha Aplicación
            p.get("calle", "").upper(),                         # Col M: Calle*
            p.get("numero", "").upper(),                        # Col N: No. (Ext / Int)*
            p.get("colonia", "").upper(),                       # Col O: Colonia*
            marca_6_59m,                                        # Col P: 6 a 59 MESES*
            marca_60_mas,                                       # Col Q: 60 Y MÁS
            "X" if com.get("personas_embarazadas") else "",     # Col R: EMBARAZADAS
            "X" if com.get("personal_salud_riesgo") else "",    # Col S: PERSONAL DE SALUD
            "X" if com.get("vih") else "",                      # Col T: VIH/sida
            "X" if com.get("diabetes") else "",                 # Col U: DIABETES MELLITUS
            "X" if com.get("obesidad") else "",                 # Col V: OBESIDAD MORBIDA
            "X" if com.get("cardiopatias") else "",             # Col W: CARDIOPATÍAS
            "X" if com.get("enfermedad_pulmonar") else "",      # Col X: EPOC Y ASMA
            "X" if com.get("cancer") else "",                   # Col Y: CÁNCER
            "X" if com.get("cardiacas_congenitas") else "",     # Col Z: CONGÉNITAS / SALICILATOS
            "X" if com.get("insuficiencia_renal") else "",      # Col AA: INSUFICIENCIA RENAL
            "X" if com.get("inmunosupresion") else "",          # Col AB: INMUNOSUPRESIÓN
            "X" if com.get("discapacidades") else "",           # Col AC: DISCAPACIDADES
            "X" if com.get("fibrosis_quistica") else "",        # Col AD: FIBROSIS QUÍSTICA
            "X" if com.get("hipertension") else "",             # Col AE: HIPERTENSIÓN ARTERIAL
            com.get("texto_otro", ""),                          # Col AF: Otros grupos de riesgo (texto)
            "",                                                 # Col AG: Influenza 1ra dosis
            "",                                                 # Col AH: Influenza 2da dosis
            "",                                                 # Col AI: Influenza Dosis anual
            "",                                                 # Col AJ: Influenza No. de lote
            "",                                                 # Col AK: Influenza Caducidad
            "",                                                 # Col AL: COVID 1ra dosis
            "",                                                 # Col AM: COVID 2da dosis
            "",                                                 # Col AN: COVID Dosis anual
            "",                                                 # Col AO: COVID No. de lote
            "",                                                 # Col AP: COVID Caducidad
            p.get("cuenta_derechohabiencia", "NO"),             # Col AQ: Derechohabiencia
            p.get("antecedente_influenza", "NO"),               # Col AR: AR INFLUENZA Si/No
            p.get("antecedente_covid", "NO"),                   # Col AS: AS COVID Si/No
            "X" if vacuna_interes in ["INFLUENZA", "AMBAS"] else "", # Col AT: INFLUENZA marcar X
            "X" if vacuna_interes in ["COVID-19", "AMBAS"] else "",  # Col AU: COVID marcar X
            "X" if vacuna_interes == "AMBAS" else "",              # Col AV: AMBAS marcar X
        ]

        # Actualizar o insertar la fila principal
        if fila_destino <= len(todos_los_valores):
            rango_celdas = f"A{fila_destino}:AV{fila_destino}"
            ws.update(rango_celdas, [fila_registro_14])
        else:
            ws.append_row(fila_registro_14)

        # Inyectar la CURP automática específicamente en la Fila 15, Columna C (C15)
        fila_curp = fila_destino + 1
        ws.update(f"C{fila_curp}", [[p.get("curp_con_nacimiento", "").upper()]])

        return folio_asignado

    except Exception as e:
        raise Exception(f"Error al guardar el registro en Google Sheets: {e}")
