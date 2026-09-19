import datetime
import io
import qrcode
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

# Diccionario con unidades médicas (omitiendo artículos, preposiciones y títulos)
unidades_issste = {
    "20 DE NOVIEMBRE": "NOV",
    "CHURUBUSCO": "CHU",
    "CLIDDA": "CLI",
    "COYOACAN": "COY",
    "DEL VALLE": "VAL",
    "DIVISION DEL NORTE": "NOR",
    "DR. DARIO FERNANDEZ FIERRO": "DAR",
    "DR. IGNACIO CHAVEZ": "CHA",
    "ERMITA": "ERM",
    "FUENTES BROTANTES": "FUE",
    "HG DRA. MATILDE PETRA MONTOYA LAFRAGUA": "MAT",
    "MILPA ALTA": "MIL",
    "NARVARTE": "NAR",
    "TLALPAN": "TLA",
    "VILLA ALVARO OBREGON": "ALV",
    "XOCHIMILCO": "XOC",
}

# Asegurar variables de estado iniciales
if "tipo_jornada" not in st.session_state:
    st.session_state.tipo_jornada = "I"
if "nombre_unidad" not in st.session_state:
    st.session_state.nombre_unidad = "ERMITA"
if "siglas_unidad" not in st.session_state:
    st.session_state.siglas_unidad = "ERM"

st.markdown(
    '<div class="section-title">1. Configuración de la Unidad y Jornada</div>',
    unsafe_allow_html=True,
)

with st.form("form_config_admin"):
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
            f"¡Configuración aplicada! Unidad: **{st.session_state.nombre_unidad}** | Estructura de folio configurada correctamente."
        )

st.markdown(
    '<div class="section-title">2. Vista Previa del Folio Generado</div>',
    unsafe_allow_html=True,
)
hoy_ejemplo = datetime.date.today().strftime("%y%m%d")
ejemplo_folio = f"{hoy_ejemplo}-{st.session_state.tipo_jornada}{st.session_state.siglas_unidad}-001"
st.info(
    f"El próximo registro que se capture utilizará la estructura: **`{ejemplo_folio}`**"
)

st.markdown(
    '<div class="section-title">3. Generador de Enlaces y Códigos QR Operativos</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
<div class="card-admin">
    <p><b>Instrucción para el Administrador:</b> Utilice el enlace predeterminado para generar el Código QR que abrirá directamente el formulario de registro (Pestaña 1).</p>
</div>
""",
    unsafe_allow_html=True,
)

# URL por defecto solicitada
url_base_default = "https://medprev-vacunas-invernal.streamlit.app/"
url_despliegue = st.text_input(
    "URL base de la aplicación desplegada (Raíz / Pestaña 1):",
    value=url_base_default,
)

if st.button("Generar Enlace y Código QR"):
    link_final = url_despliegue.strip()

    st.success(
        f"Parámetros listos para la unidad **{st.session_state.nombre_unidad}** en modalidad **{'Extramuros' if st.session_state.tipo_jornada == 'E' else 'Intramuros'}**."
    )
    st.markdown(f"🔗 **Enlace directo a la Pestaña 1 (Registro):** `{link_final}`")

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(link_final)
    qr.make(fit=True)

    img_qr = qr.make_image(fill_color="#611232", back_color="#ffffff")

    buffer = io.BytesIO()
    img_qr.save(buffer, format="PNG")
    buffer.seek(0)

    st.markdown("---")
    st.markdown("#### Código QR Operativo Generado:")
    st.image(
        buffer,
        caption=f"QR para {st.session_state.nombre_unidad} ({'Extramuros' if st.session_state.tipo_jornada == 'E' else 'Intramuros'})",
        width=250,
    )

    st.download_button(
        label="📥 Descargar Imagen QR (PNG)",
        data=buffer,
        file_name=f"QR_{st.session_state.siglas_unidad}_{st.session_state.tipo_jornada}.png",
        mime="image/png",
        use_container_width=True,
    )
