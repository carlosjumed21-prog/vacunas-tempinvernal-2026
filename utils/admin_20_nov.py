import gspread
from utils.sheets_20_nov import obtener_cliente_gspread

# ID de la hoja de cálculo exclusiva para el CMN 20 de Noviembre
SHEET_ID_20_NOV = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"

def autorizar_y_crear_jornadas_20_nov(siglas_unidad, unidad_sel, jornada_sel, tipo_jornada_letra, tipo_jornada_texto, config_jornadas_activas):
    """
    Crea las pestañas correspondientes en la hoja de Google Sheets exclusiva del CMN 20 de Noviembre,
    insertándolas al inicio (delante de las hojas principales) para mantener el orden,
    y asegurando la estructura de censo nominal con los encabezados institucionales.
    """
    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(SHEET_ID_20_NOV)
    
    hojas_creadas = []
    
    for j_conf in config_jornadas_activas:
        fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
        nombre_hoja = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_NOMINAL"
        
        try:
            # Verificar si ya existe para evitar duplicados exactos
            try:
                ws_existente = spreadsheet.worksheet(nombre_hoja)
                gid = ws_existente.id
                hojas_creadas.append({
                    "nombre": nombre_hoja,
                    "sheet_id": SHEET_ID_20_NOV,
                    "gid": gid,
                    "unidad": unidad_sel,
                    "tipo_jornada": jornada_sel,
                    "correo": j_conf["correo"]
                })
                continue
            except gspread.exceptions.WorksheetNotFound:
                pass
            
            # Duplicar plantilla base o crear nueva hoja insertándola al principio (index=0)
            try:
                plantilla = spreadsheet.worksheet("CENSO")
                nueva_hoja = spreadsheet.duplicate_sheet(plantilla.id, new_sheet_name=nombre_hoja, insert_sheet_index=0)
            except Exception:
                # Si no existe la plantilla CENSO, crea una nueva hoja en la posición 0 (al frente)
                nueva_hoja = spreadsheet.add_worksheet(title=nombre_hoja, rows=1000, cols=35, index=0)
                
                # Encabezados institucionales y de cabecera específicos para el 20 de Noviembre
                encabezados_institucionales = [
                    ["SUBDIRECCIÓN MÉDICA - CENTRO MÉDICO NACIONAL '20 DE NOVIEMBRE'"],
                    [f"JORNADA: {jornada_sel} | RESPONSABLE: {j_conf['responsable']}"],
                    [f"FECHA DE APLICACIÓN: {j_conf['fecha'].strftime('%d/%m/%Y')} | DIRECCIÓN: {j_conf['direccion']}"],
                    [],
                    ["No.", "FOLIO", "RFC", "DERECHOHABIENCIA", "TIPO DH", "¿TRABAJA EN CMN 20N?", "NO. TRABAJADOR", "PERSONAL SALUD", 
                     "CATEGORÍA", "SERVICIO", "COORDINACIÓN", "TURNO", "PATERNO", "MATERNO", "NOMBRE", 
                     "ESTADO NAC.", "MUNICIPIO NAC.", "DÍA NAC.", "MES NAC.", "AÑO NAC.", "AÑOS", "MESES", 
                     "SEXO", "EMBARAZO", "CURP", "CALLE", "NÚMERO", "COLONIA", "CORREO", "VACUNA INTERÉS", "GRUPO OBJETIVO", "FECHA REGISTRO"]
                ]
                nueva_hoja.append_rows(encabezados_institucionales)

            gid_nueva = nueva_hoja.id
            
            hojas_creadas.append({
                "nombre": nombre_hoja,
                "sheet_id": SHEET_ID_20_NOV,
                "gid": gid_nueva,
                "unidad": unidad_sel,
                "tipo_jornada": jornada_sel,
                "correo": j_conf["correo"]
            })
            
        except Exception as e:
            return [], str(e)
            
    return hojas_creadas, None
