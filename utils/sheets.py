import datetime
import base64
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID
from google.oauth2 import service_account
import gspread
import streamlit as st


def obtener_cliente_gspread():
    """Autentica y retorna el cliente de gspread reparando cualquier alteración de padding en la llave PEM."""
    if "GOOGLE_CREDENTIALS" not in st.secrets:
        raise ValueError("No se encontró la sección [GOOGLE_CREDENTIALS] en los secretos.")

    creds_dict = dict(st.secrets["GOOGLE_CREDENTIALS"])

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        pk = creds_dict["private_key"]
        
        # Limpiar retornos de carro y espacios sobrantes
        pk = pk.replace("\r", "").strip()
        
        # Extraer estrictamente el contenido entre los headers si viene mezclado
        if "BEGIN PRIVATE KEY" in pk:
            lines = pk.split("\n")
            clean_lines = []
            recording = False
            for line in lines:
                if "BEGIN PRIVATE KEY" in line:
                    recording = True
                    clean_lines.append("-----BEGIN PRIVATE KEY-----")
                    continue
                if "END PRIVATE KEY" in line:
                    clean_lines.append("-----END PRIVATE KEY-----")
                    recording = False
                    continue
                if recording:
                    # Eliminar espacios internos en la cadena base64 que rompen el padding
                    stripped = line.strip()
                    if stripped:
                        clean_lines.append(stripped)
            pk = "\n".join(clean_lines)
            
        creds_dict["private_key"] = pk

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
    """Registra los datos del paciente respetando bloques de 2 filas por paciente

    a partir de la fila 14 y colocando la CURP en la fila complementaria (Fila + 1, Columna C).
    """
    try:
        client = obtener_cliente_gspread()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        nombre_hoja = sigla_url
        if sufijo_js:
            nombre_hoja = f"{sigla_url}_{sufijo_js}"

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
                ws = spreadsheet.add_worksheet(
                    title=nombre_hoja, rows=1000, cols=50
                )

        todos_los_valores = ws.get_all_values()

        fila_destino = 14
        consecutivo = 1

        if len(todos_los_valores) >= 14:
            idx = 13
            while idx < len(todos_los_valores):
                if (
                    idx >= len(todos_los_valores)
                    or not any(todos_los_valores[idx])
                    or not todos_los_valores[idx][1]
                ):
                    fila_destino = idx + 1
                    break
                idx += 2
            else:
                fila_destino = len(todos_los_valores) + 1
                if (fila_destino - 14) % 2 != 0:
                    fila_destino += 1

        consecutivo = ((fila_destino - 14) // 2) + 1

        fecha_str = (
            val_fecha_app.strftime("%Y%m%d")
            if isinstance(val_fecha_app, datetime.date)
            else datetime.date.today().strftime("%Y%m%d")
        )
        modalidad_texto = str(
            datos_paciente.get("modalidad", "INTRAMUROS")
        ).upper()
        mod_str = "INT" if "INTRA" in modalidad_texto else "EXT"
        siglas_3 = sigla_url[:3].upper().ljust(3, "X")
        secuencial_str = str(consecutivo).zfill(4)

        folio_asignado = (
            f"{fecha_str}-{mod_str}-{siglas_3}-{secuencial_str}"
        )

        p = datos_paciente
        com = p.get("comorbilidades", {})
        fn = p.get("fecha_nacimiento")

        fn_dia = str(fn.day).zfill(2) if fn else ""
        fn_mes = str(fn.month).zfill(2) if fn else ""
        fn_anio = str(fn.year) if fn else ""

        edad_anos = str(p.get("calc_anos", 0))
        edad_meses = str(p.get("calc_meses", 0))

        es_menor_59m = (
            p.get("calc_anos", 0) * 12
        ) + p.get("calc_meses", 0) <= 59
        es_mayor_60 = p.get("calc_anos", 0) >= 60

        marca_6_59m = "X" if es_menor_59m else ""
        marca_60_mas = "X" if es_mayor_60 else ""
        vacuna_interes = p.get("vacuna_interes", "")

        fecha_registro_actual = datetime.date.today().strftime("%d/%m/%Y")

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
            (
                val_fecha_app.strftime("%d/%m/%Y")
                if isinstance(val_fecha_app, datetime.date)
                else str(val_fecha_app)
            ),
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
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            p.get("cuenta_derechohabiencia", "NO"),
            p.get("antecedente_influenza", "NO"),
            p.get("antecedente_covid", "NO"),
            "X" if vacuna_interes in ["INFLUENZA", "AMBAS"] else "",
            "X" if vacuna_interes in ["COVID-19", "AMBAS"] else "",
            "X" if vacuna_interes == "AMBAS" else "",
            fecha_registro_actual,
        ]

        if fila_destino <= len(todos_los_valores):
            rango_celdas = f"A{fila_destino}:AW{fila_destino}"
            ws.update(rango_celdas, [fila_registro_principal])
        else:
            ws.append_row(fila_registro_principal)

        fila_curp = fila_destino + 1
        ws.update(
            f"C{fila_curp}", [[p.get("curp_con_nacimiento", "").upper()]]
        )
        ws.update(f"AW{fila_curp}", [[fecha_registro_actual]])

        return folio_asignado

    except Exception as e:
        raise Exception(f"Error al guardar el registro en Google Sheets: {e}")
