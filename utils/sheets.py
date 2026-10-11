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

    en la hoja correspondiente a la unidad/jornada activa en la URL.
    """
    try:
        client = obtener_cliente_gspread()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        # Definir el nombre de la hoja según la unidad o jornada activa
        nombre_hoja = sigla_url
        if sufijo_js:
            nombre_hoja = f"{sigla_url}_{sufijo_js}"

        # Búsqueda precisa de la worksheet
        ws = None
        try:
            ws = spreadsheet.worksheet(nombre_hoja)
        except Exception:
            # Si no existe la hoja exacta, buscamos si alguna hoja contiene la sigla URL
            hojas_disponibles = spreadsheet.worksheets()
            for h in hojas_disponibles:
                if sigla_url.upper() in h.title.upper():
                    ws = h
                    break
            
            # Si de plano no existe ninguna coincidencia, la creamos automáticamente con el nombre correcto
            if ws is None:
                ws = spreadsheet.add_worksheet(title=nombre_hoja, rows=1000, cols=50)

        # Determinar consecutivo a partir de la fila 14
        todos_los_valores = ws.get_all_values()
        consecutivo = max(14, len(todos_los_valores) + 1)
        
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

        # Mapeo exacto por columnas para la Hoja activa correspondiente
        fila_registro = [
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

        ws.append_row(fila_registro)
        return folio_asignado

    except Exception as e:
        raise Exception(f"Error al guardar el registro en Google Sheets: {e}")
