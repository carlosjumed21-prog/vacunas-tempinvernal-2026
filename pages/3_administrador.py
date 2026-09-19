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

st.markdown('<p class="main-header">Panel de Control y Administración</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Configuración de Jornada, Unidad Médica y Generación de Enlaces / QR</p>', unsafe_allow_html=True)

# Asegurar variables de estado iniciales
if "tipo_jornada" not in st.session_state:
    st.session_state.tipo_jornada = "I"
if "siglas_unidad" not in st.session_state:
    st.session_state.siglas_unidad = "CMFE"

st.markdown('<div class="section-title">1. Configuración de la Unidad y Jornada</div>', unsafe_allow_html=True)

with st.form("form_config_admin"):
    unidad_input = st.text_input("Siglas de la Unidad Médica (Ej. CMFE, HGM, HGZ1)", value=st.session_state.siglas_unidad)
    
    tipo_jornada_input = st.radio(
        "Modalidad de la Jornada:",
        options=["Intramuros (I)", "Extramuros (E)"],
        index=0 if st.session_state.tipo_jornada == "I" else 1
    )

    btn_guardar_config = st.form_submit_button("Actualizar Configuración de Folios", use_container_width=True)

    if btn_guardar_config:
        st.session_state.siglas_unidad = unidad_input.strip().upper()
        st.session_state.tipo_jornada = "I" if "Intramuros" in tipo_jornada_input else "E"
        st.success(f"¡Configuración aplicada con éxito! Prefijo activo para folios: **{st.session_state.tipo_jornada}{st.session_state.siglas_unidad}**")

st.markdown('<div class="section-title">2. Vista Previa del Folio Generado</div>', unsafe_allow_html=True)
import datetime
hoy_ejemplo = datetime.date.today().strftime("%y%m%d")
ejemplo_folio = f"{st.session_state.tipo_jornada}{st.session_state.siglas_unidad}-{hoy_ejemplo}-001"
st.info(f"El próximo registro que se capture en el formulario utilizará la estructura de folio: **`{ejemplo_folio}`**")

st.markdown('<div class="section-title">3. Generador de Código QR Operativo para la Unidad</div>', unsafe_allow_html=True)
st.markdown("""
<div class="card-admin">
    <p><b>Instrucción para el Administrador:</b> Genere el código QR para que el personal operativo escanee y acceda directamente a este módulo de captura configurado con las siglas y modalidad correspondientes.</p>
</div>
""", unsafe_allow_html=True)

url_despliegue = st.text_input("URL de la aplicación desplegada (Streamlit Cloud / Servidor Local):", value="https://tu-app-vacunacion.streamlit.app")

if st.button("Generar Enlace y Ficha QR"):
    st.success(f"Parámetros empaquetados para la clínica **{st.session_state.siglas_unidad}** en modalidad **{'Extramuros' if st.session_state.tipo_jornada == 'E' else 'Intramuros'}**.")
    st.markdown(f"🔗 Enlace directo configurado: `{url_despliegue}`")
    # Nota: Aquí se puede integrar la librería 'qrcode' de Python si requieres que dibuje la imagen QR real en pantalla.
