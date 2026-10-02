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
        html_comprobante_component = """
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 0; background-color: transparent; }}
            .card-comprobante {{ 
                position: relative; 
                background-color: #ffffff; 
                border: 3px solid #1e5b4f; 
                padding: 15px; 
                border-radius: 10px; 
                color: #161a1d; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
                margin-bottom: 10px; 
                overflow: hidden; 
            }}
            .titulo-ticket {{ font-size: 0.95rem !important; font-weight: 900 !important; color: #1e5b4f !important; text-align: center; margin-top: 0; margin-bottom: 8px; z-index: 2; position: relative; }}
            .folio-grande {{ font-size: 1.25rem !important; font-weight: 900 !important; color: #611232 !important; text-align: center; background-color: #f7f4eb; padding: 6px; border-radius: 6px; border: 2px dashed #a57f2c; margin: 8px 0 4px 0; z-index: 2; position: relative; }}
            .info-text {{ margin: 4px 0; font-size: 0.85rem; z-index: 2; position: relative; }}
            .leyenda-posterior {{ font-size: 0.72rem !important; font-weight: 700 !important; color: #611232 !important; text-align: center; margin-top: 4px; margin-bottom: 0; z-index: 2; position: relative; }}
            
            .watermark-overlay {{
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                transform: rotate(-25deg);
                display: flex;
                flex-direction: column;
                justify-content: space-around;
                align-items: center;
                pointer-events: none;
                z-index: 0;
                overflow: hidden;
            }}
            .watermark-row {{
                display: flex;
                gap: 40px;
                white-space: nowrap;
                font-size: 1.05rem;
                font-weight: 900;
                color: transparent;
                -webkit-text-stroke: 1px rgba(97, 18, 50, 0.18);
                text-transform: uppercase;
                letter-spacing: 2px;
            }}
            .watermark-row:nth-child(even) {{
                transform: translateX(-40px);
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
                </div>
                <div class="titulo-ticket">FOLIO DE VACUNACION REGISTRADO</div>
                <p class="info-text"><b>Unidad:</b> {unidad}</p>
                <p class="info-text"><b>Vacuna de Interés:</b> {vacuna_interes}</p>
                <p class="info-text"><b>Paciente:</b> {nombre}</p>
                <p class="info-text"><b>CURP:</b> {curp}</p>
                <p class="info-text"><b>Grupo:</b> {grupo}</p>
                <div class="folio-grande">FOLIO: {folio}</div>
                <p class="leyenda-posterior">Posterior a su asistencia a la jornada de vacunación se le entregará un comprobante oficial.</p>
            </div>
            <div class="btn-container">
                <button class="btn btn-wa" onclick="compartirImagenWhatsApp()">💬 WhatsApp (Img)</button>
                <button class="btn btn-img" onclick="descargarCaptura()">📸 Descargar</button>
            </div>
            <script>
            function compartirImagenWhatsApp() {{
                const elemento = document.getElementById('comprobante-captura');
                html2canvas(elemento, {{ scale: 2 }}).then(canvas => {{
                    canvas.toBlob(blob => {{
                        const file = new File([blob], 'Folio_{folio}.png', {{ type: 'image/png' }});
                        const textoMensaje = `💉 *FOLIO DE VACUNACIÓN - VIGILE*\\nUnidad: {unidad}\\nVacuna: {vacuna_interes}\\nFolio: *{folio}*\\nPaciente: {nombre}\\nCURP: {curp}\\n⚠️ No es un comprobante de vacunación.\\nPosterior a su asistencia a la jornada de vacunación se le entregará un comprobante oficial.`;
                        if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                            navigator.share({{ files: [file], title: 'Folio de Vacunación', text: textoMensaje }}).catch(error => console.log('Error', error));
                        }} else {{
                            const enlace = document.createElement('a');
                            enlace.download = 'Folio_{folio}.png';
                            enlace.href = URL.createObjectURL(blob);
                            enlace.click();
                            window.open('https://wa.me/?text=' + encodeURIComponent(textoMensaje), '_blank');
                        }}
                    }}, 'image/png');
                }});
            }}
            function descargarCaptura() {{
                const elemento = document.getElementById('comprobante-captura');
                html2canvas(elemento, {{ scale: 2 }}).then(canvas => {{
                    const enlace = document.createElement('a');
                    enlace.download = 'Folio_{folio}.png';
                    enlace.href = canvas.toDataURL('image/png');
                    enlace.click();
                }});
            }}
            </script>
        </body>
        </html>
        """.format(
            unidad=st.session_state.nombre_unidad,
            vacuna_interes=p.get("vacuna_interes", "COVID-19"),
            nombre=p["nombre_completo"],
            curp=curp_mostrar,
            grupo=p["grupo_objetivo"],
            folio=p["folio"],
        )

        components.html(html_comprobante_component, height=330)
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
                " ADMINISTRATIVO EN CONTACTO CON ÁREAS CLÍNICAS Y FARMACIAS)"
            )
            st.session_state.input_digitos = "26"
            st.session_state.input_vacuna = "COVID-19"
            st.session_state.ant_cov = "SÍ"
            st.session_state.ant_inf = "SÍ"
            st.session_state.chk_discapacidad = True
            st.session_state.chk_fibrosis = False
            st.session_state.chk_hipertension = True
            st.rerun()

st.markdown(
    '<div class="section-title">1. Datos Generales y Fechas de Jornada</div>',
    unsafe_allow_html=True,
)
col_g1, col_g2, col_g3 = st.columns(3)
with col_g1:
    st.date_input(
        "Fecha de Registro",
        value=datetime.date.today(),
        format="DD/MM/YYYY",
        disabled=True,
    )
with col_g2:
    st.date_input(
        "Fecha de Aplicación (Autorizada)",
        value=val_fecha_app,
        format="DD/MM/YYYY",
        disabled=True,
    )
with col_g3:
    st.markdown(
        "**Folio Generado (Auto)**<br>`POR ASIGNAR`", unsafe_allow_html=True
    )

st.markdown(
    '<div class="section-title">2. Identificación del Paciente</div>',
    unsafe_allow_html=True,
)
col_n1, col_n2, col_n3 = st.columns(3)
with col_n1:
    paterno = st.text_input("Apellido Paterno *", key="input_paterno")
with col_n2:
    materno = st.text_input("Apellido Materno *", key="input_materno")
with col_n3:
    nombres = st.text_input("Nombre(s) *", key="input_nombres")

col_fn1, col_fn2, col_fn3 = st.columns(3)
with col_fn1:
    fecha_nacimiento = st.date_input(
        "Fecha de Nacimiento *",
        value=None,
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date.today(),
        format="DD/MM/YYYY",
        key="input_fnac",
    )
with col_fn2:
    sexo = st.selectbox(
        "Sexo *",
        options=["SELECCIONE UNA OPCIÓN", "HOMBRE", "MUJER"],
        key="input_sexo",
    )
with col_fn3:
    estado_nacimiento = st.selectbox(
        "Estado de Nacimiento *", options=estados_mexico, key="input_estnac"
    )

planes_o_embarazo = "NO"
if sexo == "MUJER":
    planes_o_embarazo = st.radio(
        "¿Está embarazada o tiene planes de embarazo?",
        options=["NO", "SÍ"],
        horizontal=True,
    )

calc_anos, calc_meses, calc_dias = (
    calcular_edad_detallada(fecha_nacimiento, val_fecha_app)
    if fecha_nacimiento
    else (0, 0, 0)
)
st.markdown(
    f'<div class="card-edad">📅 Edad calculada: {calc_anos} Años, {calc_meses}'
    f" Meses</div>",
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
with col_img2:
    try:
        st.image(
            "assets/INE.png",
            width=350,
            caption=(
                "📌 Ubicación de la Homoclave y Dígito Verificador en su Credencial"
                " para Votar (INE)"
            ),
        )
    except:
        try:
            st.image(
                "INE.png",
                width=350,
                caption=(
                    "📌 Ubicación de la Homoclave y Dígito Verificador en su"
                    " Credencial para Votar (INE)"
                ),
            )
        except:
            pass
st.markdown("<br>", unsafe_allow_html=True)

digitos_faltantes = st.text_input(
    "Homoclave y Dígito Verificador (Opcional - 2 últimos caracteres)",
    max_chars=2,
    key="input_digitos",
)
curp_algoritmica = generar_curp_algoritmica(
    paterno,
    materno,
    nombres,
    fecha_nacimiento,
    sexo,
    estado_nacimiento,
    digitos_faltantes,
)
curp_con_nacimiento = (
    f"{curp_algoritmica}/{estado_nacimiento.upper()}"
    if estado_nacimiento != "SELECCIONE UN ESTADO"
    and "COMPLETA" not in curp_algoritmica
    else curp_algoritmica
)

st.markdown(
    f'<div class="card-curp">🆔 CURP Generada: {curp_con_nacimiento}</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">3. Domicilio y Afiliación</div>',
    unsafe_allow_html=True,
)
estado_residencia = st.selectbox(
    "Estado de Residencia *", options=estados_mexico, key="input_estres"
)
col_dom1, col_dom2, col_dom3 = st.columns([2, 1, 1])
with col_dom1:
    calle = st.text_input("Calle *", key="input_calle")
with col_dom2:
    numero = st.text_input("No. (Ext / Int) *", key="input_num")
with col_dom3:
    colonia = st.text_input("Colonia *", key="input_col")
cuenta_derechohabiencia = st.selectbox(
    "¿Cuenta con derechohabiencia? *",
    options=["SELECCIONE UNA OPCIÓN", "NO", "SÍ"],
    key="input_derecho",
)

st.markdown(
    '<div class="section-title">4. Ocupación</div>', unsafe_allow_html=True
)
ocupacion = st.selectbox(
    "Seleccione su Ocupación *",
    options=[
        "SELECCIONE UNA OPCIÓN",
        (
            "PERSONAL DE SALUD (INCLUYE: PARAMÉDICO / PERSONAL SUPERVISOR Y"
            " ADMINISTRATIVO EN CONTACTO CON ÁREAS CLÍNICAS Y FARMACIAS)"
        ),
        "JUBILADO/A",
        "MAESTRO/A",
        "ADMINISTRATIVO/A",
        "TRABAJO EN GUARDERÍA",
        (
            "RESIDENTES Y PERSONAL DE CENTROS DE ASISTENCIA SOCIAL (CENTROS DE"
            " RECLUSIÓN Y/O READAPTACIÓN SOCIAL)"
        ),
        "PERSONAL DE GUARDERÍAS, CENDI O ESTANCIAS INFANTILES",
        "PERSONAL MILITAR",
        (
            "TRABAJADORES ACTIVOS DE PLATAFORMAS MARÍTIMAS Y REFINERÍAS"
            " (PEMEX)"
        ),
        "OTRAS PROFESIONES",
    ],
    key="input_ocupacion",
)

st.markdown(
    '<div class="section-title">5. Grupos de Riesgo y Comorbilidades</div>',
    unsafe_allow_html=True,
)
col_r1, col_r2 = st.columns(2)
with col_r1:
    vih = st.checkbox("VIH / SIDA", key="chk_vih")
    diabetes = st.checkbox("DIABETES MELLITUS", key="chk_diabetes")
    obesidad = st.checkbox("OBESIDAD MÓRBIDA", key="chk_obesidad")
    cardiopatias = st.checkbox(
        "CARDIOPATÍAS AGUDAS O CRÓNICAS", key="chk_cardiopatias"
    )
    discapacidades = st.checkbox("DISCAPACIDADES", key="chk_discapacidad")
with col_r2:
    cancer = st.checkbox("CÁNCER", key="chk_cancer")
    insuficiencia_renal = st.checkbox(
        "INSUFICIENCIA RENAL", key="chk_insufren"
    )
    hipertension = st.checkbox("HIPERTENSIÓN ARTERIAL", key="chk_hipertension")
    fibrosis_quistica = st.checkbox("FIBROSIS QUÍSTICA", key="chk_fibrosis")

st.markdown(
    '<div class="section-title">6. Antecedente Vacunal</div>',
    unsafe_allow_html=True,
)
col_av1, col_av2 = st.columns(2)
with col_av1:
    antecedente_covid = st.radio(
        "¿Cuenta con alguna dosis previa de COVID-19?",
        options=["SÍ", "NO", "LO DESCONOCE"],
        horizontal=True,
        key="ant_cov",
    )
with col_av2:
    antecedente_influenza = st.radio(
        "¿Cuenta con alguna dosis previa de Influenza?",
        options=["SÍ", "NO", "LO DESCONOCE"],
        horizontal=True,
        key="ant_inf",
    )

# --- 8. VACUNA DE INTERÉS ---
st.markdown(
    '<div class="section-title">8. Vacuna de Interés</div>',
    unsafe_allow_html=True,
)
vacuna_interes = st.radio(
    "Seleccione la vacuna de su interés para esta jornada:",
    options=["COVID-19", "INFLUENZA"],
    horizontal=True,
    key="input_vacuna",
)

edad_total_meses = (calc_anos * 12) + calc_meses

# --- LÓGICA DE GRUPO OBJETIVO UNIFICADA (COVID-19 / INFLUENZA) ---
grupo_sugerido = "POBLACIÓN GENERAL"

is_personal_salud = (
    "PERSONAL DE SALUD" in ocupacion
    or ocupacion
    == "PERSONAL DE SALUD (INCLUYE: PARAMÉDICO / PERSONAL SUPERVISOR Y ADMINISTRATIVO EN CONTACTO CON ÁREAS CLÍNICAS Y FARMACIAS)"
)
is_colectivo_riesgo = is_personal_salud or ocupacion in [
    "PERSONAL DE GUARDERÍAS, CENDI O ESTANCIAS INFANTILES",
    "RESIDENTES Y PERSONAL DE CENTROS DE ASISTENCIA SOCIAL (CENTROS DE RECLUSIÓN Y/O READAPTACIÓN SOCIAL)",
    "PERSONAL MILITAR",
    "TRABAJADORES ACTIVOS DE PLATAFORMAS MARÍTIMAS Y REFINERÍAS (PEMEX)",
]

if vacuna_interes == "COVID-19":
    if 6 <= edad_total_meses <= 59:
        grupo_sugerido = "6 A 59 MESES (VACUNACIÓN RUTINARIA / PRIMARIO)"
    elif planes_o_embarazo == "SÍ":
        grupo_sugerido = "PERSONAS EMBARAZADAS"
    elif calc_anos >= 60:
        grupo_sugerido = "60 AÑOS Y MÁS"
    elif is_personal_salud:
        grupo_sugerido = "PERSONAL DE SALUD"
    elif (
        vih
        or diabetes
        or obesidad
        or cardiopatias
        or cancer
        or insuficiencia_renal
        or discapacidades
        or fibrosis_quistica
        or hipertension
    ):
        grupo_sugerido = "COMORBILIDADES DE RIESGO (6 MESES A 59 AÑOS)"
else:  # INFLUENZA
    if 6 <= edad_total_meses <= 59:
        grupo_sugerido = "POBLACIÓN PEDIÁTRICA (6 A 59 MESES)"
    elif planes_o_embarazo == "SÍ":
        grupo_sugerido = "PERSONAS GESTANTES"
    elif is_colectivo_riesgo:
        grupo_sugerido = ocupacion
    elif calc_anos >= 60:
        grupo_sugerido = "POBLACIÓN ADULTA (60 Y MÁS)"
    elif (
        vih
        or diabetes
        or obesidad
        or cardiopatias
        or cancer
        or insuficiencia_renal
        or discapacidades
        or fibrosis_quistica
        or hipertension
    ):
        grupo_sugerido = "POBLACIÓN CON COMORBILIDADES (5 A 59 AÑOS)"

st.markdown(
    '<div class="section-title">7. Grupo Objetivo</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="card-grupo">🎯 Grupo Objetivo ({vacuna_interes}): {grupo_sugerido}</div>',
    unsafe_allow_html=True,
)

st.markdown("---")
if st.button("Registrarme para la jornada", use_container_width=True):
    if not fecha_nacimiento:
        st.error("Por favor seleccione la Fecha de Nacimiento.")
    elif not paterno or not nombres:
        st.error("Complete Apellido Paterno y Nombre(s).")
    elif sexo == "SELECCIONE UNA OPCIÓN":
        st.error("Seleccione una opción en Sexo.")
    elif cuenta_derechohabiencia == "SELECCIONE UNA OPCIÓN":
        st.error("Indique su derechohabiencia.")
    else:
        try:
            comorbilidades_dict = {
                "vih": vih,
                "diabetes": diabetes,
                "obesidad": obesidad,
                "cardiopatias": cardiopatias,
                "cancer": cancer,
                "insuficiencia_renal": insuficiencia_renal,
                "discapacidades": discapacidades,
                "fibrosis_quistica": fibrosis_quistica,
                "hipertension": hipertension,
            }

            datos_paciente = {
                "paterno": paterno,
                "materno": materno,
                "nombres": nombres,
                "fecha_nacimiento": fecha_nacimiento,
                "calc_anos": calc_anos,
                "calc_meses": calc_meses,
                "sexo": sexo,
                "calle": calle,
                "numero": numero,
                "colonia": colonia,
                "curp_con_nacimiento": curp_con_nacimiento,
                "cuenta_derechohabiencia": cuenta_derechohabiencia,
                "vacuna_interes": vacuna_interes,
                "grupo_sugerido": grupo_sugerido,
                "planes_o_embarazo": planes_o_embarazo,
                "ocupacion": ocupacion,
                "comorbilidades": comorbilidades_dict,
            }

            folio_asignado = guardar_registro_censal(
                sigla_url=sigla_url,
                sufijo_js=sufijo_js,
                tipo_jornada=st.session_state.tipo_jornada,
                val_fecha_app=val_fecha_app,
                nombre_unidad_completo=st.session_state.nombre_unidad,
                datos_paciente=datos_paciente,
            )

            st.session_state.ultimo_paciente_registrado = {
                "nombre_completo": f"{paterno.upper()} {materno.upper()} {nombres.upper()}",
                "curp_con_nacimiento": curp_con_nacimiento,
                "vacuna_interes": vacuna_interes,
                "grupo_objetivo": grupo_sugerido,
                "folio": folio_asignado,
            }
            st.rerun()

        except Exception as e:
            st.error("⚠️️ Error general al procesar el registro en Google Sheets:")
            st.exception(e)
