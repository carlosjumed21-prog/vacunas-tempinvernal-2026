import gspread
import urllib.parse
from utils.sheets_20_nov import obtener_cliente_gspread

# ID de la hoja de cálculo exclusiva para el CMN 20 de Noviembre
SHEET_ID_20_NOV = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"

def autorizar_y_crear_jornadas_20_nov(siglas_unidad, unidad_sel, jornada_sel, tipo_jornada_letra, tipo_jornada_texto, config_jornadas_activas):
    """
    Crea las dos pestañas correspondientes (_NOMINAL y _CENSO) en la hoja de Google Sheets 
    exclusiva del CMN 20 de Noviembre, insertándolas al final de las ya existentes, 
    y mapea los metadatos y enlaces idéntico a admin_utils.py.
    """
    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(SHEET_ID_20_NOV)
    
    hojas_creadas = []
    base_url = "https://medprev-vacunas-invernal.streamlit.app"
    
    for j_conf in config_jornadas_activas:
        fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
        fecha_formato_oficial = j_conf["fecha"].strftime("%d/%m/%Y")
        fecha_url_str = j_conf["fecha"].strftime("%Y-%m-%d")
        
        resp_encoded = urllib.parse.quote(j_conf["responsable"])
        js_param = f"&js={j_conf['sufijo_qr']}" if j_conf["sufijo_qr"] else ""
        ruta_formulario = "registro_20_noviembre" if siglas_unidad == "20N" else "formulario"
        
        link_paciente = f"{base_url}/{ruta_formulario}?unidad={siglas_unidad}&jornada={tipo_jornada_letra}&fecha={fecha_url_str}&resp={resp_encoded}{js_param}"
        
        # Nombres oficiales de las dos hojas requeridas para el 20 de Noviembre
        nombre_hoja_nominal = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_NOMINAL"
        nombre_hoja_censo = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_CENSO"
        
        link_operativo = f"{base_url}/consulta_censia?hoja_activa={urllib.parse.quote(nombre_hoja_nominal)}"

        url_qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link_paciente)}"
        formula_imagen_qr = f'=IMAGE("{url_qr_api}")'
        
        try:
            # Obtenemos el número total de hojas actuales para calcular el índice final
            total_hojas = len(spreadsheet.worksheets())
            
            # --- 1. CREACIÓN DE LA HOJA NOMINAL ---
            try:
                copia_1 = spreadsheet.worksheet(nombre_hoja_nominal)
            except gspread.exceptions.WorksheetNotFound:
                try:
                    plantilla_1 = spreadsheet.worksheet("CENSO NOMINAL")
                    copia_1 = spreadsheet.duplicate_sheet(
                        plantilla_1.id, 
                        insert_sheet_index=total_hojas, 
                        new_sheet_name=nombre_hoja_nominal
                    )
                except Exception:
                    copia_1 = spreadsheet.add_worksheet(title=nombre_hoja_nominal, rows=1000, cols=35, index=total_hojas)

            # Recalculamos el total de hojas
            total_hojas = len(spreadsheet.worksheets())

            # --- 2. CREACIÓN DE LA HOJA DE CENSO TABULAR ---
            try:
                spreadsheet.worksheet(nombre_hoja_censo)
            except gspread.exceptions.WorksheetNotFound:
                try:
                    plantilla_2 = spreadsheet.worksheet("CENSO")
                    spreadsheet.duplicate_sheet(
                        plantilla_2.id, 
                        insert_sheet_index=total_hojas, 
                        new_sheet_name=nombre_hoja_censo
                    )
                except Exception:
                    spreadsheet.add_worksheet(title=nombre_hoja_censo, rows=1000, cols=35, index=total_hojas)

            # Actualizar datos de cabecera y celdas de mapeo (AU4, AU6, AU7, AU8) en la hoja nominal
            try:
                copia_1.update_acell("D7", "CDMX")
                copia_1.update_acell("M7", "ISSSTE")
                copia_1.update_acell("T7", "Delegación Sur")
                copia_1.update_acell("AB7", "CDMX")
                copia_1.update_acell("D8", "CDMX")
                copia_1.update_acell("D9", unidad_sel)
                copia_1.update_acell("M9", "")
                copia_1.update_acell("S9", "")
                copia_1.update_acell("AB9", fecha_formato_oficial)
                copia_1.update_acell("E10", j_conf["responsable"])
                
                # Mapeo exacto de enlaces para que la sincronización universal los lea perfectamente
                copia_1.update(values=[[j_conf["correo"]]], range_name="AU4")
                copia_1.update(values=[[link_paciente]], range_name="AU6")
                copia_1.update(values=[[link_operativo]], range_name="AU7")
                copia_1.update(values=[[formula_imagen_qr]], range_name="AU8", value_input_option='USER_ENTERED')
            except Exception:
                pass

            gid_nueva = copia_1.id
            
            hojas_creadas.append({
                "nombre": nombre_hoja_nominal,
                "sheet_id": SHEET_ID_20_NOV,
                "gid": str(gid_nueva),
                "unidad": unidad_sel,
                "siglas_unidad": siglas_unidad,
                "tipo_jornada": jornada_sel,
                "tipo_jornada_letra": tipo_jornada_letra,
                "responsable": j_conf["responsable"],
                "correo": j_conf["correo"],
                "fecha": j_conf["fecha"],
                "link_formulario": link_paciente,
                "link_operativo": link_operativo
            })
            
        except Exception as e:
            return [], str(e)
            
    return hojas_creadas, None
