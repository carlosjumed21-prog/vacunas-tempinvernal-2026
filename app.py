import datetime
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Censo Nominal - Vacunación e Invernal",
    page_icon="💉",
    layout="centered",
)

# Ocultar completamente la barra lateral para usuarios operativos y definir estilos institucionales
st.markdown(
    """
    <style>
        .stApp { background-color: #fbf9f4; }
        [data-testid="stSidebar"] { display: none !important; }
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
        .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
        label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }
        .card-edad { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #611232; font-size: 1.3rem !important; margin-bottom: 15px; }
        .card-grupo { background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 15px; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; }
        .stButton>button:hover { background-color: #002f2a !important; color: white !important; }
        input[type="text"] { text-transform: uppercase !important; font-size: 1.1rem !important; }
    </style>
""",
    unsafe_allow_html=True,
)

# Inicializar variables de estado compartido si no existen
if "registros_censales" not in st.session_state:
    st.session_state.registros_censales = []
if "contador_consecutivo" not in st.session_state:
    st.session_state.contador_consecutivo = 1
if "fecha_ultimo_consecutivo" not in st.session_state:
    st.session_state.fecha_ultimo_consecutivo = datetime.date.today()
if "tipo_jornada" not in st.session_state:
    st.session_state.tipo_jornada = "I"
if "siglas_unidad" not in st.session_state:
    st.session_state.siglas_unidad = "ERM"
if "nombre_unidad" not in st.session_state:
    st.session_state.nombre_unidad = "ERMITA"


def calcular_edad_detallada(fecha_nac, fecha_ref):
    if not fecha_nac or not fecha_ref or fecha_nac > fecha_ref:
        return 0, 0, 0
    anos = fecha_ref.year - fecha_nac.year
    meses = fecha_ref.month - fecha_nac.month
    dias = fecha_ref.day - fecha_nac.day

    if dias < 0:
        meses -= 1
        mes_anterior = fecha_ref.month - 1 if fecha_ref.month > 1 else 12
        anio_anterior = (
            fecha_ref.year if fecha_ref.month > 1 else fecha_ref.year - 1
        )
        dias_mes_anterior = (
            datetime.date(anio_anterior, mes_anterior + 1, 1)
            - datetime.timedelta(days=1)
        ).day
        dias += dias_mes_anterior

    if meses < 0:
        anos -= 1
        meses += 12

    return max(0, anos), max(0, meses), max(0, dias)


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

st.markdown(
    '<p class="main-header">Sistema de Registro Nominal de Vacunación</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p class="sub-header">Unidad: <b>{st.session_state.nombre_unidad}</b> | Modalidad: <b>{"Extramuros" if st.session_state.tipo_jornada == "E" else "Intramuros"}</b></p>',
    unsafe_allow_html=True,
)

# --- BLOQUE 1: DATOS GENERALES Y FECHAS ---
st.markdown(
    '<div class="section-title">1. Datos Generales y Fechas</div>',
    unsafe_allow_html=True,
)
col_g1, col_g2, col_g3 = st.columns(3)
with col_g1:
    fecha_registro = st.date_input(
        "Fecha de Registro", value=datetime.date.today(), format="DD/MM/YYYY"
    )
with col_g2:
    fecha_aplicacion = st.date_input(
        "Fecha de Aplicación", value=datetime.date.today(), format="DD/MM/YYYY"
    )

hoy_actual = fecha_registro
if st.session_state.fecha_ultimo_consecutivo != hoy_actual:
    st.session_state.fecha_ultimo_consecutivo = hoy_actual
    st.session_state.contador_consecutivo = 1

aammmdd = hoy_actual.strftime("%y%m%d")
# Estructura de folio exacta: AAMMDD-[I/E][SIGLAS]-001 (Sin diagonales)
folio_automatico = f"{aammmdd}-{st.session_state.tipo_jornada}{st.session_state.siglas_unidad}-{str(st.session_state.contador_consecutivo).zfill(3)}"

with col_g3:
    st.markdown(
        f"**Folio Generado (Auto)**<br>`{folio_automatico}`",
        unsafe_allow_html=True,
    )

# --- BLOQUE 2: IDENTIFICACIÓN DEL PACIENTE ---
st.markdown(
    '<div class="section-title">2. Identificación del Paciente</div>',
    unsafe_allow_html=True,
)
col_n1, col_n2, col_n3 = st.columns(3)
with col_n1:
    paterno = st.text_input("Apellido Paterno *")
with col_n2:
    materno = st.text_input("Apellido Materno *")
with col_n3:
    nombres = st.text_input("Nombre(s) *")

col_fn1, col_fn2 = st.columns(2)
with col_fn1:
    fecha_nacimiento = st.date_input(
        "Fecha de Nacimiento *",
        value=None,
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date.today(),
        format="DD/MM/YYYY",
    )
with col_fn2:
    sexo = st.selectbox(
        "Sexo *", options=["SELECCIONE UNA OPCIÓN", "HOMBRE", "MUJER"]
    )

planes_o_embarazo = "NO"
if sexo == "MUJER":
    st.markdown(
        "<div style='background-color: #f7f4eb; border: 1px solid #a57f2c; padding: 12px; border-radius: 6px; margin-bottom: 10px;'>",
        unsafe_allow_html=True,
    )
    planes_o_embarazo = st.radio(
        "¿Está embarazada o tiene planes de embarazo?",
        options=["NO", "SÍ"],
        horizontal=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

calc_anos, calc_meses, calc_dias = (
    calcular_edad_detallada(fecha_nacimiento, fecha_aplicacion)
    if fecha_nacimiento
    else (0, 0, 0)
)

st.markdown(
    '<div class="section-title">Edad Calculada Automáticamente</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="card-edad">📅 {calc_anos} AÑOS, {calc_meses} MESES, {calc_dias} DÍAS</div>',
    unsafe_allow_html=True,
)

with st.form("form_censo_vacunacion_resto"):

    # --- BLOQUE 3: DOMICILIO Y AFILIACIÓN ---
    st.markdown(
        '<div class="section-title">3. Domicilio, Estados y Afiliación</div>',
        unsafe_allow_html=True,
    )
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        estado_nacimiento = st.selectbox(
            "Estado de Nacimiento *", options=estados_mexico, key="est_nac"
        )
    with col_d2:
        estado_residencia = st.selectbox(
            "Estado de Residencia (Entidad Federativa) *",
            options=estados_mexico,
            key="est_res",
        )

    col_dom1, col_dom2, col_dom3 = st.columns([2, 1, 1])
    with col_dom1:
        calle = st.text_input("Calle *")
    with col_dom2:
        numero = st.text_input("No. (Ext / Int) *")
    with col_dom3:
        colonia = st.text_input("Colonia *")

    cuenta_derechohabiencia = st.radio(
        "¿Cuenta con derechohabiencia? *",
        options=["NO", "SÍ"],
        horizontal=True,
    )

    # --- BLOQUE 4: OCUPACIÓN ---
    st.markdown(
        '<div class="section-title">4. Ocupación</div>',
        unsafe_allow_html=True,
    )
    ocupacion = st.selectbox(
        "Seleccione su Ocupación *",
        options=[
            "SELECCIONE UNA OPCIÓN",
            "PERSONAL DE SALUD",
            "JUBILADO/A",
            "MAESTRO/A",
            "ADMINISTRATIVO/A",
            "TRABAJO EN GUARDERÍA",
            "OTRAS PROFESIONES",
        ],
    )

    # --- BLOQUE 5: GRUPOS DE RIESGO Y COMORBILIDADES ---
    st.markdown(
        '<div class="section-title">5. Grupos de Riesgo y Comorbilidades</div>',
        unsafe_allow_html=True,
    )
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        vih = st.checkbox("VIH / SIDA")
        diabetes = st.checkbox("DIABETES MELLITUS")
        obesidad = st.checkbox("OBESIDAD MÓRBIDA")
        cardiopatias = st.checkbox("CARDIOPATÍAS AGUDAS O CRÓNICAS")
        epoc = st.checkbox("ENFERMEDAD PULMONAR CRÓNICA (EPOC / ASMA)")

    with col_r2:
        cancer = st.checkbox("CÁNCER")
        congenitas = st.checkbox(
            "ENFERMEDADES CARDIACAS/PULMONARES CONGÉNITAS U OTROS"
        )
        insuficiencia_renal = st.checkbox("INSUFICIENCIA RENAL")
        inmunosupresion = st.checkbox("INMUNOSUPRESIÓN ADQUIRIDA (EXCEPTO VIH)")
        hipertension = st.checkbox("HIPERTENSIÓN ARTERIAL ESENCIAL")

    # --- LÓGICA DE CONDICIONES PARA AUTODETECCIÓN DE GRUPO OBJETIVO ---
    edad_total_meses = (calc_anos * 12) + calc_meses
    tiene_comorb = any(
        [
            vih,
            diabetes,
            obesidad,
            cardiopatias,
            epoc,
            cancer,
            congenitas,
            insuficiencia_renal,
            inmunosupresion,
            hipertension,
        ]
    )

    grupo_sugerido = ""
    if fecha_nacimiento is not None:
        if 6 <= edad_total_meses <= 59:
            grupo_sugerido = "6 A 59 MESES"
        elif calc_anos >= 60:
            grupo_sugerido = "60 Y MÁS"
        elif 5 <= calc_anos <= 11:
            grupo_sugerido = (
                "5 A 11 AÑOS (Riesgo / Comorbilidad / Indicación)"
                if tiene_comorb
                else "5 A 11 AÑOS"
            )
        elif planes_o_embarazo == "SÍ":
            grupo_sugerido = "EMBARAZADAS"
        elif ocupacion == "PERSONAL DE SALUD":
            grupo_sugerido = "PERSONAL DE SALUD"
        elif 12 <= calc_anos <= 59 and tiene_comorb:
            grupo_sugerido = "12 A 59 AÑOS CON COMORBILIDAD"
        else:
            grupo_sugerido = "POBLACIÓN GENERAL / OTRO"

    st.markdown(
        '<div class="section-title">6. Grupo Objetivo (Detectado Automáticamente)</div>',
        unsafe_allow_html=True,
    )
    if grupo_sugerido == "":
        st.markdown(
            '<div class="card-grupo" style="background-color: #fbf9f4; border: 2px dashed #a57f2c; color: #611232;">POR DESIGNAR</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="card-grupo">🎯 {grupo_sugerido}</div>',
            unsafe_allow_html=True,
        )

    # --- ANTECEDENTE VACUNAL ---
    st.markdown(
        '<div class="section-title">7. Antecedente Vacunal</div>',
        unsafe_allow_html=True,
    )
    col_av1, col_av2 = st.columns(2)
    with col_av1:
        antecedente_covid = st.radio(
            "¿Cuenta con alguna dosis previa de COVID-19?",
            options=["SÍ", "NO", "LO DESCONOCE"],
            horizontal=True,
        )
    with col_av2:
        antecedente_influenza = st.radio(
            "¿Cuenta con alguna dosis previa de Influenza?",
            options=["SÍ", "NO", "LO DESCONOCE"],
            horizontal=True,
        )

    st.markdown("---")
    submitted = st.form_submit_button(
        "Guardar Paciente en el Censo Nominal", use_container_width=True
    )

    if submitted:
        if not fecha_nacimiento:
            st.error("Por favor seleccione la Fecha de Nacimiento.")
        elif grupo_sugerido == "":
            st.error(
                "Por favor complete la fecha de nacimiento para determinar el grupo objetivo."
            )
        elif (
            not paterno
            or not nombres
            or estado_nacimiento == "SELECCIONE UN ESTADO"
            or estado_residencia == "SELECCIONE UN ESTADO"
            or not calle
            or not numero
            or not colonia
            or ocupacion == "SELECCIONE UNA OPCIÓN"
        ):
            st.error(
                "Por favor complete los campos obligatorios y seleccione una opción válida en los menús desplegables (*)."
            )
        else:
            nuevo_paciente = {
                "folio": folio_automatico,
                "nombre_completo": f"{paterno.upper()} {materno.upper()}, {nombres.upper()}",
                "paterno": paterno.upper(),
                "materno": materno.upper(),
                "nombres": nombres.upper(),
                "fecha_nacimiento": fecha_nacimiento,
                "edad_anos": calc_anos,
                "edad_meses": calc_meses,
                "edad_dias": calc_dias,
                "edad_total_meses": edad_total_meses,
                "sexo": sexo,
                "embarazo": (planes_o_embarazo == "SÍ"),
                "ocupacion": ocupacion,
                "personal_salud": (ocupacion == "PERSONAL DE SALUD"),
                "derechohabiencia": cuenta_derechohabiencia,
                "tiene_comorbilidades": tiene_comorb,
                "grupo_objetivo": grupo_sugerido,
                "antecedente_covid": antecedente_covid,
                "antecedente_influenza": antecedente_influenza,
                "fecha_registro": fecha_registro,
            }
            st.session_state.registros_censales.append(nuevo_paciente)
            st.session_state.contador_consecutivo += 1

            st.success(
                f"¡Paciente registrado correctamente con Folio **{folio_automatico}**!"
            )
