import gspread
from utils.sheets_20_nov import obtener_cliente_gspread

# ID de la hoja de cálculo exclusiva para el CMN 20 de Noviembre
SHEET_ID_20_NOV = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"

def autorizar_y_crear_jornadas_20_nov(siglas_unidad, unidad_sel, jornada_sel, tipo_jornada_letra, tipo_jornada_texto, config_jornadas_activas):
    """
    Crea las dos pestañas correspondientes (_NOMINAL y _CENSO) en la hoja de Google Sheets 
    exclusiva del CMN 20 de Noviembre, insertándolas al inicio para mantener el orden.
    """
    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(SHEET_ID_20_NOV)
    
    hojas_creadas = []
    
    for j_conf in config_jornadas_activas:
        fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
        
        # Nombres oficiales de las dos hojas requeridas para el 20 de Noviembre
        nombre_hoja_nominal = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_NOMINAL"
        nombre_hoja_censo = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_CENSO"
        
        try:
            # --- 1. CREACIÓN DE LA HOJA NOMINAL ---
            try:
                copia_1 = spreadsheet.worksheet(nombre_hoja_nominal)
            except gspread.exceptions.WorksheetNotFound:
                try:
                    plantilla_1 = spreadsheet.worksheet("CENSO NOMINAL")
                    copia_1 = spreadsheet.duplicate_sheet(
                        plantilla_1.id, 
                        insert_sheet_index=0, 
                        new_sheet_name=nombre_hoja_nominal
                    )
                except Exception:
                    copia_1 = spreadsheet.add_worksheet(title=nombre_hoja_nominal, rows=1000, cols=35, index=0)

            # --- 2. CREACIÓN DE LA HOJA DE CENSO TABULAR ---
            try:
                spreadsheet.worksheet(nombre_hoja_censo)
            except gspread.exceptions.WorksheetNotFound:
                try:
                    plantilla_2 = spreadsheet.worksheet("CENSO")
                    spreadsheet.duplicate_sheet(
                        plantilla_2.id, 
                        insert_sheet_index=1, 
                        new_sheet_name=nombre_hoja_censo
                    )
                except Exception:
                    spreadsheet.add_worksheet(title=nombre_hoja_censo, rows=1000, cols=35, index=1)

            # Actualizar datos de cabecera en la hoja nominal activa
            try:
                copia_1.update_acell("D7", "CDMX")
                copia_1.update_acell("M7", "ISSSTE")
                copia_1.update_acell("T7", "Delegación Sur")
                copia_1.update_acell("AB7", "CDMX")
                copia_1.update_acell("D8", "CDMX")
                copia_1.update_acell("D9", unidad_sel)
                copia_1.update_acell("M9", "")
                copia_1.update_acell("S9", "")
                copia_1.update_acell("AB9", j_conf["fecha"].strftime('%d/%m/%Y'))
                copia_1.update_acell("E10", j_conf["responsable"])
            except Exception:
                pass

            gid_nueva = copia_1.id
            
            hojas_creadas.append({
                "nombre": nombre_hoja_nominal,
                "sheet_id": SHEET_ID_20_NOV,
                "gid": gid_nueva,
                "unidad": unidad_sel,
                "tipo_jornada": jornada_sel,
                "correo": j_conf["correo"]
            })
            
        except Exception as e:
            return [], str(e)
            
    return hojas_creadas, None
