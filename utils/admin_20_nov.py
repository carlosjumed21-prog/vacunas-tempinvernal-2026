# utils/admin_20_nov.py
import gspread
import urllib.parse
from utils.sheets_20_nov import obtener_cliente_gspread

# ID de la hoja de cálculo exclusiva para el CMN 20 de Noviembre
SHEET_ID_20_NOV = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"


def autorizar_y_crear_jornadas_20_nov(
    siglas_unidad, unidad_sel, jornada_sel, tipo_jornada_letra, tipo_jornada_texto, config_jornadas_activas
):
    """
    Crea las dos pestañas del CMN 20 de Noviembre (_NOMINAL y _CENSO),
    las inserta al final del libro y llena metadatos y enlaces en la NOMINAL.
    Retorna: (lista_de_hojas_creadas, error)
    """
    try:
        client = obtener_cliente_gspread()
        spreadsheet = client.open_by_key(SHEET_ID_20_NOV)
    except Exception as e:
        return [], str(e)

    hojas_creadas = []
    base_url = "https://medprev-vacunas-invernal.streamlit.app"

    for j_conf in config_jornadas_activas:
        fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
        fecha_formato_oficial = j_conf["fecha"].strftime("%d/%m/%Y")
        fecha_url_str = j_conf["fecha"].strftime("%Y-%m-%d")

        resp_encoded = urllib.parse.quote(j_conf["responsable"])
        js_param = f"&js={j_conf['sufijo_qr']}" if j_conf["sufijo_qr"] else ""

        link_paciente = (
            f"{base_url}/registro_20_noviembre?unidad={siglas_unidad}"
            f"&jornada={tipo_jornada_letra}&fecha={fecha_url_str}&resp={resp_encoded}{js_param}"
        )

        # Nombres oficiales de las dos hojas: SIGLA_[INTRA|EXTRA][_JSn]_DDMMAA_[NOMINAL|CENSO]
        base_nombre = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}"
        nombre_hoja_nominal = f"{base_nombre}_NOMINAL"
        nombre_hoja_censo = f"{base_nombre}_CENSO"

        link_operativo = f"{base_url}/consulta_censia?hoja_activa={urllib.parse.quote(nombre_hoja_nominal)}"

        url_qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link_paciente)}"
        formula_imagen_qr = f'=IMAGE("{url_qr_api}")'

        try:
            total_hojas = len(spreadsheet.worksheets())

            # --- 1. Hoja NOMINAL ---
            try:
                copia_1 = spreadsheet.worksheet(nombre_hoja_nominal)
            except gspread.exceptions.WorksheetNotFound:
                try:
                    plantilla_1 = spreadsheet.worksheet("NOMINAL")
                except gspread.exceptions.WorksheetNotFound:
                    try:
                        plantilla_1 = spreadsheet.worksheet("CENSO NOMINAL")
                    except gspread.exceptions.WorksheetNotFound:
                        plantilla_1 = None

                if plantilla_1 is not None:
                    copia_1 = spreadsheet.duplicate_sheet(
                        plantilla_1.id,
                        insert_sheet_index=total_hojas,
                        new_sheet_name=nombre_hoja_nominal,
                    )
                else:
                    copia_1 = spreadsheet.add_worksheet(
                        title=nombre_hoja_nominal, rows=1000, cols=60, index=total_hojas
                    )

            total_hojas = len(spreadsheet.worksheets())

            # --- 2. Hoja CENSO ---
            try:
                spreadsheet.worksheet(nombre_hoja_censo)
            except gspread.exceptions.WorksheetNotFound:
                try:
                    plantilla_2 = spreadsheet.worksheet("CENSO")
                    spreadsheet.duplicate_sheet(
                        plantilla_2.id,
                        insert_sheet_index=total_hojas,
                        new_sheet_name=nombre_hoja_censo,
                    )
                except gspread.exceptions.WorksheetNotFound:
                    spreadsheet.add_worksheet(
                        title=nombre_hoja_censo, rows=1000, cols=60, index=total_hojas
                    )

            # --- 3. Metadatos y enlaces en la NOMINAL ---
            try:
                copia_1.update_acell("D7", "CDMX")
                copia_1.update_acell("M7", "ISSSTE")
                copia_1.update_acell("T7", "Delegación Sur")
                copia_1.update_acell("AB7", "CDMX")
                copia_1.update_acell("D8", "CDMX")
                copia_1.update_acell("D9", unidad_sel)
                copia_1.update_acell("AB9", fecha_formato_oficial)
                copia_1.update_acell("E10", j_conf["responsable"])

                # La sincronización universal lee estas celdas
                copia_1.update(values=[[j_conf["correo"]]], range_name="AU4")
                copia_1.update(values=[[link_paciente]], range_name="AU6")
                copia_1.update(values=[[link_operativo]], range_name="AU7")
                copia_1.update(values=[[formula_imagen_qr]], range_name="AU8", value_input_option="USER_ENTERED")
            except Exception:
                pass

            hojas_creadas.append({
                "nombre": nombre_hoja_nominal,
                "sheet_id": SHEET_ID_20_NOV,
                "gid": str(copia_1.id),
                "unidad": unidad_sel,
                "siglas_unidad": siglas_unidad,
                "tipo_jornada": jornada_sel,
                "tipo_jornada_letra": tipo_jornada_letra,
                "responsable": j_conf["responsable"],
                "correo": j_conf["correo"],
                "fecha": j_conf["fecha"],
                "link_formulario": link_paciente,
                "link_operativo": link_operativo,
            })

        except Exception as e:
            return [], str(e)

    return hojas_creadas, None
