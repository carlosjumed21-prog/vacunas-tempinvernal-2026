import datetime
import random
import unicodedata
import streamlit as st

estados_curp = {
    "AGUASCALIENTES": "AS", "BAJA CALIFORNIA": "BC", "BAJA CALIFORNIA SUR": "BS",
    "CAMPECHE": "CC", "CHIAPAS": "CS", "CHIHUAHUA": "CH", "CIUDAD DE MÉXICO": "DF",
    "COAHUILA": "CL", "COLIMA": "CM", "DURANGO": "DG", "ESTADO DE MÉXICO": "MC",
    "GUANAJUATO": "GT", "GUERRERO": "GR", "HIDALGO": "HG", "JALISCO": "JC",
    "MICHOACÁN": "MN", "MORELOS": "MS", "NAYARIT": "NT", "NUEVO LEÓN": "NL",
    "OAXACA": "OC", "PUEBLA": "PL", "QUERÉTARO": "QT", "QUINTANA ROO": "QR",
    "SAN LUIS POTOSÍ": "SP", "SINALOA": "SL", "SONORA": "SR", "TABASCO": "TC",
    "TAMAULIPAS": "TS", "TLAXCALA": "TL", "VERACRUZ": "VZ", "YUCATÁN": "YN",
    "ZACATECAS": "ZS",
}

estados_mexico = [
    "SELECCIONE UN ESTADO", "AGUASCALIENTES", "BAJA CALIFORNIA", "BAJA CALIFORNIA SUR",
    "CAMPECHE", "CHIAPAS", "CHIHUAHUA", "CIUDAD DE MÉXICO", "COAHUILA", "COLIMA",
    "DURANGO", "ESTADO DE MÉXICO", "GUANAJUATO", "GUERRERO", "HIDALGO", "JALISCO",
    "MICHOACÁN", "MORELOS", "NAYARIT", "NUEVO LEÓN", "OAXACA", "PUEBLA",
    "QUERÉTARO", "QUINTANA ROO", "SAN LUIS POTOSÍ", "SINALOA", "SONORA",
    "TABASCO", "TAMAULIPAS", "TLAXCALA", "VERACRUZ", "YUCATÁN", "ZACATECAS",
]

lista_ocupaciones = [
    "SELECCIONE UNA OPCIÓN", "NO APLICA",
    "PERSONAL DE SALUD (INCLUYE: PARAMÉDICO / PERSONAL SUPERVISOR Y ADMINISTRATIVO EN ÁREAS CLÍNICAS Y FARMACIAS)",
    "ESTUDIANTE (PREESCOLAR, PRIMARIA, SECUNDARIA, BACHILLERATO/PREPARATORIA)",
    "JUBILADO/A", "MAESTRO/A", "ADMINISTRATIVO/A", "TRABAJO EN GUARDERÍA",
    "RESIDENTES Y PERSONAL DE CENTROS DE ASISTENCIA SOCIAL (CENTROS DE RECLUSIÓN Y/O READAPTACIÓN SOCIAL)",
    "PERSONAL DE GUARDERÍAS, CENDI O ESTANCIAS INFANTILES", "PERSONAL MILITAR",
    "TRABAJADORES ACTIVOS DE PLATAFORMAS MARÍTIMAS Y REFINERÍAS (PEMEX)", "OTRAS PROFESIONES"
]

meses_dict = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, 
    "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, 
    "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
}


def calcular_edad_detallada(fecha_nac, fecha_ref):
    if not fecha_nac or not fecha_ref or fecha_nac > fecha_ref:
        return 0, 0, 0
    anos = fecha_ref.year - fecha_nac.year
    meses = fecha_ref.month - fecha_nac.month
    dias = fecha_ref.day - fecha_nac.day
    if dias < 0:
        meses -= 1
        mes_anterior = fecha_ref.month - 1 if fecha_ref.month > 1 else 12
        anio_anterior = fecha_ref.year if fecha_ref.month > 1 else fecha_ref.year - 1
        dias_mes_anterior = (datetime.date(anio_anterior, mes_anterior + 1, 1) - datetime.timedelta(days=1)).day
        dias += dias_mes_anterior
    if meses < 0:
        anos -= 1
        meses += 12
    return max(0, anos), max(0, meses), max(0, dias)


def limpiar_texto(texto):
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).upper().strip()


def obtener_primera_vocal_interna(palabra):
    for letra in palabra[1:]:
        if letra in "AEIOU":
            return letra
    return "X"


def obtener_primera_consonante_interna(palabra):
    for letra in palabra[1:]:
        if letra in "BCDFGHJKLMNPQRSTVWXYZ":
            return letra
    return "X"


def generar_curp_algoritmica(paterno, materno, nombres, fecha_nac, sexo, est_nac, digitos_extra=""):
    p = limpiar_texto(paterno)
    m = limpiar_texto(materno) if materno else ""
    n = limpiar_texto(nombres)
    
    if not p or not n or not fecha_nac or sexo == "SELECCIONE UNA OPCIÓN" or est_nac == "SELECCIONE UN ESTADO":
        return "COMPLETA DATOS, SEXO Y ESTADO"
        
    nombres_lista = n.split()
    primer_nombre = nombres_lista[0] if nombres_lista else "X"
    if len(nombres_lista) > 1 and primer_nombre in ["JOSE", "MARIA", "MA.", "J."]:
        primer_nombre = nombres_lista[1]
        
    c1 = p[0] if p else "X"
    c2 = obtener_primera_vocal_interna(p)
    c3 = m[0] if m else "X"
    c4 = primer_nombre[0] if primer_nombre else "X"
    
    yy = str(fecha_nac.year)[-2:]
    mm = str(fecha_nac.month).zfill(2)
    dd = str(fecha_nac.day).zfill(2)
    fec_part = f"{yy}{mm}{dd}"
    
    sexo_part = "H" if sexo == "HOMBRE" else ("M" if sexo == "MUJER" else "X")
    est_part = estados_curp.get(est_nac, "NE")
    
    c14 = obtener_primera_consonante_interna(p)
    c15 = obtener_primera_consonante_interna(m) if m else "X"
    c16 = obtener_primera_consonante_interna(primer_nombre)
    
    curp_16 = f"{c1}{c2}{c3}{c4}{fec_part}{sexo_part}{est_part}{c14}{c15}{c16}"
    
    extra_limpio = limpiar_texto(digitos_extra)
    sufijo = extra_limpio[:2] if len(extra_limpio) >= 2 else "00"
    
    return f"{curp_16}{sufijo}"


@st.cache_data(ttl=600)
def obtener_recomendaciones_sheets(biologico):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        if "gcp_service_account" in st.secrets:
            credentials = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scopes
            )
            gc = gspread.authorize(credentials)
        else:
            gc = gspread.oauth()
        sh = gc.open_by_key("1jiJhSq4RQytqax7Gh1B9k8ZSglmsLroAvrCv54lEZ_k")
        nombre_hoja = "COVID" if biologico and biologico.upper() in ["COVID-19", "COVID"] else "Influenza"
        worksheet = sh.worksheet(nombre_hoja)
        return worksheet.get_all_records()
    except Exception:
        return []


def determinar_grupo_desde_sheets(biologico, edad_meses, edad_anos, gestante, ocupacion, comorbilidades_activas):
    biologico_a_consultar = "Influenza" if biologico and biologico in ["INFLUENZA", "AMBAS"] else "COVID"
    filas_sheets = obtener_recomendaciones_sheets(biologico_a_consultar)

    if not filas_sheets:
        return determinar_grupo_sugerido_fallback(biologico, edad_meses, edad_anos, gestante, ocupacion, comorbilidades_activas)

    for fila in filas_sheets:
        grupo_blanco = str(fila.get("Grupos blancos de la intervención", ""))
        categoria = str(fila.get("Categoria", ""))
        gb_lower = grupo_blanco.lower()

        if gestante == "SÍ" and ("gestante" in gb_lower or "embarazo" in gb_lower):
            return f"{grupo_blanco} ({categoria})"

        if "meses" in gb_lower:
            if "6 a 18 meses" in gb_lower and 6 <= edad_meses <= 18:
                return f"{grupo_blanco} ({categoria})"
            elif "19 a 59 meses" in gb_lower and 19 <= edad_meses <= 59:
                return f"{grupo_blanco} ({categoria})"
            elif "6 a 59 meses" in gb_lower and 6 <= edad_meses <= 59:
                return f"{grupo_blanco} ({categoria})"

        if "años" in gb_lower or "mas" in gb_lower or "y mas" in gb_lower:
            if ("60" in gb_lower or "mas" in gb_lower) and edad_anos >= 60 and "comorbilidades" not in gb_lower:
                return f"{grupo_blanco} ({categoria})"

        if "personal de salud" in gb_lower and ("PERSONAL DE SALUD" in ocupacion.upper()):
            return f"{grupo_blanco} ({categoria})"

        if comorbilidades_activas and "comorbilidades" in gb_lower:
            if "5 a 8 años" in gb_lower and 5 <= edad_anos <= 8:
                return f"{grupo_blanco} ({categoria})"
            elif "9 a 59 años" in gb_lower and 9 <= edad_anos <= 59:
                return f"{grupo_blanco} ({categoria})"
            elif "6 meses a 59 años" in gb_lower and 0.5 <= edad_anos <= 59:
                return f"{grupo_blanco} ({categoria})"

    return determinar_grupo_sugerido_fallback(biologico, edad_meses, edad_anos, gestante, ocupacion, comorbilidades_activas)


def determinar_grupo_sugerido_fallback(vacuna_interes, edad_total_meses, calc_anos, personas_gestantes, ocupacion, tiene_comorbilidades):
    is_personal_salud = "PERSONAL DE SALUD" in ocupacion.upper()
    is_colectivo_riesgo = is_personal_salud or ocupacion in [
        "PERSONAL DE GUARDERÍAS, CENDI O ESTANCIAS INFANTILES",
        "RESIDENTES Y PERSONAL DE CENTROS DE ASISTENCIA SOCIAL (CENTROS DE RECLUSIÓN Y/O READAPTACIÓN SOCIAL)",
        "PERSONAL MILITAR", "TRABAJADORES ACTIVOS DE PLATAFORMAS MARÍTIMAS Y REFINERÍAS (PEMEX)",
    ]

    if 6 <= edad_total_meses <= 18:
        rango_grupo_blanco = "6 a 18 meses"
    elif 19 <= edad_total_meses <= 59:
        rango_grupo_blanco = "19 a 59 meses"
    elif calc_anos >= 60:
        rango_grupo_blanco = "60 años y mas"
    else:
        rango_grupo_blanco = "Población General"

    if vacuna_interes in ["COVID-19", "AMBAS"]:
        if 6 <= edad_total_meses <= 59:
            return "6 A 59 MESES (VACUNACIÓN RUTINARIA / PRIMARIO) [Población Objetivo]"
        elif personas_gestantes == "SÍ":
            return "PERSONAS GESTANTES [Población de Riesgo]"
        elif calc_anos >= 60:
            return f"{rango_grupo_blanco} (Población Objetivo)"
        elif is_personal_salud:
            return "PERSONAL DE SALUD [Población de Riesgo]"
        elif tiene_comorbilidades:
            return "COMORBILIDADES DE RIESGO (6 MESES A 59 AÑOS) [Población de Riesgo]"
        else:
            return f"{rango_grupo_blanco} (Población Objetivo)"
    else:
        if 6 <= edad_total_meses <= 59:
            return "POBLACIÓN PEDIÁTRICA (6 A 59 MESES) [Población Objetivo]"
        elif personas_gestantes == "SÍ":
            return "PERSONAS GESTANTES [Población de Riesgo]"
        elif is_personal_salud:
            return "PERSONAL DE SALUD [Población de Riesgo]"
        elif is_colectivo_riesgo:
            return f"{ocupacion} [Población de Riesgo]"
        elif calc_anos >= 60:
            return f"{rango_grupo_blanco} (Población Objetivo)"
        elif tiene_comorbilidades:
            return "POBLACIÓN CON COMORBILIDADES (5 A 59 AÑOS) [Población de Riesgo]"
        else:
            return f"{rango_grupo_blanco} (Población Objetivo)"


def generar_folio_personalizado(val_fecha_app, modalidad, sigla_url):
    """
    Formato solicitado: Fecha YYYYMMDD + INT/EXT + 3 letras de unidad + 4 dígitos consecutivos (iniciando en 0001)
    Ejemplo: 20261011INT20N0001
    """
    fecha_str = val_fecha_app.strftime("%Y%m%d")
    mod_str = "INT" if modalidad.upper() == "INTRAMUROS" else "EXT"
    siglas_3 = sigla_url[:3].upper().ljust(3, 'X')
    
    try:
        registros = obtener_registros_existentes_sheets(sigla_url, "", "I", val_fecha_app)
        consecutivo_num = len(registros) + 1
    except:
        consecutivo_num = st.session_state.get("contador_folio_consecutivo", 1)
        st.session_state["contador_folio_consecutivo"] = consecutivo_num + 1
        
    secuencial_str = str(consecutivo_num).zfill(4)
    return f"{fecha_str}{mod_str}{siglas_3}{secuencial_str}"


@st.cache_data(ttl=30)
def obtener_registros_existentes_sheets(sigla_url, sufijo_js, tipo_jornada, val_fecha_app):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        if "gcp_service_account" in st.secrets:
            credentials = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scopes
            )
            gc = gspread.authorize(credentials)
        else:
            gc = gspread.oauth()
            
        sh = gc.open_by_key("1jiJhSq4RQytqax7Gh1B9k8ZSglmsLroAvrCv54lEZ_k")
        nombre_tabla = f"Censo_{sigla_url}_{val_fecha_app.strftime('%Y%m%d')}"
        if sufijo_js:
            nombre_tabla += f"_{sufijo_js}"
            
        worksheet = sh.worksheet(nombre_tabla)
        return worksheet.get_all_records()
    except Exception:
        return []


def verificar_curp_duplicada(curp_actual, sigla_url, sufijo_js, tipo_jornada, val_fecha_app):
    if not curp_actual or len(curp_actual) < 10 or "COMPLETA" in curp_actual:
        return False, None
        
    prefijo_actual = curp_actual[:10].upper()
    registros = obtener_registros_existentes_sheets(sigla_url, sufijo_js, tipo_jornada, val_fecha_app)
    
    for reg in registros:
        curp_registrada = str(reg.get("CURP", reg.get("curp_con_nacimiento", ""))).upper()
        if curp_registrada and curp_registrada[:10] == prefijo_actual:
            folio_existente = reg.get("Folio", reg.get("folio", "DESCONOCIDO"))
            return True, folio_existente
            
    return False, None
