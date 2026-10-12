
import gspread
from utils.sheets_20_nov import obtener_cliente_gspread
from config import GOOGLE_SHEET_ID

def autorizar_y_crear_jornadas_20_nov(siglas_unidad, unidad_sel, jornada_sel, tipo_jornada_letra, tipo_jornada_texto, config_jornadas_activas):
    """
    Crea las pestañas correspondientes en el Google Sheets maestro de forma específica 
    para el CMN 20 de Noviembre, asegurando la estructura dual de censo nominal.
    """
    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    
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
                    "sheet_id": GOOGLE_SHEET_ID,
                    "gid": gid,
                    "unidad": unidad_sel,
                    "tipo_jornada": jornada_sel,
                    "correo": j_conf["correo"]
                })
                continue
            except gspread.exceptions.WorksheetNotFound:
                pass
            
            # Duplicar una plantilla base o crear una nueva hoja con los encabezados del 20 de Noviembre
            # Si tienes una hoja plantilla llamada 'PLANTILLA_20N' en tu Google Sheet:
            try:
                plantilla = spreadsheet.worksheet("PLANTILLA_20N")
                nueva_hoja = spreadsheet.duplicate_sheet(plantilla.id, new_sheet_name=nombre_hoja)
            except Exception:
                # Si no existe plantilla, se crea una nueva en blanco y se configuran los encabezados institucionales
                nueva_hoja = spreadsheet.add_worksheet(title=nombre_hoja, rows=1000, cols=35)
                
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
                "sheet_id": GOOGLE_SHEET_ID,
                "gid": gid_nueva,
                "unidad": unidad_sel,
                "tipo_jornada": jornada_sel,
                "correo": j_conf["correo"]
            })
            
        except Exception as e:
            return [], str(e)
            
    return hojas_creadas, None
