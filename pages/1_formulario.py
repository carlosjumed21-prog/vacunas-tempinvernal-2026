import datetime
import unicodedata
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
from config import MAPA_SIGLAS_INVERSO, aplicar_configuracion_global
from utils.sheets import guardar_registro_censal
from aviso_privacidad import mostrar_aviso_privacidad_si_necesario

aplicar_configuracion_global("Censo Nominal - Registro", "💉")

# --- LLAMADA A LA VENTANA EMERGENTE (MODAL) DEL AVISO DE PRIVACIDAD ---
mostrar_aviso_privacidad_si_necesario()

# --- OCULTAR LA BARRA SUPERIOR NATIVA DE STREAMLIT ---
st.markdown(
    """
    <style>
        header {visibility: hidden;}
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

if "registros_censales" not in st.session_state:
    st.session_state.registros_censales = []
if "ultimo_paciente_registrado" not in st.session_state:
    st.session_state.ultimo_paciente_registrado = None

# Inicializar estados en None para evitar selecciones automáticas
if "ant_cov" not in st.session_state:
    st.session_state.ant_cov = None
if "ant_inf" not in st.session_state:
    st.session_state.ant_inf = None
if "input_vacuna" not in st.session_state:
    st.session_state.input_vacuna = None


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

        nombre_hoja = (
            "COVID" if biologico and biologico.upper() in ["COVID-19", "COVID"] else "Influenza"
        )
        worksheet = sh.worksheet(nombre_hoja)

        registros = worksheet.get_all_records()
        return registros
    except Exception:
        return []


def determinar_grupo_desde_sheets(
    biologico,
    edad_meses,
    edad_anos,
    gestante,
    ocupacion,
    comorbilidades_activas,
):
    biologico_a_consultar = (
        "Influenza" if biologico and biologico in ["INFLUENZA", "AMBAS"] else "COVID"
    )
    filas_sheets = obtener_recomendaciones_sheets(biologico_a_consultar)

    if not filas_sheets:
        return determinar_grupo_sugerido_fallback(
            biologico,
            edad_meses,
            edad_anos,
            gestante,
            ocupacion,
            comorbilidades_activas,
        )

    for fila in filas_sheets:
        grupo_blanco = str(fila.get("Grupos blancos de la intervención", ""))
        categoria = str(fila.get("Categoria", ""))
        gb_lower = grupo_blanco.lower()

        if gestante == "SÍ" and (
            "gestante" in gb_lower or "embarazo" in gb_lower
        ):
            return f"{grupo_blanco} ({categoria})"

        if "meses" in gb_lower:
            if "6 a 18 meses" in gb_lower and 6 <= edad_meses <= 18:
                return f"{grupo_blanco} ({categoria})"
            elif "19 a 59 meses" in gb_lower and 19 <= edad_meses <= 59:
                return f"{grupo_blanco} ({categoria})"
            elif "6 a 59 meses" in gb_lower and 6 <= edad_meses <= 59:
                return f"{grupo_blanco} ({categoria})"

        if "años" in gb_lower or "mas" in gb_lower or "y mas" in gb_lower:
            if (
                ("60" in gb_lower or "mas" in gb_lower)
                and edad_anos >= 60
                and "comorbilidades" not in gb_lower
            ):
                return f"{grupo_blanco} ({categoria})"

        if "personal de salud" in gb_lower and (
            "PERSONAL DE SALUD" in ocupacion.upper()
        ):
            return f"{grupo_blanco} ({categoria})"

        if comorbilidades_activas and "comorbilidades" in gb_lower:
            if (
                "5 a 8 años" in gb_lower
                and 5 <= edad_anos <= 8
                and comorbilidades_activas
            ):
                return f"{grupo_blanco} ({categoria})"
            elif (
                "9 a 59 años" in gb_lower
                and 9 <= edad_anos <= 59
                and comorbilidades_activas
            ):
                return f"{grupo_blanco} ({categoria})"
            elif (
                "6 meses a 59 años" in gb_lower
                and 0.5 <= edad_anos <= 59
                and comorbilidades_activas
            ):
                return f"{grupo_blanco} ({categoria})"

    return determinar_grupo_sugerido_fallback(
        biologico,
        edad_meses,
        edad_anos,
        gestante,
        ocupacion,
        comorbilidades_activas,
    )


def determinar_grupo_sugerido_fallback(
    vacuna_interes,
    edad_total_meses,
    calc_anos,
    personas_gestantes,
    ocupacion,
    tiene_comorbilidades,
):
    is_personal_salud = "PERSONAL DE SALUD" in ocupacion.upper()
    is_colectivo_riesgo = is_personal_salud or ocupacion in [
        "PERSONAL DE GUARDERÍAS, CENDI O ESTANCIAS INFANTILES",
        "RESIDENTES Y PERSONAL DE CENTROS DE ASISTENCIA SOCIAL (CENTROS DE RECLUSIÓN Y/O READAPTACIÓN SOCIAL)",
        "PERSONAL MILITAR",
        "TRABAJADORES ACTIVOS DE PLATAFORMAS MARÍTIMAS Y REFINERÍAS (PEMEX)",
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
            return (
                "6 A 59 MESES (VACUNACIÓN RUTINARIA / PRIMARIO) [Población Objetivo]"
            )
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
            return (
                "POBLACIÓN PEDIÁTRICA (6 A 59 MESES) [Población Objetivo]"
            )
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
            .qr-container {{ width: 110px; text-align: center; }}
            .qr-container canvas {{ width: 100% !important; height: auto !important; border: 2px solid #a57f2c; border-radius: 6px; padding: 3px; background: white; display: block; }}
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
                window.addEventListener('DOMContentLoaded', (event) => {{
                    var qr = new QRious({{
                        element: document.getElementById('qr-canvas'),
                        value: {repr(texto_qr)},
                        size: 250
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
                "fecha_nac_str",
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
                "chk_personas_embarazadas",
                "chk_personal_salud_riesgo",
                "chk_vih",
                "chk_diabetes",
                "chk_obesidad",
                "chk_cardiopatias",
                "chk_enfermedad_pulmonar",
                "chk_cancer",
                "chk_cardiacas_congenitas",
                "chk_insufren",
                "chk_inmunosupresion",
                "chk_discapacidad",
                "chk_fibrosis",
                "chk_hipertension",
                "chk_otro",
                "txt_otro_riesgo",
                "chk_gestante",
            ]
            for k in keys_a_limpiar:
                if k in st.session_state:
                    st.session_state[k] = (
                        False
                        if "chk_" in k
                        else (
                            "SELECCIONE UNA OPCIÓN"
                            if "input_sexo" in k
                            or "input_derecho" in k
                            or "input_estnac" in k
                            or "input_estres" in k
                            or "input_ocupacion" in k
                            else (None if "ant_" in k or "input_vacuna" in k else "")
                        )
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
            st.session_state.input_nombres = "CARLOS"
            st.session_state.fecha_nac_str = "15/10/1993"
            st.session_state.input_sexo = "HOMBRE"
            st.session_state.input_estnac = "CIUDAD DE MÉXICO"
            st.session_state.input_estres = "CIUDAD DE MÉXICO"
            st.session_state.input_calle = "AV. INSURGENTES SUR"
            st.session_state.input_num = "123 INT. 4B"
            st.session_state.input_col = "ROSA RIVAS"
            st.session_state.input_derecho = "SÍ"
            st.session_state.input_ocupacion = (
                "PERSONAL DE SALUD (INCLUYE: PARAMÉDICO / PERSONAL SUPERVISOR Y"
                " ADMINISTRATIVO EN ÁREAS CLÍNICAS Y FARMACIAS)"
            )
            st.session_state.input_digitos = "26"
            st.session_state.input_vacuna = "AMBAS"
            st.session_state.ant_cov = "SÍ"
            st.session_state.ant_inf = "SÍ"
            st.session_state.chk_gestante = "NO"
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

# --- CALENDARIO INTERACTIVO ESTILO TARJETA CON SELECTORES DE MES Y AÑO ---
st.markdown(
    "<label style='font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important;'>Fecha de Nacimiento *</label>",
    unsafe_allow_html=True,
)

if "fecha_nac_str" not in st.session_state:
    st.session_state.fecha_nac_str = "15/10/1993"

fecha_inicial_iso = ""
val_str = st.session_state.fecha_nac_str
if val_str:
    try:
        if "/" in val_str:
            partes = val_str.split("/")
            if len(partes) == 3:
                fecha_inicial_iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
        else:
            fecha_inicial_iso = val_str
    except:
        pass

componente_calendario_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{ font-family: sans-serif; background-color: transparent; margin: 0; padding: 2px; }}
    .calendar-card {{
        background: #ffffff;
        border: 2px solid #1e5b4f;
        border-radius: 8px;
        padding: 12px;
        max-width: 100%;
        box-sizing: border-box;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }}
    .calendar-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        gap: 6px;
    }}
    .calendar-header select, .calendar-header button {{
        padding: 6px 8px;
        font-size: 0.95rem;
        border: 1px solid #a57f2c;
        border-radius: 4px;
        background: #fff;
        cursor: pointer;
    }}
    .calendar-header select {{ font-weight: bold; color: #1e5b4f; flex: 1; }}
    .calendar-header button {{ font-weight: bold; color: #611232; background: #f7f4eb; }}
    .calendar-grid {{
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        text-align: center;
        gap: 4px;
    }}
    .calendar-day-name {{
        font-size: 0.8rem;
        font-weight: bold;
        color: #611232;
        padding-bottom: 6px;
    }}
    .calendar-day {{
        padding: 8px 0;
        font-size: 0.95rem;
        border-radius: 4px;
        cursor: pointer;
        color: #161a1d;
        font-weight: 600;
    }}
    .calendar-day:hover {{
        background-color: #f7f4eb;
    }}
    .calendar-day.selected {{
        background-color: #1e5b4f;
        color: white;
        font-weight: bold;
    }}
    .calendar-day.other-month {{
        color: #ccc;
    }}
</style>
</head>
<body>

<div class="calendar-card">
    <div class="calendar-header">
        <button onclick="cambiarMes(-1)">&#10094;</button>
        <select id="select-month" onchange="actualizarCalendarioDesdeSelect()">
            <option value="0">Enero</option>
            <option value="1">Febrero</option>
            <option value="2">Marzo</option>
            <option value="3">Abril</option>
            <option value="4">Mayo</option>
            <option value="5">Junio</option>
            <option value="6">Julio</option>
            <option value="7">Agosto</option>
            <option value="8">Septiembre</option>
            <option value="9">Octubre</option>
            <option value="10">Noviembre</option>
            <option value="11">Diciembre</option>
        </select>
        <select id="select-year" onchange="actualizarCalendarioDesdeSelect()"></select>
        <button onclick="cambiarMes(1)">&#10095;</button>
    </div>
    <div class="calendar-grid">
        <div class="calendar-day-name">L</div>
        <div class="calendar-day-name">M</div>
        <div class="calendar-day-name">X</div>
        <div class="calendar-day-name">J</div>
        <div class="calendar-day-name">V</div>
        <div class="calendar-day-name">S</div>
        <div class="calendar-day-name">D</div>
    </div>
    <div class="calendar-grid" id="calendar-days-body"></div>
</div>

<script>
    let fechaActual = new Date(1993, 9, 15);
    let fechaSeleccionada = {f"new Date('{fecha_inicial_iso}')" if fecha_inicial_iso else 'null'};

    function inicializarAnios() {{
        const selectYear = document.getElementById('select-year');
        const anioActual = new Date().getFullYear();
        for (let y = anioActual; y >= 1920; y--) {{
            let opt = document.createElement('option');
            opt.value = y;
            opt.text = y;
            selectYear.appendChild(opt);
        }}
    }}

    function renderCalendario() {{
        const year = fechaActual.getFullYear();
        const month = fechaActual.getMonth();

        document.getElementById('select-month').value = month;
        document.getElementById('select-year').value = year;

        const body = document.getElementById('calendar-days-body');
        body.innerHTML = '';

        const primerDiaMes = new Date(year, month, 1);
        let diaSemana = primerDiaMes.getDay();
        diaSemana = (diaSemana === 0) ? 6 : diaSemana - 1;

        const ultimoDiaMes = new Date(year, month + 1, 0).getDate();
        const ultimoDiaMesAnterior = new Date(year, month, 0).getDate();

        for (let i = diaSemana - 1; i >= 0; i--) {{
            let div = document.createElement('div');
            div.className = 'calendar-day other-month';
            div.innerText = ultimoDiaMesAnterior - i;
            body.appendChild(div);
        }}

        for (let d = 1; d <= ultimoDiaMes; d++) {{
            let div = document.createElement('div');
            div.className = 'calendar-day';
            div.innerText = d;
            
            if (fechaSeleccionada && 
                fechaSeleccionada.getFullYear() === year && 
                fechaSeleccionada.getMonth() === month && 
                fechaSeleccionada.getDate() === d) {{
                div.classList.add('selected');
            }}

            div.onclick = function() {{
                fechaSeleccionada = new Date(year, month, d);
                renderCalendario();
                
                let yyyy = fechaSeleccionada.getFullYear();
                let mm = String(fechaSeleccionada.getMonth() + 1).padStart(2, '0');
                let dd = String(fechaSeleccionada.getDate()).padStart(2, '0');
                let fechaFormateada = dd + '/' + mm + '/' + yyyy;

                const docInput = window.parent.document.querySelector('input[aria-label="Fecha Seleccionada"]');
                if (docInput) {{
                    docInput.value = fechaFormateada;
                    docInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    docInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }};
            body.appendChild(div);
        }}
    }}

    function cambiarMes(delta) {{
        fechaActual.setMonth(fechaActual.getMonth() + delta);
        renderCalendario();
    }}

    function actualizarCalendarioDesdeSelect() {{
        const m = parseInt(document.getElementById('select-month').value);
        const y = parseInt(document.getElementById('select-year').value);
        fechaActual.setFullYear(y);
        fechaActual.setMonth(m);
        renderCalendario();
    }}

    inicializarAnios();
    if (fechaSeleccionada) {{
        fechaActual = new Date(fechaSeleccionada);
    }}
    renderCalendario();
</script>

</body>
</html>
"""

components.html(componente_calendario_html, height=290)

def actualizar_fecha_callback():
    pass

fecha_nac_str = st.text_input(
    "Fecha Seleccionada", 
    key="fecha_nac_str", 
    label_visibility="collapsed", 
    placeholder="DD/MM/YYYY",
    on_change=actualizar_fecha_callback
)

fecha_nacimiento = None
if st.session_state.get("fecha_nac_str"):
    try:
        fecha_nacimiento = datetime.datetime.strptime(st.session_state.fecha_nac_str, "%d/%m/%Y").date()
    except:
        try:
            fecha_nacimiento = datetime.datetime.strptime(st.session_state.fecha_nac_str, "%Y-%m-%d").date()
        except:
            pass

col_fn2, col_fn3 = st.columns(2)
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

personas_gestantes = "NO"
if sexo == "MUJER":
    personas_gestantes = st.radio(
        "¿Es una persona gestante o tiene planes de embarazo?",
        options=["NO", "SÍ"],
        horizontal=True,
        key="chk_gestante",
    )

calc_anos, calc_meses, calc_dias = (
    calcular_edad_detallada(fecha_nacimiento, val_fecha_app)
    if fecha_nacimiento
    else (0, 0, 0)
)
st.markdown(
    f'<div class="card-edad">📅 Edad calculada: {calc_anos} Años, {calc_meses}'
    " Meses</div>",
    unsafe_allow_html=True,
)

edad_total_meses = (calc_anos * 12) + calc_meses
es_rango_infantil = 6 <= edad_total_meses <= 59

st.markdown("<br>", unsafe_allow_html=True)
col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
with col_img2:
    try:
        st.image(
            "assets/INE.png",
            width=350,
            caption=(
                "📌 Ubicación del Dígito Verificador en su Credencial"
                " para Votar (INE)"
            ),
        )
    except:
        try:
            st.image(
                "INE.png",
                width=350,
                caption=(
                    "📌 Ubicación del Dígito Verificador en su"
                    " Credencial para Votar (INE)"
                ),
            )
        except:
            pass
st.markdown("<br>", unsafe_allow_html=True)

digitos_faltantes = st.text_input(
    "Dígito Verificador (Opcional - Últimos caracteres)",
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
    f'<div class="card-curp">🆔 CURP / RFC Generada: {curp_con_nacimiento}</div>',
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

lista_ocupaciones = [
    "SELECCIONE UNA OPCIÓN",
    "NO APLICA",
    (
        "PERSONAL DE SALUD (INCLUYE: PARAMÉDICO / PERSONAL SUPERVISOR Y"
        " ADMINISTRATIVO EN ÁREAS CLÍNICAS Y FARMACIAS)"
    ),
    "ESTUDIANTE (PREESCOLAR, PRIMARIA, SECUNDARIA, BACHILLERATO/PREPARATORIA)",
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
]

if es_rango_infantil:
    st.info("ℹ️ Menor de 6 a 59 meses: Ocupación asignada automáticamente como 'NO APLICA'.")
    st.session_state.input_ocupacion = "NO APLICA"
    ocupacion = st.selectbox(
        "Seleccione su Ocupación *",
        options=lista_ocupaciones,
        index=lista_ocupaciones.index("NO APLICA"),
        key="input_ocupacion",
        disabled=True,
    )
else:
    ocupacion = st.selectbox(
        "Seleccione su Ocupación *",
        options=lista_ocupaciones,
        key="input_ocupacion",
    )

st.markdown(
    '<div class="section-title">5. Grupos de Riesgo y Comorbilidades</div>',
    unsafe_allow_html=True,
)

es_personal_salud_ocupacion = "PERSONAL DE SALUD" in ocupacion.upper()
es_embarazada_activa = (sexo == "MUJER" and personas_gestantes == "SÍ")

st.session_state.chk_personas_embarazadas = es_embarazada_activa
st.session_state.chk_personal_salud_riesgo = es_personal_salud_ocupacion

col_r1, col_r2 = st.columns(2)
with col_r1:
    personas_embarazadas = st.checkbox(
        "EMBARAZADAS", 
        disabled=es_embarazada_activa,
        key="chk_personas_embarazadas"
    )
    personal_salud_riesgo = st.checkbox(
        "PERSONAL DE SALUD", 
        disabled=es_personal_salud_ocupacion,
        key="chk_personal_salud_riesgo"
    )
    vih = st.checkbox("VIH/sida", key="chk_vih")
    diabetes = st.checkbox("DIABETES MELLITUS", key="chk_diabetes")
    obesidad = st.checkbox("OBESIDAD MÓRBIDA", key="chk_obesidad")
    cardiopatias = st.checkbox("CARDIOPATÍAS AGUDAS O CRÓNICAS", key="chk_cardiopatias")
    enfermedad_pulmonar = st.checkbox("ENFERMEDAD PULMONAR CRÓNICA, INCLUYE EPOC Y ASMA", key="chk_enfermedad_pulmonar")

with col_r2:
    cancer = st.checkbox("CÁNCER", key="chk_cancer")
    cardiacas_congenitas = st.checkbox("ENFERMEDADES CARDIACAS O PULMONARES CONGÉNITAS U OTROS PADECIMIENTOS CRÓNICOS QUE REQUIERAN CONSUMO PROLONGADO DE SALICILATOS*", key="chk_cardiacas_congenitas")
    insuficiencia_renal = st.checkbox("INSUFICIENCIA RENAL", key="chk_insufren")
    inmunosupresion = st.checkbox("INMUNOSUPRESIÓN ADQUIRIDA POR ENFERMEDAD O TRATAMIENTO, EXCEPTO VIH/sida", key="chk_inmunosupresion")
    discapacidades = st.checkbox("DISCAPACIDADES", key="chk_discapacidad")
    fibrosis_quistica = st.checkbox("FIBROSIS QUÍSTICA", key="chk_fibrosis")
    hipertension = st.checkbox("HIPERTENSIÓN ARTERIAL", key="chk_hipertension")
    
    otro_riesgo = st.checkbox("OTRO", key="chk_otro")
    texto_otro_riesgo = ""
    if otro_riesgo:
        texto_otro_riesgo = st.text_input("Especifique otro grupo de riesgo:", key="txt_otro_riesgo")

st.markdown(
    '<div class="section-title">6. Antecedente Vacunal</div>',
    unsafe_allow_html=True,
)
col_av1, col_av2 = st.columns(2)
with col_av1:
    antecedente_covid = st.radio(
        "¿Cuenta con alguna dosis previa de COVID-19? *",
        options=["SÍ", "NO", "LO DESCONOCE"],
        index=None,
        horizontal=True,
        key="ant_cov",
    )
with col_av2:
    antecedente_influenza = st.radio(
        "¿Cuenta con alguna dosis previa de Influenza? *",
        options=["SÍ", "NO", "LO DESCONOCE"],
        index=None,
        horizontal=True,
        key="ant_inf",
    )

st.markdown(
    '<div class="section-title">8. Vacuna de Interés</div>',
    unsafe_allow_html=True,
)
vacuna_interes = st.radio(
    "Seleccione la vacuna de su interés para esta jornada: *",
    options=["AMBAS", "COVID-19", "INFLUENZA"],
    index=None,
    horizontal=True,
    key="input_vacuna",
)

if fecha_nacimiento is None or not vacuna_interes:
    grupo_sugerido = "POR ASIGNAR"
else:
    tiene_comorbilidades = (
        vih or diabetes or obesidad or cardiopatias or enfermedad_pulmonar or 
        cancer or cardiacas_congenitas or insuficiencia_renal or inmunosupresion or 
        discapacidades or fibrosis_quistica or hipertension or otro_riesgo or personas_embarazadas or personal_salud_riesgo
    )

    grupo_sugerido = determinar_grupo_desde_sheets(
        biologico=vacuna_interes,
        edad_meses=edad_total_meses,
        edad_anos=calc_anos,
        gestante="SÍ" if personas_embarazadas else personas_gestantes,
        ocupacion=ocupacion,
        comorbilidades_activas=tiene_comorbilidades
    )

st.markdown(
    '<div class="section-title">7. Grupo Objetivo</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="card-grupo">🎯 Grupo Objetivo: {grupo_sugerido}</div>',
    unsafe_allow_html=True,
)

st.markdown("---")
if st.button("Registrarme para la jornada", use_container_width=True):
    calle_limpia = calle.strip() if calle else ""
    if not fecha_nacimiento:
        st.error("⚠️ Por favor seleccione la Fecha de Nacimiento en el calendario.")
    elif not paterno.strip() or not materno.strip() or not nombres.strip():
        st.error("⚠️ Complete Apellido Paterno, Apellido Materno y Nombre(s).")
    elif sexo == "SELECCIONE UNA OPCIÓN":
        st.error("⚠️ Seleccione una opción válida en Sexo.")
    elif estado_nacimiento == "SELECCIONE UN ESTADO":
        st.error("⚠️ Seleccione su Estado de Nacimiento.")
    elif estado_residencia == "SELECCIONE UN ESTADO":
        st.error("⚠️ Seleccione su Estado de Residencia.")
    elif not calle_limpia:
        st.error("⚠️ Complete el campo de Calle.")
    elif not numero.strip():
        st.error("⚠️ Complete el número Exterior/Interior.")
    elif not colonia.strip():
        st.error("⚠️ Complete el campo de Colonia.")
    elif cuenta_derechohabiencia == "SELECCIONE UNA OPCIÓN":
        st.error("⚠️ Indique si cuenta con derechohabiencia.")
    elif not es_rango_infantil and ocupacion == "SELECCIONE UNA OPCIÓN":
        st.error("⚠️ Seleccione una opción en Ocupación.")
    elif not antecedente_covid:
        st.error("⚠️ Indique su antecedente vacunal de COVID-19.")
    elif not antecedente_influenza:
        st.error("⚠️ Indique su antecedente vacunal de Influenza.")
    elif not vacuna_interes:
        st.error("⚠️ Seleccione la vacuna de su interés.")
    else:
        try:
            comorbilidades_dict = {
                "personas_embarazadas": personas_embarazadas,
                "personal_salud_riesgo": personal_salud_riesgo,
                "vih": vih,
                "diabetes": diabetes,
                "obesidad": obesidad,
                "cardiopatias": cardiopatias,
                "enfermedad_pulmonar": enfermedad_pulmonar,
                "cancer": cancer,
                "cardiacas_congenitas": cardiacas_congenitas,
                "insuficiencia_renal": insuficiencia_renal,
                "inmunosupresion": inmunosupresion,
                "discapacidades": discapacidades,
                "fibrosis_quistica": fibrosis_quistica,
                "hipertension": hipertension,
                "otro": otro_riesgo,
                "texto_otro": texto_otro_riesgo.upper(),
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
                "estado_nacimiento": estado_nacimiento if estado_nacimiento != "SELECCIONE UN ESTADO" else "CDMX",
                "estado_residencia": estado_residencia if estado_residencia != "SELECCIONE UN ESTADO" else "CDMX",
                "curp_con_nacimiento": curp_con_nacimiento,
                "cuenta_derechohabiencia": cuenta_derechohabiencia,
                "vacuna_interes": vacuna_interes,
                "antecedente_covid": antecedente_covid,
                "antecedente_influenza": antecedente_influenza,
                "grupo_sugerido": grupo_sugerido,
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

            st.cache_data.clear()

            st.session_state.ultimo_paciente_registrado = {
                "nombre_completo": f"{paterno.upper()} {materno.upper()} {nombres.upper()}",
                "curp_con_nacimiento": curp_con_nacimiento,
                "vacuna_interes": vacuna_interes,
                "grupo_objetivo": grupo_sugerido,
                "folio": folio_asignado,
            }
            st.rerun()

        except Exception as e:
            st.error("⚠️ Error general al procesar el registro en Google Sheets:")
            st.exception(e)
