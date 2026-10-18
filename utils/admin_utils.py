import datetime
import io
import json
import urllib.parse
from config import (
    GOOGLE_SCOPES,
    GOOGLE_SHEET_ID,
    UNIDADES_ISSSTE,
)
from google.oauth2 import service_account
import gspread
import qrcode
import streamlit as st

# ==========================================
# CONFIGURACIÓN DE ACCESOS ADMINISTRATIVOS
# ==========================================
ADMINS_AUTORIZADOS = [
    "carlosju.med21@gmail.com",
    "wendy.hernandeza@issste.gob.mx"
]


def autenticar_administrador(correo, password):
    """Valida las credenciales de acceso del administrador."""
    correo_limpio = correo.strip().lower()
    if (correo_limpio == "carlosju.med21@gmail.com" and password == "OtaniOrochi26") or \
       (correo_limpio == "wendy.hernandeza@issste.gob.mx" and password == "MedPrev26"):
        return True, correo_limpio
    return False, ""


def es_administrador_autorizado(correo):
    """Verifica si un correo cuenta con permisos administrativos activos."""
    if not correo:
        return False
    return correo.strip().lower() in ADMINS_AUTORIZADOS


def obtener_cliente_gspread():
    """Autentica y retorna el cliente de gspread usando los secretos de Streamlit de forma nativa y segura."""
    scope = GOOGLE_SCOPES
    if "GOOGLE_CREDENTIALS" in st.secrets:
        raw_creds = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    elif "gpex" in st.secrets:
        creds_dict = dict(st.secrets["gpex"])
    else:
        primera_llave = list(st.secrets.keys())[0]
        valor = st.secrets[primera_llave]
        creds_dict = dict(valor) if hasattr(valor, "keys") else json.loads(valor)

    if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    return gspread.service_account_from_dict(creds_dict, scopes=scope)


def verificar_hojas_existentes(siglas_unidad, config_jornadas):
    """
    Verifica si las hojas ya existen en Google Sheets para evitar duplicados.

    Para 20N:
      - se sigue usando el patrón con sufijo de jornada/jornada simultánea
      - pero ya no se fuerza el sufijo _NOMINAL aquí
    """
    try:
        client = obtener_cliente_gspread()
        sheet_id_destino = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE" if siglas_unidad == "20N" else GOOGLE_SHEET_ID
        spreadsheet_maestro = client.open_by_key(sheet_id_destino)
        hojas_existentes = [h.title for h in spreadsheet_maestro.worksheets()]
        duplicadas = []

        for j_conf in config_jornadas:
            fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
            tipo_texto = j_conf["tipo_texto"]
            sufijo_hoja = j_conf.get("sufijo_hoja", "")

            nombre_prueba = f"{siglas_unidad}_{tipo_texto}{sufijo_hoja}_{fecha_str_val}"

            if nombre_prueba in hojas_existentes:
                duplicadas.append(nombre_prueba)

        return duplicadas, None
    except Exception as e:
        return [], str(e)


def autorizar_y_crear_jornadas(siglas_unidad, unidad_sel, jornada_sel, tipo_jornada_letra, tipo_jornada_texto, config_jornadas_activas):
    """Duplica la plantilla en Google Sheets, actualiza los metadatos y genera los enlaces y códigos QR."""
    try:
        client = obtener_cliente_gspread()
        sheet_id_destino = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE" if siglas_unidad == "20N" else GOOGLE_SHEET_ID
        spreadsheet_maestro = client.open_by_key(sheet_id_destino)

        hojas_creadas_exito = []
        base_url = "https://medprev-vacunas-invernal.streamlit.app"

        for j_conf in config_jornadas_activas:
            fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
            fecha_formato_oficial = j_conf["fecha"].strftime("%d/%m/%Y")
            fecha_url_str = j_conf["fecha"].strftime("%Y-%m-%d")

            resp_encoded = urllib.parse.quote(j_conf["responsable"])
            js_param = f"&js={j_conf['sufijo_qr']}" if j_conf["sufijo_qr"] else ""
            ruta_formulario = "registro_20_noviembre" if siglas_unidad == "20N" else "formulario"

            link_paciente = f"{base_url}/{ruta_formulario}?unidad={siglas_unidad}&jornada={tipo_jornada_letra}&fecha={fecha_url_str}&resp={resp_encoded}{js_param}"
            nombre_hoja_objetivo = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}"
            link_operativo = f"{base_url}/consulta_censia?hoja_activa={urllib.parse.quote(nombre_hoja_objetivo)}"

            url_qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link_paciente)}"
            formula_imagen_qr = f'=IMAGE("{url_qr_api}")'

            plantilla_nombre = "CENSO NOMINAL"
            plantilla = spreadsheet_maestro.worksheet(plantilla_nombre)

            copia = spreadsheet_maestro.duplicate_sheet(
                plantilla.id,
                insert_sheet_index=len(spreadsheet_maestro.worksheets()),
                new_sheet_name=nombre_hoja_objetivo
            )
            hoja_activa_maestro = spreadsheet_maestro.worksheet(nombre_hoja_objetivo)

            hoja_activa_maestro.update_acell("D7", "CDMX")
            hoja_activa_maestro.update_acell("M7", "ISSSTE")
            hoja_activa_maestro.update_acell("T7", "Delegación Sur")
            hoja_activa_maestro.update_acell("AB7", "CDMX")
            hoja_activa_maestro.update_acell("D8", "CDMX")
            hoja_activa_maestro.update_acell("D9", unidad_sel)
            hoja_activa_maestro.update_acell("AB9", fecha_formato_oficial)
            hoja_activa_maestro.update_acell("E10", j_conf["responsable"])

            hoja_activa_maestro.update(values=[[j_conf["correo"]]], range_name="AU4")
            hoja_activa_maestro.update(values=[[link_paciente]], range_name="AU6")
            hoja_activa_maestro.update(values=[[link_operativo]], range_name="AU7")
            hoja_activa_maestro.update(values=[[formula_imagen_qr]], range_name="AU8", value_input_option="USER_ENTERED")

            hoja_info = {
                "nombre": nombre_hoja_objetivo,
                "gid": str(copia.id),
                "unidad": unidad_sel,
                "siglas_unidad": siglas_unidad,
                "tipo_jornada": jornada_sel,
                "tipo_jornada_letra": tipo_jornada_letra,
                "responsable": j_conf["responsable"],
                "correo": j_conf["correo"],
                "fecha": j_conf["fecha"],
                "sheet_id": sheet_id_destino,
                "link_formulario": link_paciente,
                "link_operativo": link_operativo,
            }
            hojas_creadas_exito.append(hoja_info)

        return hojas_creadas_exito, None
    except Exception as e:
        return [], str(e)


@st.cache_data(ttl=60, show_spinner=False)
def _sincronizar_historial_universal_cache():
    client = obtener_cliente_gspread()
    ids_a_revisar = [GOOGLE_SHEET_ID, "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"]
    hojas_encontradas = []
    base_url = "https://medprev-vacunas-invernal.streamlit.app"

    for sheet_id_item in ids_a_revisar:
        try:
            sp_item = client.open_by_key(sheet_id_item)
            for ws in sp_item.worksheets():
                titulo_w = ws.title
                if titulo_w not in ["CENSO NOMINAL", "CENSO", "Influenza", "COVID"]:
                    try:
                        val_au4 = ws.acell("AU4").value
                    except Exception:
                        val_au4 = ""
                    try:
                        link_form_leido = ws.acell("AU6").value
                    except Exception:
                        link_form_leido = ""
                    try:
                        link_op_leido = ws.acell("AU7").value
                    except Exception:
                        link_op_leido = ""
                    try:
                        unidad_leida = ws.acell("D9").value
                    except Exception:
                        unidad_leida = ""
                    try:
                        fecha_leida_str = ws.acell("AB9").value
                    except Exception:
                        fecha_leida_str = ""

                    siglas_h = "20N" if "20N_" in titulo_w or sheet_id_item == "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE" else "GEN"

                    titulo_upper = titulo_w.upper()
                    if "EXTRA" in titulo_upper:
                        tipo_letra_h = "E"
                        jornada_texto = "Extramuros E"
                    elif "INTRA" in titulo_upper:
                        tipo_letra_h = "I"
                        jornada_texto = "Intramuros I"
                    elif "MOVIL" in titulo_upper or "MÓVIL" in titulo_upper:
                        tipo_letra_h = "M"
                        jornada_texto = "Brigada Móvil M"
                    else:
                        tipo_letra_h = "I"
                        jornada_texto = "Intramuros I"

                    fecha_obj = datetime.date.today()
                    if fecha_leida_str:
                        try:
                            fecha_obj = datetime.datetime.strptime(fecha_leida_str.strip(), "%d/%m/%Y").date()
                        except Exception:
                            pass

                    if not unidad_leida:
                        unidad_leida = "CMN 20 DE NOVIEMBRE" if siglas_h == "20N" else "Unidad Médica"

                    if not link_form_leido or not link_form_leido.startswith("http"):
                        ruta_form = "registro_20_noviembre" if siglas_h == "20N" else "formulario"
                        link_form_leido = f"{base_url}/{ruta_form}?unidad={siglas_h}&jornada={tipo_letra_h}"

                    if not link_op_leido or not link_op_leido.startswith("http"):
                        link_op_leido = f"{base_url}/consulta_censia?hoja_activa={urllib.parse.quote(titulo_w)}"

                    hojas_encontradas.append({
                        "nombre": titulo_w,
                        "gid": str(ws.id),
                        "unidad": unidad_leida,
                        "siglas_unidad": siglas_h,
                        "tipo_jornada": jornada_texto,
                        "tipo_jornada_letra": tipo_letra_h,
                        "responsable": "PERSONAL OPERATIVO",
                        "correo": val_au4.strip().lower() if val_au4 else "No asignado",
                        "fecha": fecha_obj,
                        "sheet_id": sheet_id_item,
                        "link_formulario": link_form_leido,
                        "link_operativo": link_op_leido,
                    })
        except Exception:
            pass

    return hojas_encontradas


def sincronizar_historial_universal(force_refresh=False):
    """Escanea los libros maestros en Google Sheets y devuelve las jornadas activas.
    Usa caché temporal para reducir el tiempo de carga en la interfaz.
    """
    try:
        if force_refresh:
            _sincronizar_historial_universal_cache.clear()
        hojas_encontradas = _sincronizar_historial_universal_cache()
        return hojas_encontradas, None
    except Exception as e:
        return [], str(e)


def generar_imagen_qr(link):
    """Genera los bytes de una imagen QR a partir de un enlace."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#611232", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
