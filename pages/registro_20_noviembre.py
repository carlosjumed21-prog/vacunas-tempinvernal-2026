import datetime
import unicodedata
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from config import MAPA_SIGLAS_INVERSO, aplicar_configuracion_global
from utils.sheets import guardar_registro_censal_20_nov
from aviso_privacidad import mostrar_aviso_privacidad_si_necesario

aplicar_configuracion_global("Censo Nominal - 20 de Noviembre", "💉")

# --- MOSTRAR AVISO DE PRIVACIDAD OBLIGATORIO AL ENTRAR ---
mostrar_aviso_privacidad_si_necesario()

# --- INICIALIZACIÓN DE ESTADOS DE SESIÓN ---
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

if "ultimo_paciente_20n" not in st.session_state:
    st.session_state.ultimo_paciente_20n = None

v_form = st.session_state.form_version

# --- CARGA DINÁMICA DE CATÁLOGOS DESDE LA PESTAÑA 'LISTAS' ---
@st.cache_data(show_spinner=False)
def cargar_catalogos_excel():
    try:
        df = pd.read_excel("assets/lista vac.xlsx", sheet_name="LISTAS", header=0, dtype=str)
        
        def limpiar_columna(serie):
            if serie is not None and not serie.empty:
                return sorted([str(x).strip().upper() for x in serie.dropna().unique() if str(x).strip() and str(x).strip().upper() not in ["NAN", "NAT", ""]])
            return []

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
        .card-curp { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }
        .card-rfc { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; }
        input[type="text"] { text-transform: uppercase !important; font-size: 1.1rem !important; }
    </style>
""",
    unsafe_allow_html=True,
)

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
        return "FALTAN DATOS"
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
        return "FALTAN DATOS"
    nombres_lista = n.split()
    primer_nombre = nombres_lista[0] if nombres_lista else "X"
    if len(nombres_lista) > 1 and primer_nombre in ["JOSE", "MARIA", "MA.", "J."]:
        primer_nombre = nombres_lista[1]
    c1 = p[0] if p else "X"
    c2 = obtener_primera_vocal_interna(p)
    if m:
        c3 = m[0]
    elif len(p) > 1:
        c3 = p[1]
    else:
        c3 = "X"
    c4 = primer_nombre[0] if primer_nombre else "X"
    yy = str(fecha_nac.year)[-2:]
    mm = str(fecha_nac.month).zfill(2)
    dd = str(fecha_nac.day).zfill(2)
    return f"{c1}{c2}{c3}{c4}{yy}{mm}{dd}"

estados_mexico = list(estados_curp.keys())
estados_mexico.insert(0, "SELECCIONE UN ESTADO")

# --- MODAL DE COMPROBANTE CON CÓDIGO QR Y OPCIONES DE DESCARGA ---
@st.dialog("🎉 ¡REGISTRO EXITOSO - TICKET DIGITAL!")
def mostrar_modal_comprobante_20n():
    p = st.session_state.ultimo_paciente_20n
    if p:
        curp_mostrar = p.get("curp", "CURP")
        nombre_val = p["nombre_completo"]
        folio_val = p["folio"]
        vacuna_val = p.get("vacuna_interes", "AMBAS")
        rfc_val = p.get("rfc", "RFC")
        fecha_val = datetime.date.today().strftime("%d/%m/%Y")

        texto_qr = (
            f"CMN 20 DE NOVIEMBRE - REGISTRO NOMINAL\n"
            f"FOLIO: {folio_val}\n"
            f"PACIENTE: {nombre_val}\n"
            f"CURP: {curp_mostrar}\n"
            f"RFC: {rfc_val}\n"
            f"VACUNA: {vacuna_val}\n"
            f"FECHA: {fecha_val}\n"
            f"ESTADO: REGISTRADO"
        )

        html_comprobante_component = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
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
                        <span>CMN 20 DE NOVIEMBRE</span><span>CMN 20 DE NOVIEMBRE</span>
                    </div>
                    <div class="watermark-row">
                        <span>REGISTRO NOMINAL DE VACUNACIÓN</span><span>REGISTRO NOMINAL</span>
                    </div>
                    <div class="watermark-row">
                        <span>CMN 20 DE NOVIEMBRE</span><span>CMN 20 DE NOVIEMBRE</span>
                    </div>
                    <div class="watermark-row">
                        <span>REGISTRO NOMINAL DE VACUNACIÓN</span><span>REGISTRO NOMINAL</span>
                    </div>
                </div>
                <div class="titulo-ticket">CMN 20 DE NOVIEMBRE - REGISTRO EXITOSO</div>
                <div class="cuerpo-ticket">
                    <div class="info-container">
                        <p class="info-text"><b>Paciente:</b> {nombre_val}</p>
                        <p class="info-text"><b>CURP:</b> {curp_mostrar}</p>
                        <p class="info-text"><b>RFC:</b> {rfc_val}</p>
                        <p class="info-text"><b>Vacuna:</b> {vacuna_val}</p>
                    </div>
                    <div class="qr-container">
                        <canvas id="qr-canvas"></canvas>
                    </div>
                </div>
                <div class="folio-grande">Folio Asignado: {folio_val}</div>
                <p class="leyenda-posterior">Guarde este comprobante para su presentación en el módulo de vacunación.</p>
            </div>
            <div class="btn-container">
                <button class="btn btn-wa" onclick="compartirImagenWhatsApp()">💬 WhatsApp (Img)</button>
                <button class="btn btn-img" onclick="descargarCaptura()">📸 Descargar</button>
            </div>
            <script>
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
                            const textoMensaje = `💉 *REGISTRO CMN 20 DE NOVIEMBRE*\\nPaciente: {nombre_val}\\nFolio: *{folio_val}*\\nCURP: {curp_mostrar}\\nVacuna: {vacuna_val}\\nGuarde este comprobante para su validación.`;
                            
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
        if st.button("➕ Nuevo Registro (Reiniciar Formulario)", use_container_width=True):
            st.session_state.ultimo_paciente_20n = None
            st.session_state.form_version += 1
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

dh = st.selectbox("¿Cuenta con derechohabiencia? *", options=["SELECCIONE", "SÍ", "NO"], key=f"20n_dh_{v_form}")

tipo_dh = "NO APLICA"
trabaja_cmn = "NO"
num_trabajador = ""
personal_salud_val = "NO"
categoria = "NO APLICA"
servicio = "NO APLICA"
coordinacion = "NO APLICA"
turno_val = "NO APLICA"

if dh == "SÍ":
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        tipo_dh = st.selectbox("Tipo de DH *", options=["SELECCIONE"] + opt_tipo_dh, key=f"20n_tipo_dh_{v_form}")
    with col_d2:
        trabaja_cmn = st.radio("¿Trabaja en CMN 20 de Noviembre?", options=["NO", "SÍ"], horizontal=True, key=f"20n_trabaja_cmn_{v_form}")

    if trabaja_cmn == "SÍ":
        num_trabajador = st.text_input("Número de Trabajador", key=f"20n_num_trabajador_{v_form}")
        
        personal_salud_radio = st.radio("¿Es usted Personal de Salud?", options=["NO", "SÍ"], horizontal=True, key=f"20n_pers_salud_radio_{v_form}")
        personal_salud_val = personal_salud_radio

        if personal_salud_val == "SÍ":
            col_lab1, col_lab2, col_lab3, col_lab4 = st.columns(4)
            with col_lab1:
                categoria = st.selectbox("Categoría", options=["SELECCIONE"] + opt_categoria, key=f"20n_categoria_{v_form}")
            with col_lab2:
                servicio = st.selectbox("Servicio", options=["SELECCIONE"] + opt_servicio, key=f"20n_servicio_{v_form}")
            with col_lab3:
                coordinacion = st.selectbox("Coordinación", options=["SELECCIONE"] + opt_coordinacion, key=f"20n_coordinacion_{v_form}")
            with col_lab4:
                turno_full = st.selectbox("Turno", options=["SELECCIONE"] + opt_turno, key=f"20n_turno_{v_form}")

            turno_map = {"MATUTINO": "M", "VESPERTINO": "V", "NOCTURNO": "N", "JORNADA ACUMULADA": "JA"}
            turno_val = turno_map.get(turno_full.upper(), turno_full[:1] if turno_full != "SELECCIONE" else "")

# --- 2. IDENTIFICACIÓN DEL PACIENTE ---
st.markdown('<div class="section-title">2. Identificación del Paciente</div>', unsafe_allow_html=True)
col_n1, col_n2, col_n3 = st.columns(3)
with col_n1:
    paterno = st.text_input("Apellido Paterno *", key=f"20n_paterno_{v_form}")
with col_n2:
    materno = st.text_input("Apellido Materno (Opcional)", key=f"20n_materno_{v_form}")
with col_n3:
    nombres = st.text_input("Nombre(s) *", key=f"20n_nombres_{v_form}")

col_fn1, col_fn2, col_fn3 = st.columns(3)
with col_fn1:
    fecha_nacimiento = st.date_input(
        "Fecha de Nacimiento *",
        value=None,
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date.today(),
        format="DD/MM/YYYY",
        key=f"20n_fnac_{v_form}",
    )
with col_fn2:
    sexo = st.selectbox("Sexo *", options=["SELECCIONE UNA OPCIÓN", "HOMBRE", "MUJER"], key=f"20n_sexo_{v_form}")
with col_fn3:
    edo_nac = st.selectbox("Estado de Nacimiento (Edo Nac) *", options=estados_mexico, key=f"20n_edonac_{v_form}")

lista_municipios = municipios_por_estado.get(edo_nac, ["OTRO (ESPECIFIQUE)"])
if edo_nac in municipios_por_estado:
    muni_nac = st.selectbox("Municipio / Alcaldía de Nacimiento (Muni Nac) *", options=lista_municipios, key=f"20n_muninac_sel_{v_form}")
else:
    muni_nac = st.text_input("Municipio / Alcaldía de Nacimiento (Muni Nac) *", key=f"20n_muninac_txt_{v_form}")

embarazo = "NO"
if sexo == "MUJER":
    embarazo = st.radio("¿Embarazo?", options=["NO", "SÍ"], horizontal=True, key=f"20n_embarazo_{v_form}")

calc_anos, calc_meses, calc_dias = calcular_edad_detallada(fecha_nacimiento, val_fecha_app) if fecha_nacimiento else (0, 0, 0)
st.markdown(f'<div class="card-edad">📅 Edad calculada: {calc_anos} Años, {calc_meses} Meses</div>', unsafe_allow_html=True)

edad_total_meses = (calc_anos * 12) + calc_meses
es_pediatrico_59m = 6 <= edad_total_meses <= 59

digitos_faltantes = st.text_input("Homoclave y Dígito Verificador (Opcional - CURP)", max_chars=2, key=f"20n_digitos_{v_form}")
curp_algoritmica = generar_curp_algoritmica(paterno, materno, nombres, fecha_nacimiento, sexo, edo_nac, digitos_faltantes)
curp_con_nacimiento = f"{curp_algoritmica}/{edo_nac.upper()}" if edo_nac != "SELECCIONE UN ESTADO" and "FALTAN" not in curp_algoritmica else curp_algoritmica
st.markdown(f'<div class="card-curp">🆔 CURP Generada: {curp_con_nacimiento}</div>', unsafe_allow_html=True)

rfc_generado = generar_rfc_algoritmico(paterno, materno, nombres, fecha_nacimiento)
st.markdown(f'<div class="card-rfc">📋 RFC Generado: {rfc_generado}</div>', unsafe_allow_html=True)

# --- 3. DOMICILIO Y AFILIACIÓN ---
st.markdown('<div class="section-title">3. Domicilio y Afiliación</div>', unsafe_allow_html=True)
estado_residencia = st.selectbox("Estado de Residencia *", options=estados_mexico, key=f"20n_estres_{v_form}")
col_dom1, col_dom2, col_dom3 = st.columns([2, 1, 1])
with col_dom1:
    calle = st.text_input("Calle *", key=f"20n_calle_{v_form}")
with col_dom2:
    numero = st.text_input("No. (Ext / Int) *", key=f"20n_num_{v_form}")
with col_dom3:
    colonia = st.text_input("Colonia *", key=f"20n_col_{v_form}")

# --- 5. GRUPOS DE RIESGO Y COMORBILIDADES ---
st.markdown('<div class="section-title">5. Grupos de Riesgo y Comorbilidades</div>', unsafe_allow_html=True)
col_r1, col_r2 = st.columns(2)
with col_r1:
    vih = st.checkbox("VIH / SIDA", key=f"20n_vih_{v_form}")
    diabetes = st.checkbox("DIABETES MELLITUS", key=f"20n_diabetes_{v_form}")
    obesidad = st.checkbox("OBESIDAD MÓRBIDA", key=f"20n_obesidad_{v_form}")
    cardiopatias = st.checkbox("CARDIOPATÍAS AGUDAS O CRÓNICAS", key=f"20n_cardiopatias_{v_form}")
    discapacidades = st.checkbox("DISCAPACIDADES", key=f"20n_discapacidad_{v_form}")
with col_r2:
    cancer = st.checkbox("CÁNCER", key=f"20n_cancer_{v_form}")
    insuficiencia_renal = st.checkbox("INSUFICIENCIA RENAL", key=f"20n_insufren_{v_form}")
    hipertension = st.checkbox("HIPERTENSIÓN ARTERIAL", key=f"20n_hipertension_{v_form}")
    fibrosis_quistica = st.checkbox("FIBROSIS QUÍSTICA", key=f"20n_fibrosis_{v_form}")

# --- 6. ANTECEDENTE VACUNAL Y VACUNA DE INTERÉS ---
st.markdown('<div class="section-title">6. Antecedente Vacunal y Vacuna de Interés</div>', unsafe_allow_html=True)
col_av1, col_av2 = st.columns(2)
with col_av1:
    antecedente_covid = st.radio("¿Dosis previa COVID-19?", options=["SÍ", "NO", "LO DESCONOCE"], horizontal=True, key=f"20n_ant_cov_{v_form}")
with col_av2:
    antecedente_influenza = st.radio("¿Dosis previa Influenza?", options=["SÍ", "NO", "LO DESCONOCE"], horizontal=True, key=f"20n_ant_inf_{v_form}")

vacuna_interes = st.radio("Vacuna de interés:", options=["AMBAS", "COVID-19", "INFLUENZA"], horizontal=True, key=f"20n_vacuna_{v_form}")

st.markdown("---")
if st.button("Registrar en CMN 20 de Noviembre", use_container_width=True):
    if not fecha_nacimiento:
        st.error("Seleccione la fecha de nacimiento.")
    elif not paterno or not nombres:
        st.error("Complete Apellido Paterno y Nombre(s).")
    elif dh == "SELECCIONE":
        st.error("Indique si cuenta con derechohabiencia.")
    elif dh == "SÍ" and tipo_dh == "SELECCIONE":
        st.error("Seleccione el Tipo de DH.")
    elif sexo == "SELECCIONE UNA OPCIÓN":
        st.error("Seleccione el Sexo.")
    else:
        try:
            fn_dia = str(fecha_nacimiento.day).zfill(2)
            fn_mes = str(fecha_nacimiento.month).zfill(2)
            fn_ano = str(fecha_nacimiento.year)

            comorbilidades_dict = {
                "vih": vih, "diabetes": diabetes, "obesidad": obesidad,
                "cardiopatias": cardiopatias, "cancer": cancer,
                "insuficiencia_renal": insuficiencia_renal,
                "discapacidades": discapacidades,
                "fibrosis_quistica": fibrosis_quistica,
                "hipertension": hipertension
            }

            datos_20n = {
                "rfc": rfc_generado,
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
                "muni_nac": muni_nac.upper() if muni_nac else "",
                "fn_dia": fn_dia,
                "fn_mes": fn_mes,
                "fn_ano": fn_ano,
                "anos": calc_anos,
                "meses": calc_meses,
                "sexo": sexo,
                "embarazo": embarazo,
                "curp": curp_con_nacimiento,
                "calle": calle.upper(),
                "numero": numero.upper(),
                "colonia": colonia.upper(),
                "vacuna_interes": vacuna_interes,
                "comorbilidades": comorbilidades_dict,
                "tipo_jornada": st.session_state.tipo_jornada,
                "val_fecha_app": val_fecha_app
            }

            folio_asignado = guardar_registro_censal_20_nov(datos_20n)

            st.session_state.ultimo_paciente_20n = {
                "nombre_completo": f"{paterno.upper()} {materno.upper() if materno else ''} {nombres.upper()}".strip(),
                "folio": folio_asignado,
                "rfc": rfc_generado,
                "curp": curp_con_nacimiento,
                "vacuna_interes": vacuna_interes,
            }
            st.rerun()

        except Exception as e:
            st.error("⚠️ Error al registrar en la hoja de Google Sheets del CMN 20 de Noviembre:")
            st.exception(e)
