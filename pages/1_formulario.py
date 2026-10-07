import datetime
import unicodedata
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
from config import MAPA_SIGLAS_INVERSO, aplicar_configuracion_global
from utils.sheets import guardar_registro_censal

aplicar_configuracion_global("Censo Nominal - Registro", "💉")

# --- BOTÓN DE RETORNO AL MENÚ PRINCIPAL ---
col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
with col_nav1:
    if st.button("🏠 Volver al Menú Principal", use_container_width=True):
        st.switch_page("app.py")

st.markdown("---")

# --- RECUPERACIÓN CORRECTA DE PARÁMETROS DE URL ---
params = st.query_params
sigla_url = params.get("unidad", "20N").upper()

nombre_base_unidad = MAPA_SIGLAS_INVERSO.get(sigla_url, "20 DE NOVIEMBRE")
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
        .card-grupo { background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 15px; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; }
        input[type="text"] { text-transform: uppercase !important; font-size: 1.1rem !important; }
    </style>
""",
    unsafe_allow_html=True,
)

if "registros_censales" not in st.session_state:
    st.session_state.registros_censales = []
if "ultimo_paciente_registrado" not in st.session_state:
    st.session_state.ultimo_paciente_registrado = None


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
    "AGUASCALIENTES": "AS",
    "BAJA CALIFORNIA": "BC",
    "BAJA CALIFORNIA SUR": "BS",
    "CAMPECHE": "CC",
    "CHIAPAS": "CS",
    "CHIHUAHUA": "CH",
    "CIUDAD DE MÉXICO": "DF",
    "COAHUILA": "CL",
    "COLIMA": "CM",
    "DURANGO": "DG",
    "ESTADO DE MÉXICO": "MC",
    "GUANAJUATO": "GT",
    "GUERRERO": "GR",
    "HIDALGO": "HG",
    "JALISCO": "JC",
    "MICHOACÁN": "MN",
    "MORELOS": "MS",
    "NAYARIT": "NT",
    "NUEVO LEÓN": "NL",
    "OAXACA": "OC",
    "PUEBLA": "PL",
    "QUERÉTARO": "QT",
    "QUINTANA ROO": "QR",
    "SAN LUIS POTOSÍ": "SP",
    "SINALOA": "SL",
    "SONORA": "SR",
    "TABASCO": "TC",
    "TAMAULIPAS": "TS",
    "TLAXCALA": "TL",
    "VERACRUZ": "VZ",
    "YUCATÁN": "YN",
    "ZACATECAS": "ZS",
}


def generar_curp_algoritmica(
    paterno, materno, nombres, fecha_nac, sexo, est_nac, digitos_extra=""
):
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


@st.dialog("🎉 ¡REGISTRO EXITOSO - TICKET DIGITAL!")
def mostrar_modal_comprobante():
    p = st.session_state.ultimo_paciente_registrado
    if p:
        curp_mostrar = p.get(
            "curp_con_nacimiento",
            p.get("curp_con_municipio", p.get("curp_con_entidad", "CURP")),
        )
        nombre_val = p["nombre_completo"]
        folio_val = p["folio"]
        vacuna_val = p.get("vacuna_interes", "AMBAS")
        grupo_val = p["grupo_objetivo"]
        fecha_val = datetime.date.today().strftime("%d/%m/%Y")

        # Texto estructurado con saltos de línea reales para el QR
        texto_qr = (
            f"ISSSTE - REGISTRO DE FOLIO VIGILE\n"
            f"FOLIO: {folio_val}\n"
            f"PACIENTE: {nombre_val}\n"
            f"CURP: {curp_mostrar}\n"
            f"VACUNA: {vacuna_val}\n"
            f"GRUPO: {grupo_val}\n"
            f"FECHA: {fecha_val}\n"
            f"ESTADO: REGISTRADO"
        )

        html_comprobante_component = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <!-- Librería QRious para generar el código QR localmente como Canvas -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrious/4.0.2/qrious.min.js"></script>
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 0; background-color: transparent; }}
            .card-comprobante {{ 
                position: relative; 
                background-color: #ffffff; 
                border: 3px solid #1e5b4f; 
                padding: 12px; 
                border-radius: 10px; 
                color: #161a1d; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
                margin-bottom: 10px; 
                overflow: hidden; 
            }}
            .titulo-ticket {{ font-size: 0.90rem !important; font-weight: 900 !important; color: #1e5b4f !important; text-align: center; margin-top: 0; margin-bottom: 6px; z-index: 2; position: relative; }}
            .cuerpo-ticket {{ display: flex; align-items: center; gap: 12px; z-index: 2; position: relative; }}
            .info-container {{ flex: 1; }}
            .qr-container {{ text-align: center; }}
            .qr-container canvas {{ width: 95px !important; height: 95px !important; border: 2px solid #a57f2c; border-radius: 6px; padding: 3px; background: white; display: block; }}
            .folio-grande {{ font-size: 1.10rem !important; font-weight: 900 !important; color: #611232 !important; text-align: center; background-color: #f7f4eb; padding: 5px; border-radius: 6px; border: 2px dashed #a57f2c; margin-top: 6px; z-index: 2; position: relative; }}
            .info-text {{ margin: 3px 0; font-size: 0.78rem; z-index: 2; position: relative; }}
            .leyenda-posterior {{ font-size: 0.68rem !important; font-weight: 700 !important; color: #611232 !important; text-align: center; margin-top: 5px; margin-bottom: 0; z-index: 2; position: relative; }}
            
            .watermark-overlay {{
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                transform: rotate(-25deg);
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                align-items: center;
                pointer-events: none;
                z-index: 0;
                overflow: hidden;
            }}
            .watermark-row {{
                display: flex;
                gap: 20px;
                white-space: nowrap;
                font-size: 0.95rem;
                font-weight: 900;
                color: transparent;
                -webkit-text-stroke: 1px rgba(97, 18, 50, 0.22);
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .watermark-row:nth-child(even) {{
                transform: translateX(-30px);
            }}
            
            .btn-container {{ display: flex; gap: 8px; }}
            .btn {{ flex: 1; padding: 0.65rem 0.4rem; font-size: 0.85rem; font-weight: bold; border-radius: 6px; border: none; cursor: pointer; text-align: center; box-sizing: border-box; }}
            .btn-wa {{ background-color: #25D366; color: white; }}
            .btn-img {{ background-color: #1e5b4f; color: white; }}
        </style>
        </head>
        <body>
            <div id="comprobante-captura" class="card-comprobante">
                <div class="watermark-overlay">
                    <div class="watermark-row">
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                    </div>
                    <div class="watermark-row">
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                    </div>
                    <div class="watermark-row">
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                    </div>
                    <div class="watermark-row">
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                    </div>
                    <div class="watermark-row">
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                    </div>
                    <div class="watermark-row">
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                    </div>
                    <div class="watermark-row">
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                        <span>NO ES UN COMPROBANTE DE VACUNACION</span>
                    </div>
                </div>
                <div class="titulo-ticket">FOLIO DE VACUNACION REGISTRADO</div>
                <div class="cuerpo-ticket">
                    <div class="info-container">
                        <p class="info-text"><b>Paciente:</b> {nombre_val}</p>
                        <p class="info-text"><b>CURP:</b> {curp_mostrar}</p>
                        <p class="info-text"><b>Vacuna:</b> {vacuna_val}</p>
                        <p class="info-text"><b>Grupo:</b> {grupo_val}</p>
                    </div>
                    <div class="qr-container">
                        <canvas id="qr-canvas"></canvas>
                    </div>
                </div>
                <div class="folio-grande">Folio: {folio_val}</div>
                <p class="leyenda-posterior">Posterior a su asistencia a la jornada de vacunación se le entregará un comprobante oficial.</p>
            </div>
            <div class="btn-container">
                <button class="btn btn-wa" onclick="compartirImagenWhatsApp()">💬 WhatsApp (Img)</button>
                <button class="btn btn-img" onclick="descargarCaptura()">📸 Descargar</button>
            </div>
            <script>
                // Generar QR de manera local y síncrona con QRious
                window.addEventListener('DOMContentLoaded', (event) => {{
                    var qr = new QRious({{
                        element: document.getElementById('qr-canvas'),
                        value: {repr(texto_qr)},
                        size: 150
                    }});
                }});

                function compartirImagenWhatsApp() {{
                    const elemento = document.getElementById('comprobante-captura');
                    html2canvas(elemento, {{ scale: 2, useCORS: true }}).then(canvas => {{
                        canvas.toBlob(blob => {{
                            const fileName = 'Folio_{folio_val}.png';
                            const textoMensaje = `💉 *FOLIO DE VACUNACIÓN - VIGILE*\\nPaciente: {nombre_val}\\nFolio: *{folio_val}*\\nCURP: {curp_mostrar}\\nVacuna: {vacuna_val}\\n⚠️ No es un comprobante de vacunación.\\nPosterior a su asistencia a la jornada de vacunación se le entregará un comprobante oficial.`;
                            
                            const enlace = document.createElement('a');
                            enlace.download = fileName;
                            enlace.href = URL.createObjectURL(blob);
                            enlace.click();
                            
                            window.open('https://wa.me/?text=' + encodeURIComponent(textoMensaje), '_blank');
                        }}, 'image/png');
                    }});
                }}
                function descargarCaptura() {{
                    const elemento = document.getElementById('comprobante-captura');
                    html2canvas(elemento, {{ scale: 2, useCORS: true }}).then(canvas => {{
                        const enlace = document.createElement('a');
                        enlace.download = 'Folio_{folio_val}.png';
                        enlace.href = canvas.toDataURL('image/png');
                        enlace.click();
                    }});
                }}
            </script>
        </body>
        </html>
        """

        components.html(html_comprobante_component, height=350)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(
            "➕ Nuevo Registro (Reiniciar Formulario)", use_container_width=True
        ):
            st.session_state.ultimo_paciente_registrado = None
            keys_a_limpiar = [
                "input_paterno",
                "input_materno",
                "input_nombres",
                "input_fnac",
                "input_sexo",
                "input_estnac",
                "input_estres",
                "input_calle",
                "input_num",
                "input_col",
                "input_derecho",
                "input_ocupacion",
                "input_digitos",
                "input_vacuna",
                "ant_cov",
                "ant_inf",
                "chk_discapacidad",
                "chk_fibrosis",
                "chk_hipertension",
                "chk_vih",
                "chk_diabetes",
                "chk_obesidad",
                "chk_cardiopatias",
                "chk_cancer",
                "chk_insufren",
                "chk_gestante",
            ]
            for k in keys_a_limpiar:
                if k in st.session_state:
                    st.session_state[k] = (
                        False
                        if "chk_" in k
                        else ("" if "input_" in k and "fnac" not in k else None)
                    )
            st.rerun()


if st.session_state.ultimo_paciente_registrado is not None:
    mostrar_modal_comprobante()

st.markdown(
    '<p class="main-header">Sistema de Registro Nominal de Vacunación</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p class="sub-header">Unidad: <b>{st.session_state.nombre_unidad}</b> |'
    f' Modalidad: <b>{"Extramuros" if st.session_state.tipo_jornada == "E" else "Intramuros"}</b></p>',
    unsafe_allow_html=True,
)

# --- BOTÓN DE SIMULACIÓN DE DATOS ---
if params.get("test", "").lower() == "true" or st.session_state.get(
    "autenticado_admin", False
):
    with st.container():
        st.markdown(
            """
            <div style="background-color: #fcf8e3; border: 2px dashed #f0ad4e; padding: 10px; border-radius: 8px; margin-bottom: 15px; text-align: center;">
                <span style="font-weight: bold; color: #8a6d3b;">🛠 Modo de Pruebas / Simulación Activo</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "⚡ Simular Datos de Prueba (Autocompletar Todos los Campos)",
            use_container_width=True,
        ):
            st.session_state.input_paterno = "BADILLO"
            st.session_state.input_materno = "XICOHTENCATL"
            st.session_state.input_nombres = "JUAN CARLOS"
            st.session_state.input_fnac = datetime.date(1993, 10, 15)
            st.session_state.input_sexo = "HOMBRE"
            st.session_state.input_estnac = "CIUDAD DE MÉXICO"
            st.session_state.input_estres = "CIUDAD DE MÉXICO"
            st.session_state.input_calle = "AV. INSURGENTES SUR"
            st.session_state.input_num = "123 INT. 4B"
            st.session_state.input_col = "ROSA RIVAS"
            st.session_state.input_derecho = "SÍ"
            st.session_state.input_ocupacion = (
                "PERSONAL DE SALUD (INCLUYE: PARAMÉDICO / PERSONAL SUPERVISOR Y"
                " ADMINISTRATIVO EN ÁREAS CLÍNICAS Y
