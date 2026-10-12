import datetime
from config import GOOGLE_SCOPES, GOOGLE_SHEET_ID
from google.oauth2 import service_account
import gspread
import streamlit as st


def obtener_cliente_gspread():
    """Autentica y retorna el cliente de gspread normalizando correctamente la llave privada."""
    if "GOOGLE_CREDENTIALS" not in st.secrets:
        raise ValueError("No se encontró la sección [GOOGLE_CREDENTIALS] en los secretos de Streamlit Cloud.")

    # Extraer los datos de la sección de secretos de forma segura
    secret_section = st.secrets["GOOGLE_CREDENTIALS"]
    creds_dict = {
        "type": secret_section.get("type", "service_account"),
        "project_id": secret_section.get("project_id"),
        "private_key_id": secret_section.get("private_key_id"),
        "private_key": secret_section.get("private_key"),
        "client_email": secret_section.get("client_email"),
        "client_id": secret_section.get("client_id"),
        "auth_uri": secret_section.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
        "token_uri": secret_section.get("token_uri", "https://oauth2.googleapis.com/token"),
        "auth_provider_x509_cert_url": secret_section.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
        "client_x509_cert_url": secret_section.get("client_x509_cert_url"),
        "universe_domain": secret_section.get("universe_domain", "googleapis.com")
    }

    pk = creds_dict.get("private_key", "")
    if pk:
        # Limpiar retornos de carro y espacios extras
        pk = pk.replace("\r", "").strip()
        
        # Si la llave viene con caracteres '\\n' escapados, los convertimos a saltos de línea reales
        if "\\n" in pk and "\n" not in pk:
            pk = pk.replace("\\n", "\n")
            
        # Asegurarnos de que las cabeceras estén limpias y sin espacios internos
        lines = [line.strip() for line in pk.split("\n") if line.strip()]
        
        # Reconstruir el bloque PEM de forma exacta
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        
        if header in lines:
            lines.remove(header)
        if footer in lines:
            lines.remove(footer)
            
        # Formatear el contenido base64 en líneas exactas de 64 caracteres (requisito estricto de padding RSA)
        body_joined = "".join(lines)
        chunks = [body_joined[i:i+64] for i in range(0, len(body_joined), 64)]
        
        creds_dict["private_key"] = f"{header}\n" + "\n".join(chunks) + f"\n{footer}\n"

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
