import datetime
import unicodedata
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from config import MAPA_SIGLAS_INVERSO, aplicar_configuracion_global
from utils.sheets import guardar_registro_censal_20_nov

aplicar_configuracion_global("Censo Nominal - 20 de Noviembre", "💉")

# --- CARGA DE CATÁLOGOS DESDE LA PESTAÑA ESPECÍFICA 'Hoja 1 LISTAS' ---
@st.cache_data(show_spinner=False)
def cargar_catalogos_excel():
    try:
        # Indicamos explícitamente el nombre de la pestaña exacta
        df = pd.read_excel("assets/lista vac.xlsx", sheet_name="Hoja 1 LISTAS", dtype=str)
        
        def limpiar_columna(serie):
            if serie is not None and not serie.empty:
                return sorted([str(x).strip().upper() for x in serie.dropna().unique() if str(x).strip() and str(x).strip().upper() != "NAN"])
            return []

        # Columna A (Tipo DH), Columna B (Servicio), Columna C (Coordinación), Columna D (Categoría), Columna E (Turno)
        opt_dh = limpiar_columna(df.iloc[:, 0]) if df.shape[1] > 0 else []
        opt_serv = limpiar_columna(df.iloc[:, 1]) if df.shape[1] > 1 else []
        opt_coord = limpiar_columna(df.iloc[:, 2]) if df.shape[1] > 2 else []
        opt_cat = limpiar_columna(df.iloc[:, 3]) if df.shape[1] > 3 else []
        opt_turno = limpiar_columna(df.iloc[:, 4]) if df.shape[1] > 4 else []

        return (
            opt_dh or ["TRABAJADOR ACTIVO", "JUBILADO / PENSIONADO", "FAMILIAR", "OTRO"],
            opt_serv or ["EPIDEMIOLOGÍA", "URGENCIAS", "PEDIATRÍA", "MEDICINA INTERNA", "CIRUGÍA", "OTRO"],
            opt_coord or ["DIRECCIÓN MÉDICA", "SUBDIRECCIÓN", "ENFERMERÍA", "OTRO"],
            opt_cat or ["MÉDICO", "ENFERMERA", "ADMINISTRATIVO", "OTRO"],
            opt_turno or ["MATUTINO", "VESPERTINO", "NOCTURNO", "JORNADA ACUMULADA"]
        )
    except Exception as e:
        # Respaldo por si ocurre algún inconveniente con el archivo
        return (
            ["TRABAJADOR ACTIVO", "JUBILADO / PENSIONADO", "FAMILIAR", "OTRO"],
            ["EPIDEMIOLOGÍA", "URGENCIAS", "PEDIATRÍA", "MEDICINA INTERNA", "CIRUGÍA", "OTRO"],
            ["DIRECCIÓN MÉDICA", "SUBDIRECCIÓN", "ENFERMERÍA", "OTRO"],
            ["MÉDICO", "ENFERMERA", "ADMINISTRATIVO", "OTRO"],
            ["MATUTINO", "VESPERTINO", "NOCTURNO", "JORNADA ACUMULADA"]
        )

opt_tipo_dh, opt_servicio, opt_coordinacion, opt_categoria, opt_turno = cargar_catalogos_excel()

# --- BOTÓN DE RETORNO AL MENÚ PRINCIPAL ---
col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
with col_nav1:
    if st.button("🏠 Volver al Menú Principal", use_container_width=True):
        st.switch_page("app.py")

st.markdown("---")

# --- RECUPERACIÓN DE PARÁMETROS DE URL ---
params = st.query_params
sigla_url = params.get("unidad", "20N").upper()
nombre_base_unidad = MAPA_SIGLAS_INVERSO.get(sigla_url, "CENTRO MÉDICO NACIONAL '20 DE NOVIEMBRE'")
sufijo_js = params.get("js", "")

st.session_state.siglas_unidad = sigla_url
st.session_state.nombre_unidad = (
    f"{nombre_base_unidad} (Brigada {sufijo_js})"
    if sufijo_js
    else nombre_base_unidad
)
st.session_state.tipo_jornada = params.get("jornada", "I")

fecha_url_str = params.get("fecha", datetime.date.today().strftime("%Y-%m-%d"))
try:
    val_fecha_app = datetime.datetime.strptime(fecha_url_str, "%Y-%m-%d").date()
except:
    val_fecha_app = datetime.date.today()

st.markdown(
    """
    <style>
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
        .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
        label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }
        .card-edad { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #611232; font-size: 1.3rem !important; margin-bottom: 15px; }
        .card-curp { background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }
        .card-rfc { background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; }
        input[type="text"] { text-transform: uppercase !important; font-size: 1.1rem !important; }
    </style>
""",
    unsafe_allow_html=True,
)

if "ultimo_paciente_20n" not in st.session_state:
    st.session_state.ultimo_paciente_20n = None


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
        dias_mes_anterior = (
            datetime.date(anio_anterior, mes_anterior + 1, 1)
            - datetime.timedelta(days=1)
        ).day
        dias += dias_mes_anterior
    if meses < 0:
        anos -= 1
        meses += 12
    return max(0, anos), max(0, meses), max(0, dias)


def limpiar_texto(texto):
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
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


estados_curp = {
    "AGUASCALIENTES": "AS", "BAJA CALIFORNIA": "BC", "BAJA CALIFORNIA SUR": "BS",
    "CAMPECHE": "CC", "CHIAPAS": "CS", "CHIHUAHUA": "CH", "CIUDAD DE MÉXICO": "DF",
    "COAHUILA": "CL", "COLIMA": "CM", "DURANGO": "DG", "ESTADO DE MÉXICO": "MC",
    "GUANAJUATO": "GT", "GUERRERO": "GR", "HIDALGO": "HG", "JALISCO": "JC",
    "MICHOACÁN": "MN", "MORELOS": "MS", "NAYARIT": "NT", "NUEVO LEÓN": "NL",
    "OAXACA": "OC", "PUEBLA": "PL", "QUERÉTARO": "QT", "QUINTANA ROO": "QR",
    "SAN LUIS POTOSÍ": "SP", "SINALOA": "SL", "SONORA": "SR", "TABASCO": "TC",
    "TAMAULIPAS": "TS", "TLAXCALA": "TL", "VERACRUZ": "VZ", "YUCATÁN": "YN", "ZACATECAS": "ZS",
}

municipios_por_estado = {
    "CIUDAD DE MÉXICO": [
        "ÁLVARO OBREGÓN", "AZCAPOTZALCO", "BENITO JUÁREZ", "COYOACÁN", "CUAJIMALPA DE MORELOS",
        "CUAUHTÉMOC", "GUSTAVO A. MADERO", "IZTACALCO", "IZTAPALAPA", "LA MAGDALENA CONTRERAS",
        "MIGUEL HIDALGO", "MILPA ALTA", "TÁHUAC", "TLALPAN", "VENUSTIANO CARRANZA", "XOCHIMILCO"
    ],
    "ESTADO DE MÉXICO": [
        "ECATEPEC DE MORELOS", "NEZAHUALCÓYOTL", "NAUCALPAN DE JUÁREZ", "TOLUCA", "TLANEPANTLA DE BAZ",
        "CHIMALHUACÁN", "CUAUTITLÁN IZCALLI", "ATIZAPÁN DE ZARAGOZA", "IXTAPALUCA", "CHICOLOAPAN",
        "METEPEC", "TEXCOCO", "VALLE DE CHALCO SOLIDARIDAD", "ACAMBAY", "ATLACOMULCO", "OTRO"
    ],
    "PUEBLA": [
        "PUEBLA", "TEHUACÁN", "SAN MARTÍN TEXMELUCAN", "ATLIXCO", "SAN PEDRO CHOLULA",
        "SAN ANDRÉS CHOLULA", "TECAMACHALCO", "HUAUCHINANGO", "ZACATLÁN", "TEZIUTLÁN", "OTRO"
    ],
    "HIDALGO": [
        "PACHUCA DE SOTO", "TULA DE ALLENDE", "TULANCINGO DE BRAVO", "TIZAYUCA", "TEPEJI DEL RÍO", "HUEJUTLA DE REYES", "OTRO"
    ],
    "MORELOS": [
        "CUERNAVACA", "JIUTEPEC", "CUAUTLA", "TEMIXCO", "EMILIANO ZAPATA", "YAUTEPEC", "JOJUTLA", "OTRO"
    ],
    "TLAXCALA": [
        "TLAXCALA", "APIZACO", "HUAMANTLA", "CHIAUTEMPAN", "ZACATELCO", "SAN PABLO DEL MONTE", "OTRO"
    ],
    "VERACRUZ": [
        "VERACRUZ", "XALAPA", "COATZACOALCOS", "CÓRDOBA", "POZA RICA DE HIDALGO", "ORIZABA", "MINATITLÁN", "TUXPAN", "OTRO"
    ]
}


def generar_curp_algoritmica(paterno, materno, nombres, fecha_nac, sexo, est_nac, digitos_extra=""):
    p = limpiar_texto(paterno)
    m = limpiar_texto(materno) if materno else ""
    n = limpiar_texto(nombres)
    if not p or not n or not fecha_nac:
        return "COMPLETA DATOS Y FECHA"
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


def generar_rfc_algoritmico(paterno, materno, nombres, fecha_nac):
    p = limpiar_texto(paterno)
    m = limpiar_texto(materno) if materno else ""
    n = limpiar_texto(nombres)
    if not p or not n or not fecha_nac:
        return "COMPLETA DATOS Y FECHA"
    nombres_lista = n.split()
    primer_nombre = nombres_lista[0] if nombres_lista else "X"
    if len(nombres_lista) > 1 and primer_nombre in ["JOSE", "MARIA", "MA.", "J."]:
        primer_nombre = nombres_lista[1]
    c1 = p[0] if p else "X"
    c2 = obtener_primera_vocal_interna(p)
    c3 = m[0] if m and m != "X" else (p[1] if len(p) > 1 else "X")
    c4 = primer_nombre[0] if primer_nombre else "X"
    yy = str(fecha_nac.year)[-2:]
    mm = str(fecha_nac.month).zfill(2)
    dd = str(fecha_nac.day).zfill(2)
    return f"{c1}{c2}{c3}{c4}{yy}{mm}{dd}XXX"


estados_mexico = list(estados_curp.keys())
estados_mexico.insert(0, "SELECCIONE UN ESTADO")


@st.dialog("🎉 ¡REGISTRO EXITOSO - 20 DE NOVIEMBRE!")
def mostrar_modal_comprobante_20n():
    p = st.session_state.ultimo_paciente_20n
    if p:
        st.success(f"Registro guardado correctamente para **{p['nombre_completo']}**.")
        st.info(f"**Folio Asignado:** {p['folio']} | **RFC:** {p['rfc']}")
        if st.button("➕ Nuevo Registro (Reiniciar)", use_container_width=True):
            st.session_state.ultimo_paciente_20n = None
            st.rerun()


if st.session_state.ultimo_paciente_20n is not None:
    mostrar_modal_comprobante_20n()

modalidad_texto = "Extramuros" if st.session_state.tipo_jornada == "E" else "Intramuros"

st.markdown(
    '<p class="main-header">CMN "20 de Noviembre" - Registro Nominal</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p class="sub-header">Unidad: <b>{st.session_state.nombre_unidad}</b> | Modalidad: <b>{modalidad_texto}</b></p>',
    unsafe_allow_html=True,
)

# --- 1. DERECHOHABIENCIA Y ADSCRIPCIÓN LABORAL ---
st.markdown('<div class="section-title">1. Derechohabiencia y Adscripción Laboral</div>', unsafe_allow_html=True)

dh = st.selectbox("¿Cuenta con derechohabiencia? *", options=["SELECCIONE", "SÍ", "NO"], key="20n_dh")

tipo_dh = "NO APLICA"
trabaja_cmn = "NO"
num_trabajador = ""

if dh == "SÍ":
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        tipo_dh = st.selectbox("Tipo de DH *", options=["SELECCIONE"] + opt_tipo_dh, key="20n_tipo_dh")
    with col_d2:
        trabaja_cmn = st.radio("¿Trabaja en CMN 20 de Noviembre?", options=["NO", "SÍ"], horizontal=True, key="20n_trabaja_cmn")

    if trabaja_cmn == "SÍ":
        num_trabajador = st.text_input("Número de Trabajador", key="20n_num_trab
