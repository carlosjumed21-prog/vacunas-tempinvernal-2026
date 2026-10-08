import datetime
import unicodedata
import streamlit as st
import streamlit.components.v1 as components
from config import aplicar_configuracion_global
from utils.sheets import guardar_registro_censal_20_nov

aplicar_configuracion_global("Censo Nominal - 20 de Noviembre", "💉")

# --- BOTÓN DE RETORNO AL MENÚ PRINCIPAL ---
col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
with col_nav1:
    if st.button("🏠 Volver al Menú Principal", use_container_width=True):
        st.switch_page("app.py")

st.markdown("---")

# --- RECUPERACIÓN DE PARÁMETROS DE URL ---
params = st.query_params
sufijo_js = params.get("js", "")
st.session_state.siglas_unidad = "20N"
st.session_state.nombre_unidad = (
    f"CENTRO MÉDICO NACIONAL '20 DE NOVIEMBRE' (Brigada {sufijo_js})"
    if sufijo_js
    else "CENTRO MÉDICO NACIONAL '20 DE NOVIEMBRE'"
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
    fec_part = f"{yy}{mm}{dd}"
    
    return f"{c1}{c2}{c3}{c4}{fec_part}XXX"


estados_mexico = [
    "SELECCIONE UN ESTADO",
    "AGUASCALIENTES",
    "BAJA CALIFORNIA",
    "BAJA CALIFORNIA SUR",
    "CAMPECHE",
    "CHIAPAS",
    "CHIHUAHUA",
    "CIUDAD DE MÉXICO",
    "COAHUILA",
    "COLIMA",
    "DURANGO",
    "ESTADO DE MÉXICO",
    "GUANAJUATO",
    "GUERRERO",
    "HIDALGO",
    "JALISCO",
    "MICHOACÁN",
    "MORELOS",
    "NAYARIT",
    "NUEVO LEÓN",
    "OAXACA",
    "PUEBLA",
    "QUERÉTARO",
    "QUINTANA ROO",
    "SAN LUIS POTOSÍ",
    "SINALOA",
    "SONORA",
    "TABASCO",
    "TAMAULIPAS",
    "TLAXCALA",
    "VERACRUZ",
    "YUCATÁN",
    "ZACATECAS",
]


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

st.markdown(
    '<p class="main-header">CMN "20 de Noviembre" - Registro Nominal</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p class="sub-header">Unidad: <b>{st.session_state.nombre_unidad}</b></p>',
    unsafe_allow_html=True,
)

# --- 1. DERECHOHABIENCIA Y ADSCRIPCIÓN ---
st.markdown('<div class="section-title">1. Derechohabiencia y Adscripción Laboral</div>', unsafe_allow_html=True)

col_d1, col_d2 = st.columns(2)
with col_d1:
    dh = st.selectbox("¿Cuenta con derechohabiencia? *", options=["SELECCIONE", "SÍ", "NO"], key="20n_dh")
with col_d2:
    tipo_dh = st.selectbox("Tipo de DH *", options=["SELECCIONE", "TRABAJADOR ACTIVO", "JUBILADO / PENSIONADO", "FAMILIAR", "OTRO"], key="20n_tipo_dh")

col_t1, col_t2 = st.columns(2)
with col_t1:
    trabaja_cmn = st.radio("¿Trabaja en CMN 20 de Noviembre?", options=["NO", "SÍ"], horizontal=True, key="20n_trabaja_cmn")
with col_t2:
    num_trabajador = st.text_input("Número de Trabajador", key="20n_num_trabajador") if trabaja_cmn == "SÍ" else ""

# --- 2. IDENTIFICACIÓN DEL PACIENTE ---
st.markdown('<div class="section-title">2. Identificación del Paciente</div>', unsafe_allow_html=True)
col_n1, col_n2, col_n3 = st.columns(3)
with col_n1:
    paterno = st.text_input("Apellido Paterno *", key="20n_paterno")
with col_n2:
    materno = st.text_input("Apellido Materno *", key="20n_materno")
with col_n3:
    nombres = st.text_input("Nombre(s) *", key="20n_nombres")

col_fn1, col_fn2, col_fn3 = st.columns(3)
with col_fn1:
    fecha_nacimiento = st.date_input(
        "Fecha de Nacimiento *",
        value=None,
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date.today(),
        format="DD/MM/YYYY",
        key="20n_fnac",
    )
with col_fn2:
    sexo = st.selectbox("Sexo *", options=["SELECCIONE UNA OPCIÓN", "HOMBRE", "MUJER"], key="20n_sexo")
with col_fn3:
    edo_nac = st.selectbox("Estado de Nacimiento (Edo Nac) *", options=estados_mexico, key="20n_edonac")

muni_nac = st.text_input("Municipio de Nacimiento (Muni Nac) *", key="20n_muninac")

embarazo = "NO"
if sexo == "MUJER":
    embarazo = st.radio("¿Embarazo?", options=["NO", "SÍ"], horizontal=True, key="20n_embarazo")

calc_anos, calc_meses, _ = calcular_edad_detallada(fecha_nacimiento, val_fecha_app) if fecha_nacimiento else (0, 0, 0)
st.markdown(f'<div class="card-edad">📅 Edad calculada: {calc_anos} Años, {calc_meses} Meses</div>', unsafe_allow_html=True)

# Generación automática de RFC debajo de CURP/Edad
rfc_generado = generar_rfc_algoritmico(paterno, materno, nombres, fecha_nacimiento)
rfc_final = st.text_input("RFC (Calculado / Editable) *", value=rfc_generado, key="20n_rfc")
st.markdown(f'<div class="card-rfc">📋 RFC: {rfc_final}</div>', unsafe_allow_html=True)

# --- 3. OCUPACIÓN Y ADSCRIPCIÓN INSTITUCIONAL ---
st.markdown('<div class="section-title">3. Datos de Ocupación y Adscripción Institucional</div>', unsafe_allow_html=True)

personal_salud_opc = st.selectbox(
    "Seleccione su Ocupación *",
    options=[
        "SELECCIONE UNA OPCIÓN",
        "PERSONAL DE SALUD (MÉDICO, ENFERMERÍA, PARAMÉDICO, ETC.)",
        "ADMINISTRATIVO/A",
        "OTRO",
    ],
    key="20n_ocupacion",
)
personal_salud_val = "SÍ" if "PERSONAL DE SALUD" in personal_salud_opc else "NO"

col_lab1, col_lab2, col_lab3, col_lab4 = st.columns(4)
with col_lab1:
    categoria = st.selectbox("Categoría", options=["SELECCIONE", "MÉDICO", "ENFERMERA", "ADMINISTRATIVO", "OTRO"], key="20n_categoria")
with col_lab2:
    servicio = st.selectbox("Servicio", options=["SELECCIONE", "EPIDEMIOLOGÍA", "URGENCIAS", "PEDIATRÍA", "MEDICINA INTERNA", "CIRUGÍA", "OTRO"], key="20n_servicio")
with col_lab3:
    coordinacion = st.selectbox("Coordinación", options=["SELECCIONE", "DIRECCIÓN MÉDICA", "SUBDIRECCIÓN", "ENFERMERÍA", "OTRO"], key="20n_coordinacion")
with col_lab4:
    turno_full = st.selectbox("Turno", options=["SELECCIONE", "Matutino", "Vespertino", "Nocturno", "Jornada Acumulada"], key="20n_turno")

turno_map = {
    "Matutino": "M",
    "Vespertino": "V",
    "Nocturno": "N",
    "Jornada Acumulada": "JA"
}
turno_val = turno_map.get(turno_full, "")

st.markdown("---")
if st.button("Registrar en CMN 20 de Noviembre", use_container_width=True):
    if not fecha_nacimiento:
        st.error("Seleccione la fecha de nacimiento.")
    elif not paterno or not nombres:
        st.error("Complete Apellido Paterno y Nombre(s).")
    elif dh == "SELECCIONE":
        st.error("Indique si cuenta con derechohabiencia.")
    elif tipo_dh == "SELECCIONE":
        st.error("Seleccione el Tipo de DH.")
    elif sexo == "SELECCIONE UNA OPCIÓN":
        st.error("Seleccione el Sexo.")
    elif personal_salud_opc == "SELECCIONE UNA OPCIÓN":
        st.error("Seleccione la Ocupación.")
    else:
        try:
            fn_dia = str(fecha_nacimiento.day).zfill(2)
            fn_mes = str(fecha_nacimiento.month).zfill(2)
            fn_ano = str(fecha_nacimiento.year)

            datos_20n = {
                "rfc": rfc_final,
                "dh": dh,
                "tipo_dh": tipo_dh,
                "trabaja_cmn": trabaja_cmn,
                "num_trabajador": num_trabajador,
                "personal_salud": personal_salud_val,
                "categoria": categoria,
                "servicio": servicio,
                "coordinacion": coordinacion,
                "turno": turno_val,
                "nombre": nombres.upper(),
                "paterno": paterno.upper(),
                "materno": materno.upper() if materno else "",
                "edo_nac": edo_nac,
                "muni_nac": muni_nac.upper(),
                "fn_dia": fn_dia,
                "fn_mes": fn_mes,
                "fn_ano": fn_ano,
                "anos": calc_anos,
                "meses": calc_meses,
                "sexo": sexo,
                "embarazo": embarazo,
            }

            folio_asignado = guardar_registro_censal_20_nov(datos_20n)

            st.session_state.ultimo_paciente_20n = {
                "nombre_completo": f"{paterno.upper()} {materno.upper()} {nombres.upper()}",
                "folio": folio_asignado,
                "rfc": rfc_final,
            }
            st.rerun()

        except Exception as e:
            st.error("⚠️ Error al registrar en la hoja de Google Sheets del CMN 20 de Noviembre:")
            st.exception(e)
