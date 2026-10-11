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

    y retorna un folio único asignado.
    """
    try:
        client = obtener_cliente_gspread()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        # Definir el nombre de la hoja según la unidad o jornada activa
        nombre_hoja = sigla_url
        if sufijo_js:
            nombre_hoja = f"{sigla_url}_{sufijo_js}"

        # Intentar obtener la worksheet; si no existe, se puede usar una por defecto o crearla
        try:
            ws = spreadsheet.worksheet(nombre_hoja)
        except Exception:
            # Si no existe la hoja específica, intentamos usar la primera o la predeterminada
            ws = spreadsheet.get_worksheet(0)

        # Generar un folio consecutivo basado en los registros existentes
        todos_los_valores = ws.get_all_values()
        # Filtramos filas que tengan datos para contar el siguiente consecutivo
        consecutivo = len(todos_los_valores) + 1
        folio_asignado = (
            f"VIGILE-{sigla_url}-{datetime.datetime.now().strftime('%Y%m%d')}-{consecutivo:04d}"
        )

        # Extraer comorbilidades y datos del diccionario recibido
        p = datos_paciente
        com = p.get("comorbilidades", {})

        # Preparar la fila de datos estructurada según el orden de tus columnas
        # (Ajusta los campos de la lista según la estructura exacta de tu tabla en Google Sheets)
        fila_registro = [
            str(consecutivo),  # A: ID / Consecutivo
            p.get("paterno", "").upper(),  # B: Apellido Paterno
            p.get("materno", "").upper(),  # C: Apellido Materno
            p.get("nombres", "").upper(),  # D: Nombre(s)
            (
                p.get("fecha_nacimiento").strftime("%Y-%m-%d")
                if p.get("fecha_nacimiento")
                else ""
            ),  # E: Fecha Nac.
            str(p.get("calc_anos", 0)),  # F: Años
            str(p.get("calc_meses", 0)),  # G: Meses
            p.get("sexo", ""),  # H: Sexo
            p.get("curp_con_nacimiento", ""),  # I: CURP
            p.get("estado_residencia", ""),  # J: Estado Residencia
            p.get("calle", "").upper(),  # K: Calle
            p.get("numero", "").upper(),  # L: Número
            p.get("colonia", "").upper(),  # M: Colonia
            p.get("cuenta_derechohabiencia", ""),  # N: Derechohabiencia
            p.get("ocupacion", "").upper(),  # O: Ocupación
            (
                "SÍ" if com.get("personas_embarazadas") else "NO"
            ),  # P: Embarazada
            ("SÍ" if com.get("personal_salud_riesgo") else "NO"),  # Q: Personal Salud
            ("SÍ" if com.get("vih") else "NO"),  # R: VIH
            ("SÍ" if com.get("diabetes") else "NO"),  # S: Diabetes
            ("SÍ" if com.get("obesidad") else "NO"),  # T: Obesidad
            ("SÍ" if com.get("cardiopatias") else "NO"),  # U: Cardiopatías
            ("SÍ" if com.get("enfermedad_pulmonar") else "NO"),  # V: EPOC/Asma
            ("SÍ" if com.get("cancer") else "NO"),  # W: Cáncer
            ("SÍ" if com.get("cardiacas_congenitas") else "NO"),  # X: Congénitas
            ("SÍ" if com.get("insuficiencia_renal") else "NO"),  # Y: Renal
            ("SÍ" if com.get("inmunosupresion") else "NO"),  # Z: Inmunosupresión
            ("SÍ" if com.get("discapacidades") else "NO"),  # AA: Discapacidad
            ("SÍ" if com.get("fibrosis_quistica") else "NO"),  # AB: Fibrosis
            ("SÍ" if com.get("hipertension") else "NO"),  # AC: Hipertensión
            ("SÍ" if com.get("otro") else "NO"),  # AD: Otro riesgo
            com.get("texto_otro", ""),  # AE: Especificación otro
            p.get("vacuna_interes", ""),  # AF: Vacuna de interés
            p.get("antecedente_covid", ""),  # AS: Antecedente COVID
            p.get("antecedente_influenza", ""),  # AR: Antecedente Influenza
            val_fecha_app.strftime("%d/%m/%Y")
            if isinstance(val_fecha_app, datetime.date)
            else str(val_fecha_app),  # AW: Fecha Aplicación
            datetime.date.today().strftime("%d/%m/%Y"),  # Fecha Registro
            folio_asignado,  # Folio Asignado
        ]

        # Agregar la fila al final de la hoja en Google Sheets
        ws.append_row(fila_registro)

        return folio_asignado

    except Exception as e:
        raise Exception(f"Error al guardar el registro en Google Sheets: {e}")
