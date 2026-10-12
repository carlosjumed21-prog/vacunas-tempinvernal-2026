import gspread
from utils.sheets import obtener_cliente_gspread

# ID de la hoja de cálculo exclusiva para el CMN 20 de Noviembre
SHEET_ID_20_NOV = "1PQhYZeGROAiXXtsRexyifuDJ5nOnADaTJnKHKCeV7gE"

def autorizar_y_crear_jornadas_20_nov(siglas_unidad, unidad_sel, jornada_sel, tipo_jornada_letra, tipo_jornada_texto, config_jornadas_activas):
    """
    Crea las pestañas correspondientes en la hoja de Google Sheets exclusiva del CMN 20 de Noviembre,
    asegurando la estructura de censo nominal y los encabezados institucionales correctos.
    """
    client = obtener_cliente_gspread()
    spreadsheet = client.open_by_key(SHEET_ID_20_NOV)
    
    hojas_creadas = []
    
    for j_conf in config_jornadas_activas:
        fecha_str_val = j_conf["fecha"].strftime("%d%m%y")
        # Nomenclatura exacta requerida para las hojas del 20 de Noviembre
        nombre_hoja = f"{siglas_unidad}_{tipo_jornada_texto}{j_conf['sufijo_hoja']}_{fecha_str_val}_NOMINAL"
        
        try:
            # Verificar si la pestaña ya existe para evitar duplicados
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
            
            # Intentar duplicar la pestaña base 'CENSO' si existe en la hoja de destino,
            # de lo contrario, crear una nueva hoja con los encabezados institucionales del 20 de Noviembre.
            try:
                plantilla = spreadsheet.worksheet("CENSO")
                nueva_hoja = spreadsheet.duplicate_sheet(plantilla.id, new_sheet_name=nombre_hoja)
            except Exception:
                nueva_hoja = spreadsheet.add_worksheet(title=nombre_hoja, rows=1000, cols=35)
                
                # Encabezados institucionales y de cabecera oficiales del CMN 20 de Noviembre
                encabezados_institucionales = [
                    ["Subsecretaría de Políticas de Salud y Bienestar Poblacional"],
                    ["Centro Nacional para la Salud de la Infancia y la Adolescencia"],
                    ["Programa de Vacunación Universal"],
                    ["Censo Nominal, vacunación para la temporada invernal 2026-2027"],
                    ["Entidad Federativa:", "CDMX", "Institución", "ISSSTE", "Jurisdicción / Delegación:", "Delegación Sur", "Municipio:", "CDMX"],
                    ["Localidad:", "CDMX"],
                    [f"Unidad de Salud: ,{unidad_sel},AGEB,,Sector:,,Fecha (dd/mm/aaaa):,{j_conf['fecha'].strftime('%d/%m/%Y')}"],
                    [f"Nombre del responsable de vacunación,{j_conf['responsable']}"],
                    [],
                    # Fila de columnas del censo nominal
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
