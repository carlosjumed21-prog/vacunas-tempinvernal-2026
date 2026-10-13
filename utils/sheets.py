# utils/sheets.py
import datetime
import json
from config import GOOGLE_SHEET_ID, GOOGLE_SCOPES
import gspread
import streamlit as st


@st.cache_resource
def obtener_cliente_gspread():
    """Autentica y retorna el cliente de gspread usando GOOGLE_CREDENTIALS de forma nativa y segura."""
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = (
            json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
        )
    else:
        primera_llave = list(st.secrets.keys())[0]
        creds_dict = dict(st.secrets[primera_llave])

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    # Utiliza el método oficial de gspread para evitar cualquier error de AuthorizedSession
    return gspread.service_account_from_dict(creds_dict, scopes=GOOGLE_SCOPES)


def guardar_registro_censal(
    sigla_url,
    sufijo_js,
    tipo_jornada,
    val_fecha_app,
    nombre_unidad_completo,
    datos_paciente,
):
    """
    Versión altamente optimizada: lee la columna B una sola vez y utiliza
    batch_update para escribir tanto la fila principal como la complementaria
    en una sola solicitud HTTP, eliminando el lag.
    """
    try:
        client = obtener_cliente_gspread()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        nombre_hoja = sigla_url if not sufijo_js else f"{sigla_url}_{sufijo_js}"
        try:
            ws = spreadsheet.worksheet(nombre_hoja)
        except Exception:
            ws = None
            for h in spreadsheet.worksheets():
                if sigla_url.upper() in h.title.upper():
                    ws = h
                    break
            if ws is None:
                ws = spreadsheet.add_worksheet(title=nombre_hoja, rows=2000, cols=60)

        # --- localizar fila destino leyendo sólo la columna B (folios) ---
        col_b = ws.col_values(2)
        fila_destino = 14
        if len(col_b) >= 14:
            idx = 13
            while idx < len(col_b):
                if idx >= len(col_b) or not str(col_b[idx]).strip():
                    fila_destino = idx + 1
                    break
                idx += 2
            else:
                fila_destino = len(col_b) + 1
                if (fila_destino - 14) % 2 != 0:
                    fila_destino += 1

        consecutivo = ((fila_destino - 14) // 2) + 1

        fecha_str = val_fecha_app.strftime("%Y%m%d") if isinstance(val_fecha_app, datetime.date) else datetime.date.today().strftime("%Y%m%d")
        modalidad_texto = str(datos_paciente.get("modalidad", "INTRAMUROS")).upper()
        mod_str = "INT" if "INTRA" in modalidad_texto else "EXT"
        siglas_3 = sigla_url[:3].upper().ljust(3, 'X')
        secuencial_str = str(consecutivo).zfill(4)

        folio_asignado = f"{fecha_str}-{mod_str}-{siglas_3}-{secuencial_str}"

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

        fecha_registro_actual = datetime.date.today().strftime("%d/%m/%Y")
        correo_paciente_val = p.get("correo_paciente", "").strip()

        fila_registro_principal = [
            str(consecutivo),
            folio_asignado,
            p.get("paterno", "").upper(),
            p.get("materno", "").upper(),
            p.get("nombres", "").upper(),
            fn_dia,
            fn_mes,
            fn_anio,
            edad_anos,
            edad_meses,
            p.get("sexo", ""),
            val_fecha_app.strftime("%d/%m/%Y") if isinstance(val_fecha_app, datetime.date) else str(val_fecha_app),
            p.get("calle", "").upper(),
            p.get("numero", "").upper(),
            p.get("colonia", "").upper(),
            marca_6_59m,
            marca_60_mas,
            "X" if com.get("personas_embarazadas") else "",
            "X" if com.get("personal_salud_riesgo") else "",
            "X" if com.get("vih") else "",
            "X" if com.get("diabetes") else "",
            "X" if com.get("obesidad") else "",
            "X" if com.get("cardiopatias") else "",
            "X" if com.get("enfermedad_pulmonar") else "",
            "X" if com.get("cancer") else "",
            "X" if com.get("cardiacas_congenitas") else "",
            "X" if com.get("insuficiencia_renal") else "",
            "X" if com.get("inmunosupresion") else "",
            "X" if com.get("discapacidades") else "",
            "X" if com.get("fibrosis_quistica") else "",
            "X" if com.get("hipertension") else "",
            com.get("texto_otro", ""),
            "", "", "", "", "", "", "", "", "", "",
            p.get("cuenta_derechohabiencia", "NO"),
            p.get("antecedente_influenza", "NO"),
            p.get("antecedente_covid", "NO"),
            "X" if vacuna_interes in ["INFLUENZA", "AMBAS"] else "",
            "X" if vacuna_interes in ["COVID-19", "AMBAS"] else "",
            "X" if vacuna_interes == "AMBAS" else "",
            fecha_registro_actual,
            correo_paciente_val,
        ]

        curp_val = p.get("curp_con_nacimiento", "").upper()
        fila_curp = fila_destino + 1

        data_a_actualizar = [
            {
                'range': f"A{fila_destino}:AX{fila_destino}",
                'values': [fila_registro_principal]
            },
            {
                'range': f"C{fila_curp}",
                'values': [[curp_val]]
            },
            {
                'range': f"AW{fila_curp}",
                'values': [[fecha_registro_actual]]
            }
        ]

        ws.batch_update(data_a_actualizar)

        return folio_asignado, False, None

    except Exception as e:
        raise Exception(f"Error al guardar el registro en Google Sheets: {e}")
