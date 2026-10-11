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
    """Registra los datos del paciente en la hoja de Google Sheets correspondiente

    respetando el mapeo exacto del Censo Nominal y la Hoja CENSO.
    """
    try:
        client = obtener_cliente_gspread()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        # Definir el nombre de la hoja según la unidad o jornada activa
        nombre_hoja = sigla_url
        if sufijo_js:
            nombre_hoja = f"{sigla_url}_{sufijo_js}"

        try:
            ws = spreadsheet.worksheet(nombre_hoja)
        except Exception:
            ws = spreadsheet.get_worksheet(0)

        # Generar un folio consecutivo basado en los registros existentes (Fila inicial 14 o siguiente)
        todos_los_valores = ws.get_all_values()
        consecutivo = max(14, len(todos_los_valores) + 1)
        
        # Folio Formato Fila 14-15 (Ej: VIGILE-20N-20261011-0014)
        folio_asignado = (
            f"VIGILE-{sigla_url}-{datetime.datetime.now().strftime('%Y%m%d')}-{consecutivo:04d}"
        )

        p = datos_paciente
        com = p.get("comorbilidades", {})
        fn = p.get("fecha_nacimiento")

        # Separar fecha de nacimiento para las columnas individuales
        fn_dia = str(fn.day).zfill(2) if fn else ""
        fn_mes = str(fn.month).zfill(2) if fn else ""
        fn_anio = str(fn.year) if fn else ""

        # Mapeo exacto para Hoja 2 "CENSO" o la hoja activa del Censo Nominal
        fila_registro = [
            str(consecutivo),                                   # Col A (# / ID)
            folio_asignado,                                     # Col B (Folio consecutivo / Fila 14-15B)
            p.get("curp_con_nacimiento", ""),                   # Col C (RFC / CURP calculada automáticamente)
            p.get("cuenta_derechohabiencia", "NO"),             # Col D (¿Cuenta con derechohabiencia al ISSSTE?)
            p.get("tipo_dh", "ISSSTE"),                         # Col E (Tipo de DH)
            "SÍ" if p.get("trabaja_cmn") else "NO",             # Col F (Trabaja CMN)
            p.get("num_trabajador", ""),                        # Col G (# Trabajador)
            "SÍ" if com.get("personal_salud_riesgo") else "NO", # Col H (Personal de Salud)
            p.get("categoria", "NO APLICA"),                    # Col I (Categoría)
            p.get("servicio", "NO APLICA"),                     # Col J (Servicio)
            p.get("coordinacion", "NO APLICA"),                 # Col K (Coordinación)
            p.get("turno", "MATUTINO"),                         # Col L (Turno)
            p.get("nombres", "").upper(),                       # Col M (Nombre)
            p.get("paterno", "").upper(),                       # Col N (Paterno)
            p.get("materno", "").upper(),                       # Col O (Materno)
            p.get("estado_nacimiento", ""),                     # Col P (Edo Nac)
            p.get("municipio_nacimiento", "CDMX"),              # Col Q (Muni Nac)
            fn_dia,                                             # Col R (FN Día)
            fn_mes,                                             # Col S (FN Mes)
            fn_anio,                                            # Col T (FN Año)
            str(p.get("calc_anos", 0)),                         # Col U (Años - Edad calculada)
            str(p.get("calc_meses", 0)),                        # Col V (Meses - Edad calculada)
            p.get("sexo", ""),                                  # Col W (Sexo)
            "SÍ" if com.get("personas_embarazadas") else "NO",  # Col X (Embarazo condicionado si es Mujer)
            p.get("estado_residencia", "CDMX"),                 # Col Y / Entidad Federativa (CDMX)
            "ISSSTE",                                           # Col Z / Institución
            "Delegación Sur",                                   # Col AA / Jurisdicción
            "CDMX",                                             # Col AB / Municipio
            "CDMX",                                             # Col AC / Localidad
            p.get("unidad_salud", "CMN 20 de Noviembre"),       # Col AD / Unidad de Salud
            "",                                                 # Col AE / AGEB
            "",                                                 # Col AF / Sector
            val_fecha_app.strftime("%d/%m/%Y") if isinstance(val_fecha_app, datetime.date) else str(val_fecha_app), # Col AG / Fecha de aplicación
            p.get("responsable_vacunacion", ""),                # Col AH / Nombre del responsable
            # Comorbilidades / Grupos de riesgo marcados con X o SÍ según tu interfaz
            "X" if com.get("personas_embarazadas") else "",     # EMBARAZADAS
            "X" if com.get("personal_salud_riesgo") else "",    # PERSONAL DE SALUD
            "X" if com.get("vih") else "",                      # VIH/sida
            "X" if com.get("diabetes") else "",                 # DIABETES MELLITUS
            "X" if com.get("obesidad") else "",                 # OBESIDAD MÓRBIDA
            "X" if com.get("cardiopatias") else "",             # CARDIOPATÍAS
            "X" if com.get("enfermedad_pulmonar") else "",      # EPOC / ASMA
            "X" if com.get("cancer") else "",                   # CÁNCER
            "X" if com.get("cardiacas_congenitas") else "",     # CARDIACAS O PULMONARES CONGÉNITAS
            "X" if com.get("insuficiencia_renal") else "",      # INSUFICIENCIA RENAL
            "X" if com.get("inmunosupresion") else "",          # INMUNOSUPRESIÓN
            "X" if com.get("discapacidades") else "",           # DISCAPACIDADES
            "X" if com.get("fibrosis_quistica") else "",        # FIBROSIS QUÍSTICA
            "X" if com.get("hipertension") else "",             # HIPERTENSIÓN ARTERIAL
            com.get("texto_otro", ""),                          # Otros grupos de riesgo (texto libre)
            p.get("cuenta_derechohabiencia", ""),               # Derechohabiencia (AQ)
            p.get("antecedente_influenza", ""),                 # AR: Antecedente Influenza (Si/No)
            p.get("antecedente_covid", ""),                     # AS: Antecedente COVID (Si/No)
            "X" if p.get("vacuna_interes") in ["INFLUENZA", "AMBAS"] else "", # AT: INFLUENZA interés
            "X" if p.get("vacuna_interes") in ["COVID-19", "AMBAS"] else "",  # AU: COVID interés
            "X" if p.get("vacuna_interes") == "AMBAS" else "",              # AV: AMBAS interés
        ]

        ws.append_row(fila_registro)
        return folio_asignado

    except Exception as e:
        raise Exception(f"Error al guardar el registro en Google Sheets: {e}")
