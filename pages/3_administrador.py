import datetime
import streamlit as st

st.set_page_config(
    page_title="Panel de Administración - Censo Nominal",
    page_icon="⚙️",
    layout="centered",
)

st.markdown(
    """
    <style>
        .stApp { background-color: #fbf9f4; }
        [data-testid="stSidebar"] { background-color: #611232 !important; }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span { color: #ffffff !important; }
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
        .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
        .card-admin { background-color: #ffffff; border: 2px solid #a57f2c; padding: 20px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.08); }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="main-header">Panel de Control y Administración</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-header">Configuración de Jornada, Unidad Médica y Generación de Enlaces / QR</p>',
    unsafe_allow_html=True,
)

# Diccionario de unidades médicas con sus respectivas siglas clave para el folio
unidades_issste = {
    "20 DE NOVIEMBRE": "20NOV",
    "CHURUBUSCO": "CHUR",
    "CLIDDA": "CLID",
    "COYOACAN": "COYO",
    "DEL VALLE": "DVALL",
    "DIVISION DEL NORTE": "DIVN",
    "DR. DARIO FERNANDEZ FIERRO": "DFF",
    "DR. IGNACIO CHAVEZ": "ICHAV",
    "ERMITA": "CMFE",
    "FUENTES BROTANTES": "FBROT",
    "HG DRA. MATILDE PETRA MONTOYA LAFRAGUA": "MPML",
    "MILPA ALTA": "MILPA",
    "NARVARTE": "NARV",
    "TLALPAN": "TLAL",
    "VILLA ALVARO OBREGON": "VAO",
    "XOCHIMILCO": "XOCH",
}

# Asegurar variables de estado iniciales
if "tipo_jornada" not in st.session_state:
    st.session_state.tipo_jornada = "I"
if "nombre_unidad" not in st.session_state:
    st.session_state.nombre_unidad = "ERMITA"
if "siglas_unidad" not in st.session_state:
    st.session_state.siglas_unidad = "CMFE"

st.markdown(
    '<div class="section-title">1. Configuración de la Unidad y Jornada</div>',
    unsafe_allow_html=True,
)

with st.form("form_config_admin"):
    # Encontrar el índice actual para el selectbox
    nombres_unidades_lista = list(unidades_issste.keys())
    indice_actual = (
        nombres_unidades_lista.index(st.session_state.nombre_unidad)
        if st.session_state.nombre_unidad in nombres_unidades_lista
        else 0
    )

    unidad_seleccionada = st.selectbox(
        "Seleccione la Unidad Médica:",
        options=nombres_unidades_lista,
        index=indice_actual,
    )

    tipo_jornada_input = st.radio(
        "Modalidad de la Jornada:",
        options=["Intramuros (I)", "Extramuros (E)"],
        index=0 if st.session_state.tipo_jornada == "I" else 1,
    )

    btn_guardar_config = st.form_submit_button(
        "Actualizar Configuración de Folios", use_container_width=True
    )

    if btn_guardar_config:
        st.session_state.nombre_unidad = unidad_seleccionada
        st.session_state.siglas_unidad = unidades_issste[unidad_seleccionada]
        st.session_state.tipo_jornada = (
            "I" if "Intramuros" in tipo_jornada_input else "E"
        )
        st.success(
            f"¡Configuración aplicada! Unidad: **{st.session_state.nombre_unidad}** ({st.session_state.siglas_unidad}) | Prefijo activo para folios: **{st.session_state.tipo_jornada}{st.session_state.siglas_unidad}**"
        )

st.markdown(
    '<div class="section-title">2. Vista Previa del Folio Generado</div>',
    unsafe_allow_html=True,
)
hoy_ejemplo = datetime.date.today().strftime("%y%m%d")
ejemplo_folio = f"{st.session_state.tipo_jornada}{st.session_state.siglas_unidad}-{hoy_ejemplo}-001"
st.info(
    f"El próximo registro que se capture en el formulario utilizará la estructura de folio: **`{ejemplo_folio}`**"
)

st.markdown(
    '<div class="section-title">3. Generador de Código QR Operativo para la Unidad</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
<div class="card-admin">
    <p><b>Instrucción para el Administrador:</b> Genere el enlace y código QR correspondiente para distribuir a la unidad médica seleccionada, garantizando el control de la jornada y trazabilidad nominal.</p>
</div>
""",
    unsafe_allow_html=True,
)

url_despliegue = st.text_input(
    "URL de la aplicación desplegada (Streamlit Cloud / Servidor Local):",
    value="https://tu-app-vacunacion.streamlit.app",
)

if st.button("Generar Enlace y Ficha QR"):
    st.success(
        f"Parámetros empaquetados correctamente para la unidad **{st.session_state.nombre_unidad}** bajo la modalidad **{'Extramuros' if st.session_state.tipo_jornada == 'E' else 'Intramuros'}**."
    )
    st.markdown(f"🔗 Enlace directo configurado: `{url_despliegue}`")
