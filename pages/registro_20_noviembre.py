import datetime
import random
import streamlit as st
import streamlit.components.v1 as components
from config import MAPA_SIGLAS_INVERSO, aplicar_configuracion_global
from utils.sheets_20_nov import guardar_registro_censal_20_nov, obtener_cliente_gspread
from config import GOOGLE_SHEET_ID
from aviso_privacidad import mostrar_aviso_privacidad_si_necesario
from utils.email_sender import enviar_comprobante_correo
from utils.logica_registro import (
    calcular_edad_detallada, generar_curp_algoritmica,
    determinar_grupo_desde_sheets, verificar_curp_duplicada,
    estados_mexico, lista_ocupaciones, meses_dict
)

# Importar componentes auxiliares del 20 de Noviembre desde utils
from utils.componentes_censo_20n import (
    cargar_catalogos_excel,
    estados_mexico as estados_mexico_20n,
    municipios_por_estado,
    generar_curp_algoritmica as generar_curp_20n,
    generar_rfc_algoritmico
)

aplicar_configuracion_global("Censo Nominal - Registro (20 de Noviembre)", "💉")

# --- LLAMADA A LA VENTANA EMERGENTE (MODAL) DEL AVISO DE PRIVACIDAD ---
mostrar_aviso_privacidad_si_necesario()

# --- CARGA DINÁMICA DE CATÁLOGOS DESDE LA PESTAÑA 'LISTAS' ---
opt_tipo_dh, opt_servicio, opt_coordinacion, opt_categoria, opt_turno = cargar_catalogos_excel()

# --- ESTILOS CSS ---
st.markdown(
    """
    <style>
        header {visibility: hidden;}
        .main-header { font-size: 2.2rem !important; font-weight: 800 !important; color: #1e5b4f !important; margin-bottom: 0.2rem; border-bottom: 3px solid #a57f2c; padding-bottom: 10px; }
        .sub-header { font-size: 1.2rem !important; color: #611232 !important; margin-bottom: 1.5rem; font-weight: 700 !important; }
        .section-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e5b4f !important; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e6d194; padding-bottom: 0.4rem; }
        label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; white-space: normal !important; word-wrap: break-word !important; }
        .stCheckbox { margin-bottom: 8px !important; }
        .card-edad { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #611232; font-size: 1.3rem !important; margin-bottom: 15px; }
        .card-curp { background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }
        .card-rfc { background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 15px; }
        .card-grupo { background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 15px; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1rem !important; }
        input[type="text"] { text-transform: uppercase !important; font-size: 1.1rem !important; }
        div[data-baseweb="select"] > div { font-size: 1rem !important; white-space: normal !important; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- RECUPERACIÓN DE PARÁMETROS DE URL ---
params = st.query_params
sigla_url = params.get("unidad", "20N").upper()

nombre_base_unidad = MAPA_SIGLAS_INVERSO.get(sigla_url, "CENTRO MÉDICO NACIONAL '20 DE NOVIEMBRE'")
sufijo_js = params.get("js", "")
modalidad_url = params.get("modalidad", "INTRAMUROS").upper()
es_admin = params.get("admin", "").lower() in ["true", "1", "si", "yes"] or params.get("rol", "").lower() == "admin"

st.session_state.siglas_unidad = sigla_url
st.session_state.nombre_unidad = f"{nombre_base_unidad} (Brigada {sufijo_js})" if sufijo_js else nombre_base_unidad
st.session_state.tipo_jornada = params.get("jornada", "I")
st.session_state.modalidad = modalidad_url if modalidad_url in ["INTRAMUROS", "EXTRAMUROS"] else "INTRAMUROS"

# --- FECHAS Y CONFIGURACIÓN ---
fecha_sistema = datetime.date.today()
fecha_url_str = params.get("fecha", fecha_sistema.strftime("%Y-%m-%d"))
try:
    val_fecha_app = datetime.datetime.strptime(fecha_url_str, "%Y-%m-%d").date()
except:
    val_fecha_app = fecha_sistema

if "ultimo_paciente_registrado" not in st.session_state:
    st.session_state.ultimo_paciente_registrado = None
if "paciente_duplicado_info" not in st.session_state:
    st.session_state.paciente_duplicado_info = None
if "enviando_registro" not in st.session_state:
    st.session_state.enviando_registro = False

if "ant_cov" not in st.session_state:
    st.session_state.ant_cov = None
if "ant_inf" not in st.session_state:
    st.session_state.ant_inf = None
if "input_vacuna" not in st.session_state:
    st.session_state.input_vacuna = None

@st.dialog("🎉 ¡REGISTRO EXITOSO - TICKET DIGITAL!")
def mostrar_modal_comprobante():
    p = st.session_state.get("ultimo_paciente_registrado")
    if p:
        curp_mostrar = p.get("curp_con_nacimiento", "CURP")
        nombre_val = p["nombre_completo"]
        folio_val = p["folio"]
        vacuna_val = p.get("vacuna_interes", "AMBAS")
        grupo_val = p["grupo_objetivo"]
        correo_capturado = p.get("correo_paciente", "")
        fecha_val = p.get("fecha_aplicacion", val_fecha_app.strftime("%d/%m/%Y"))

        texto_qr = (
            f"CMN 20 DE NOVIEMBRE - REGISTRO NOMINAL\n"
            f"FOLIO: {folio_val}\n"
            f"PACIENTE: {nombre_val}\n"
            f"CURP: {curp_mostrar}\n"
            f"VACUNA: {vacuna_val}\n"
            f"GRUPO: {grupo_val}\n"
            f"FECHA APLICACIÓN: {fecha_val}\n"
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
                position: relative; background-color: #ffffff; border: 3px solid #1e5b4f; 
                padding: 12px; border-radius: 10px; color: #161a1d; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 10px; overflow: hidden; 
            }}
            .watermark-overlay {{
                position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                display: flex; flex-direction: column; justify-content: space-evenly; align-items: center;
                pointer-events: none; z-index: 1; overflow: hidden;
            }}
            .watermark-row {{
                display: flex; gap: 15px; white-space: nowrap; font-size: 0.75rem; font-weight: 900;
                color: rgba(97, 18, 50, 0.12); text-transform: uppercase; letter-spacing: 1px; transform: rotate(-25deg);
            }}
            .titulo-ticket {{ font-size: 0.90rem !important; font-weight: 900 !important; color: #1e5b4f !important; text-align: center; margin: 0 0 6px 0; z-index: 2; position: relative; }}
            .cuerpo-ticket {{ display: flex; align-items: center; gap: 12px; z-index: 2; position: relative; }}
            .info-container {{ flex: 1; z-index: 2; position: relative; }}
            .qr-container {{ width: 110px; text-align: center; z-index: 2; position: relative; }}
            .qr-container canvas {{ width: 100% !important; height: auto !important; border: 2px solid #a57f2c; border-radius: 6px; padding: 3px; background: white; display: block; }}
            .folio-grande {{ font-size: 1.10rem !important; font-weight: 900 !important; color: #611232 !important; text-align: center; background-color: #f7f4eb; padding: 5px; border-radius: 6px; border: 2px dashed #a57f2c; margin-top: 6px; z-index: 2; position: relative; }}
            .info-text {{ margin: 3px 0; font-size: 0.78rem; }}
            .leyenda-posterior {{ font-size: 0.68rem !important; font-weight: 700 !important; color: #611232 !important; text-align: center; margin: 6px 0 0 0; z-index: 2; position: relative; }}
            .btn-container {{ display: flex; gap: 8px; }}
            .btn {{ width: 100%; padding: 0.65rem 0.4rem; font-size: 0.85rem; font-weight: bold; border-radius: 6px; border: none; cursor: pointer; text-align: center; }}
            .btn-img {{ background-color: #1e5b4f; color: white; }}
        </style>
        </head>
        <body>
            <div id="comprobante-captura" class="card-comprobante">
                <div class="watermark-overlay">
                    <div class="watermark-row"><span>CMN 20 DE NOVIEMBRE</span><span>CMN 20 DE NOVIEMBRE</span></div>
                    <div class="watermark-row"><span>REGISTRO NOMINAL DE VACUNACIÓN</span><span>REGISTRO NOMINAL</span></div>
                    <div class="watermark-row"><span>CMN 20 DE NOVIEMBRE</span><span>CMN 20 DE NOVIEMBRE</span></div>
                </div>
                <div class="titulo-ticket">CMN 20 DE NOVIEMBRE - REGISTRO EXITOSO</div>
                <div class="cuerpo-ticket">
                    <div class="info-container">
                        <p class="info-text"><b>Paciente:</b> {nombre_val}</p>
                        <p class="info-text"><b>CURP:</b> {curp_mostrar}</p>
                        <p class="info-text"><b>Vacuna:</b> {vacuna_val}</p>
                        <p class="info-text"><b>Grupo:</b> {grupo_val}</p>
                        <p class="info-text"><b>Fecha Aplicación:</b> {fecha_val}</p>
                    </div>
                    <div class="qr-container"><canvas id="qr-canvas"></canvas></div>
                </div>
                <div class="folio-grande">Folio: {folio_val}</div>
                <p class="leyenda-posterior">Guarde este comprobante para su presentación en el módulo de vacunación.</p>
            </div>
            <div class="btn-container">
                <button class="btn btn-img" onclick="descargarCaptura()">📸 Descargar Comprobante</button>
            </div>
            <script>
                window.addEventListener('DOMContentLoaded', () => {{
                    new QRious({{ element: document.getElementById('qr-canvas'), value: {repr(texto_qr)}, size: 250 }});
                }});
                function descargarCaptura() {{
                    html2canvas(document.getElementById('comprobante-captura'), {{ scale: 2, useCORS: true }}).then(canvas => {{
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
        components.html(html_comprobante_component, height=360)
        st.markdown("<br>", unsafe_allow_html=True)

        # --- ENVÍO DE CORREO DESDE EL MODAL ---
        st.markdown("##### ✉️ Enviar Comprobante de Folio por Correo")
        correo_destino_input = st.text_input("Correo electrónico del paciente:", value=correo_capturado, placeholder="correo@ejemplo.com", key="input_correo_registro_modal")
        
        if st.button("🚀 Enviar Folio por Correo", use_container_width=True, key="btn_enviar_mail_reg"):
            if not correo_destino_input.strip():
                st.warning("⚠️ Ingrese un correo electrónico válido.")
            else:
                exito, mensaje = enviar_comprobante_correo(
                    destinatario_email=correo_destino_input.strip(),
                    nombre_paciente=nombre_val,
                    folio=folio_val,
                    dosis_str=vacuna_val,
                    lotes_str=f"Grupo: {grupo_val}",
                    fecha_val=fecha_val,
                    tipo="folio"
                )
                if exito:
                    st.success(mensaje)
                else:
                    st.error(mensaje)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Nuevo Registro", use_container_width=True, key="btn_nuevo_registro_modal"):
            st.session_state.ultimo_paciente_registrado = None
            keys_a_limpiar = [
                "input_paterno", "input_materno", "input_nombres", "sel_dia", "sel_mes", "sel_anio",
                "input_sexo", "input_estnac", "input_muninac_sel", "input_muninac_txt", "input_estres", "input_calle", "input_num", "input_col",
                "input_derecho", "input_tipo_dh", "input_trabaja_cmn", "input_num_trabajador", "input_pers_salud_radio",
                "input_categoria", "input_servicio", "input_coordinacion", "input_turno",
                "input_ocupacion", "input_digitos", "input_vacuna", "ant_cov", "ant_inf",
                "input_correo_paciente",
                "chk_vih", "chk_diabetes", "chk_obesidad",
                "chk_cardiopatias", "chk_cancer",
                "chk_insufren", "chk_discapacidad", "chk_fibrosis", "chk_hipertension",
                "chk_gestante"
            ]
            for k in keys_a_limpiar:
                if k in st.session_state:
                    if "chk_" in k: st.session_state[k] = False
                    elif "sel_" in k:
                        if k == "sel_dia": st.session_state[k] = "Día"
                        elif k == "sel_mes": st.session_state[k] = "Mes"
                        elif k == "sel_anio": st.session_state[k] = "Año"
                    elif k in ["input_sexo", "input_derecho", "input_tipo_dh", "input_estnac", "input_estres", "input_ocupacion", "input_categoria", "input_servicio", "input_coordinacion", "input_turno"]:
                        st.session_state[k] = "SELECCIONE UNA OPCIÓN" if "SELECCIONE UNA OPCIÓN" in st.session_state.get(k, "") else "SELECCIONE"
                    elif "ant_" in k or "input_vacuna" in k: st.session_state[k] = None
                    else: st.session_state[k] = ""
            st.rerun()

@st.dialog("⚠️ ¡PACIENTE YA REGISTRADO!")
def mostrar_modal_duplicado():
    p = st.session_state.get("paciente_duplicado_info")
    if p:
        st.markdown(
            f"""
            <div style="background-color: #fcf0f0; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
                <span style="font-size: 1.1rem; font-weight: 800; color: #611232;">
                    Este paciente ya cuenta con un registro previo en esta jornada.
                </span><br><br>
                <b>Paciente:</b> {p['nombre']}<br>
                <b>Folio asignado:</b> <span style="color: #611232; font-size: 1.2rem;">{p['folio']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Entendido (Reiniciar)", use_container_width=True, key="btn_entendido_duplicado"):
            st.session_state.paciente_duplicado_info = None
            st.rerun()

# --- LLAMADAS A MODALES ---
if st.session_state.get("ultimo_paciente_registrado") is not None:
    mostrar_modal_comprobante()

if st.session_state.get("paciente_duplicado_info") is not None:
    mostrar_modal_duplicado()

st.markdown('<p class="main-header">CMN "20 de Noviembre" - Registro Nominal</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">Unidad: <b>{st.session_state.nombre_unidad}</b> | Modalidad: <b>{st.session_state.modalidad}</b></p>', unsafe_allow_html=True)

# --- PANEL DE DATOS SIMULADOS ---
if es_admin:
    with st.expander("🛠️ Panel de Administración (Datos de Prueba)", expanded=False):
        if st.button("🧪 Rellenar con Datos Simulados"):
            st.session_state.input_paterno = random.choice(["PÉREZ", "GÓMEZ", "LÓPEZ", "MARTÍNEZ", "RODRÍGUEZ"])
            st.session_state.input_materno = random.choice(["HERNÁNDEZ", "GARCÍA", "SÁNCHEZ", "RAMÍREZ", "TORRES"])
            st.session_state.input_nombres = random.choice(["JUAN CARLOS", "MARÍA GUADALUPE", "JOSE LUIS", "ANA KAREN", "ROBERTO"])
            st.session_state.sel_dia = str(random.randint(1, 28)).zfill(2)
            st.session_state.sel_mes = random.choice(list(meses_dict.keys()))
            st.session_state.sel_anio = str(random.randint(1975, 2010))
            st.session_state.input_sexo = random.choice(["HOMBRE", "MUJER"])
            st.session_state.input_estnac = random.choice(estados_mexico[1:])
            st.session_state.input_estres = st.session_state.input_estnac
            st.session_state.input_calle = "AV. COYOACÁN"
            st.session_state.input_num = str(random.randint(100, 999))
            st.session_state.input_colonia = "DEL VALLE"
            st.session_state.input_derecho = "SÍ"
            st.session_state.input_tipo_dh = "TRABAJADOR ACTIVO"
            st.session_state.input_trabaja_cmn = "SÍ"
            st.session_state.input_num_trabajador = "123456"
            st.session_state.input_pers_salud_radio = "SÍ"
            st.session_state.input_ocupacion = random.choice(lista_ocupaciones[1:])
            st.session_state.input_correo_paciente = "carlosju.med21@gmail.com"
            st.session_state.ant_cov = random.choice(["SÍ", "NO", "LO DESCONOCE"])
            st.session_state.ant_inf = random.choice(["SÍ", "NO", "LO DESCONOCE"])
            st.session_state.input_vacuna = random.choice(["AMBAS", "COVID-19", "INFLUENZA"])
            if st.session_state.input_sexo == "MUJER":
                st.session_state.chk_gestante = random.choice(["NO", "SÍ"])
            st.rerun()

# --- DERECHOHABIENCIA Y ADSCRIPCIÓN LABORAL ---
st.markdown('<div class="section-title">1. Derechohabiencia y Adscripción Laboral</div>', unsafe_allow_html=True)
cuenta_derechohabiencia = st.selectbox("¿Cuenta con derechohabiencia? *", options=["SELECCIONE", "NO", "SÍ"], key="input_derecho")

tipo_dh = "NO APLICA"
trabaja_cmn = "NO"
num_trabajador = ""
personal_salud_val = "NO"
categoria = "NO APLICA"
servicio = "NO APLICA"
coordinacion = "NO APLICA"
turno_val = "NO APLICA"

if cuenta_derechohabiencia == "SÍ":
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        tipo_dh = st.selectbox("Tipo de DH *", options=["SELECCIONE"] + opt_tipo_dh, key="input_tipo_dh")
    with col_d2:
        trabaja_cmn = st.radio("¿Trabaja en CMN 20 de Noviembre?", options=["NO", "SÍ"], horizontal=True, key="input_trabaja_cmn")

    if trabaja_cmn == "SÍ":
        num_trabajador = st.text_input("Número de Trabajador", key="input_num_trabajador")
        
        personal_salud_radio = st.radio("¿Es usted Personal de Salud?", options=["NO", "SÍ"], horizontal=True, key="input_pers_salud_radio")
        personal_salud_val = personal_salud_radio

        if personal_salud_val == "SÍ":
            col_lab1, col_lab2, col_lab3, col_lab4 = st.columns(4)
            with col_lab1:
                categoria = st.selectbox("Categoría", options=["SELECCIONE"] + opt_categoria, key="input_categoria")
            with col_lab2:
                servicio = st.selectbox("Servicio", options=["SELECCIONE"] + opt_servicio, key="input_servicio")
            with col_lab3:
                coordinacion = st.selectbox("Coordinación", options=["SELECCIONE"] + opt_coordinacion, key="input_coordinacion")
            with col_lab4:
                turno_full = st.selectbox("Turno", options=["SELECCIONE"] + opt_turno, key="input_turno")

            turno_map = {"MATUTINO": "M", "VESPERTINO": "V", "NOCTURNO": "N", "JORNADA ACUMULADA": "JA"}
            turno_val = turno_map.get(turno_full.upper(), turno_full[:1] if turno_full != "SELECCIONE" else "")

# --- IDENTIFICACIÓN DEL PACIENTE ---
st.markdown('<div class="section-title">2. Identificación del Paciente</div>', unsafe_allow_html=True)
col_n1, col_n2, col_n3 = st.columns(3)
with col_n1: paterno = st.text_input("Apellido Paterno *", key="input_paterno")
with col_n2: materno = st.text_input("Apellido Materno *", key="input_materno")
with col_n3: nombres = st.text_input("Nombre(s) *", key="input_nombres")

st.markdown("<label style='font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important;'>Fecha de Nacimiento *</label>", unsafe_allow_html=True)
col_d, col_m, col_a = st.columns(3)
with col_d: dia_sel = st.selectbox("Día", options=["Día"] + [str(d).zfill(2) for d in range(1, 32)], key="sel_dia", label_visibility="collapsed")
with col_m: mes_sel = st.selectbox("Mes", options=["Mes"] + list(meses_dict.keys()), key="sel_mes", label_visibility="collapsed")
with col_a: anio_sel = st.selectbox("Año", options=["Año"] + [str(a) for a in range(datetime.date.today().year, 1919, -1)], key="sel_anio", label_visibility="collapsed")

fecha_nacimiento = None
if dia_sel != "Día" and mes_sel != "Mes" and anio_sel != "Año":
    try: fecha_nacimiento = datetime.date(int(anio_sel), meses_dict[mes_sel], int(dia_sel))
    except ValueError: st.error("⚠️ La combinación de fecha seleccionada no es válida.")

if fecha_nacimiento:
    st.markdown(f'<div style="background-color: #f7f4eb; border: 2px solid #1e5b4f; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 15px;"><span style="font-size: 1.1rem; font-weight: 800; color: #1e5b4f;">✅ Fecha Seleccionada: {fecha_nacimiento.strftime("%d/%m/%Y")}</span></div>', unsafe_allow_html=True)

col_fn1, col_fn2, col_fn3 = st.columns(3)
with col_fn1: sexo = st.selectbox("Sexo *", options=["SELECCIONE UNA OPCIÓN", "HOMBRE", "MUJER"], key="input_sexo")
with col_fn2: estado_nacimiento = st.selectbox("Estado de Nacimiento *", options=estados_mexico, key="input_estnac")

lista_municipios = municipios_por_estado.get(estado_nacimiento, ["OTRO (ESPECIFIQUE)"])
with col_fn3:
    if estado_nacimiento in municipios_por_estado:
        muni_nac = st.selectbox("Municipio / Alcaldía *", options=lista_municipios, key="input_muninac_sel")
    else:
        muni_nac = st.text_input("Municipio / Alcaldía *", key="input_muninac_txt")

personas_gestantes = "NO"
if sexo == "MUJER":
    personas_gestantes = st.radio("¿Es una persona gestante?", options=["NO", "SÍ"], index=None, horizontal=True, key="chk_gestante")
else:
    st.session_state.chk_gestante = None

calc_anos, calc_meses, _ = calcular_edad_detallada(fecha_nacimiento, val_fecha_app) if fecha_nacimiento else (0, 0, 0)
st.markdown(f'<div class="card-edad">📅 Edad calculada: {calc_anos} Años, {calc_meses} Meses</div>', unsafe_allow_html=True)

edad_total_meses = (calc_anos * 12) + calc_meses

# --- IMAGEN ILUSTRATIVA DE INE (DÍGITO VERIFICADOR) ---
st.markdown("<br>", unsafe_allow_html=True)
col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
with col_img2:
    try: st.image("assets/INE.png", width=350, caption="📌 Ubicación del Dígito Verificador")
    except: pass
st.markdown("<br>", unsafe_allow_html=True)

digitos_faltantes = st.text_input("Dígito Verificador (Opcional - Últimos caracteres)", max_chars=2, key="input_digitos")
curp_algoritmica = generar_curp_algoritmica(paterno, materno, nombres, fecha_nacimiento, sexo, estado_nacimiento, digitos_faltantes)
curp_con_nacimiento = f"{curp_algoritmica}/{estado_nacimiento.upper()}" if estado_nacimiento != "SELECCIONE UN ESTADO" and "COMPLETA" not in curp_algoritmica else curp_algoritmica

st.markdown(f'<div class="card-curp">🆔 CURP / RFC Generada: {curp_con_nacimiento}</div>', unsafe_allow_html=True)

rfc_generado = generar_rfc_algoritmico(paterno, materno, nombres, fecha_nacimiento)
st.markdown(f'<div class="card-rfc">📋 RFC Generado: {rfc_generado}</div>', unsafe_allow_html=True)

# --- DOMICILIO Y CORREO ---
st.markdown('<div class="section-title">3. Domicilio y Correo Electrónico</div>', unsafe_allow_html=True)
estado_residencia = st.selectbox("Estado de Residencia *", options=estados_mexico, key="input_estres")
col_dom1, col_dom2, col_dom3 = st.columns([2, 1, 1])
with col_dom1: calle = st.text_input("Calle *", key="input_calle")
with col_dom2: numero = st.text_input("No. (Ext / Int) *", key="input_num")
with col_dom3: colonia = st.text_input("Colonia *", key="input_col")

correo_paciente = st.text_input("📧 Correo Electrónico (Para envío de su folio) *", placeholder="correo@ejemplo.com", key="input_correo_paciente")

# --- OCUPACIÓN ---
st.markdown('<div class="section-title">4. Ocupación</div>', unsafe_allow_html=True)
if fecha_nacimiento and edad_total_meses < 59:
    st.info("ℹ️ Menor de 59 meses (< 5 años): Ocupación asignada automáticamente como 'NO APLICA'.")
    st.session_state.input_ocupacion = "NO APLICA"
    ocupacion = st.selectbox("Seleccione su Ocupación *", options=lista_ocupaciones, index=lista_ocupaciones.index("NO APLICA"), key="input_ocupacion", disabled=True)
else:
    ocupacion = st.selectbox("Seleccione su Ocupación *", options=lista_ocupaciones, key="input_ocupacion")

# --- COMORBILIDADES ---
st.markdown('<div class="section-title">5. Grupos de Riesgo y Comorbilidades</div>', unsafe_allow_html=True)
es_personal_salud_ocupacion = "PERSONAL DE SALUD" in ocupacion.upper() or personal_salud_val == "SÍ"
es_embarazada_activa = (sexo == "MUJER" and personas_gestantes == "SÍ")

if es_embarazada_activa:
    st.session_state.chk_personas_embarazadas = True
elif sexo != "MUJER" or personas_gestantes != "SÍ":
    st.session_state.chk_personas_embarazadas = False

col_r1, col_r2 = st.columns(2)
with col_r1:
    personas_embarazadas = st.checkbox("EMBARAZADAS", disabled=es_embarazada_activa, key="chk_personas_embarazadas")
    vih = st.checkbox("VIH/sida", key="chk_vih")
    diabetes = st.checkbox("DIABETES MELLITUS", key="chk_diabetes")
    obesidad = st.checkbox("OBESIDAD MÓRBIDA", key="chk_obesidad")
    cardiopatias = st.checkbox("CARDIOPATÍAS AGUDAS O CRÓNICAS", key="chk_cardiopatias")
    enfermedad_pulmonar = st.checkbox("ENFERMEDAD PULMONAR CRÓNICA, INCLUYE EPOC Y ASMA", key="chk_enfermedad_pulmonar")

with col_r2:
    cancer = st.checkbox("CÁNCER", key="chk_cancer")
    cardiacas_congenitas = st.checkbox("ENFERMEDADES CARDIACAS O PULMONARES CONGÉNITAS U OTROS PADECIMIENTOS", key="chk_cardiacas_congenitas")
    insuficiencia_renal = st.checkbox("INSUFICIENCIA RENAL", key="chk_insufren")
    inmunosupresion = st.checkbox("INMUNOSUPRESIÓN ADQUIRIDA", key="chk_inmunosupresion")
    discapacidades = st.checkbox("DISCAPACIDADES", key="chk_discapacidad")
    fibrosis_quistica = st.checkbox("FIBROSIS QUÍSTICA", key="chk_fibrosis")
    hipertension = st.checkbox("HIPERTENSIÓN ARTERIAL", key="chk_hipertension")
    otro_riesgo = st.checkbox("OTRO", key="chk_otro")
    texto_otro_riesgo = st.text_input("Especifique otro grupo de riesgo:", key="txt_otro_riesgo") if otro_riesgo else ""

# --- ANTECEDENTE Y VACUNA ---
st.markdown('<div class="section-title">6. Antecedente Vacunal y 8. Vacuna de Interés</div>', unsafe_allow_html=True)
col_av1, col_av2 = st.columns(2)
with col_av1:
    antecedente_covid = st.radio("¿Cuenta con dosis previa de COVID-19? *", options=["SÍ", "NO", "LO DESCONOCE"], index=None, horizontal=True, key="ant_cov")
with col_av2:
    antecedente_influenza = st.radio("¿Cuenta con dosis previa de Influenza? *", options=["SÍ", "NO", "LO DESCONOCE"], index=None, horizontal=True, key="ant_inf")

vacuna_interes = st.radio("Seleccione la vacuna de su interés: *", options=["AMBAS", "COVID-19", "INFLUENZA"], index=None, horizontal=True, key="input_vacuna")

tiene_comorbilidades = vih or diabetes or obesidad or cardiopatias or enfermedad_pulmonar or cancer or cardiacas_congenitas or insuficiencia_renal or inmunosupresion or discapacidades or fibrosis_quistica or hipertension or otro_riesgo or personas_embarazadas or (personal_salud_val == "SÍ")

grupo_sugerido = determinar_grupo_desde_sheets(vacuna_interes, edad_total_meses, calc_anos, "SÍ" if personas_embarazadas else personas_gestantes, ocupacion, tiene_comorbilidades) if vacuna_interes else "POR ASIGNAR"

st.markdown('<div class="section-title">7. Grupo Objetivo</div>', unsafe_allow_html=True)
st.markdown(f'<div class="card-grupo">🎯 Grupo Objetivo: {grupo_sugerido}</div>', unsafe_allow_html=True)

st.markdown("---")

# --- BOTÓN DE REGISTRO ---
btn_disabled = st.session_state.enviando_registro
if st.button("Registrarme para la jornada (20 de Noviembre)", use_container_width=True, disabled=btn_disabled, key="btn_registrar_jornada"):
    if not fecha_nacimiento:
        st.error("⚠️ Seleccione correctamente el Día, Mes y Año de Nacimiento.")
    elif not paterno.strip() or not materno.strip() or not nombres.strip():
        st.error("⚠️ Complete Apellido Paterno, Materno y Nombre(s).")
    elif not correo_paciente.strip():
        st.error("⚠️ Ingrese el correo electrónico para enviarle su comprobante de folio.")
    elif cuenta_derechohabiencia == "SELECCIONE":
        st.error("⚠️ Indique si cuenta con derechohabiencia.")
    elif cuenta_derechohabiencia == "SÍ" and tipo_dh == "SELECCIONE":
        st.error("⚠️ Seleccione el Tipo de Derechohabiencia.")
    elif sexo == "SELECCIONE UNA OPCIÓN":
        st.error("⚠️ Seleccione una opción en Sexo.")
    elif vacuna_interes is None:
        st.error("⚠️ Seleccione la vacuna de su interés.")
    else:
        st.session_state.enviando_registro = True
        
        duplicado, folio_previo = verificar_curp_duplicada(
            curp_con_nacimiento, sigla_url, sufijo_js, st.session_state.tipo_jornada, val_fecha_app
        )
        
        if duplicado:
            st.session_state.enviando_registro = False
            st.session_state.paciente_duplicado_info = {
                "nombre": f"{paterno.upper()} {materno.upper()} {nombres.upper()}",
                "folio": folio_previo
            }
            st.rerun()
        else:
            try:
                fecha_aplicacion_str = val_fecha_app.strftime("%d/%m/%Y")

                comorbilidades_dict = {
                    "personas_embarazadas": personas_embarazadas, "personal_salud_riesgo": (personal_salud_val == "SÍ"),
                    "vih": vih, "diabetes": diabetes, "obesidad": obesidad, "cardiopatias": cardiopatias,
                    "enfermedad_pulmonar": enfermedad_pulmonar, "cancer": cancer, "cardiacas_congenitas": cardiacas_congenitas,
                    "insuficiencia_renal": insuficiencia_renal, "inmunosupresion": inmunosupresion,
                    "discapacidades": discapacidades, "fibrosis_quistica": fibrosis_quistica,
                    "hipertension": hipertension, "otro": otro_riesgo, "texto_otro": texto_otro_riesgo.upper(),
                }

                datos_paciente = {
                    "paterno": paterno, "materno": materno, "nombres": nombres,
                    "fecha_nacimiento": fecha_nacimiento, "calc_anos": calc_anos, "calc_meses": calc_meses,
                    "sexo": sexo, "calle": calle, "numero": numero, "colonia": colonia,
                    "correo_paciente": correo_paciente.strip(),
                    "estado_nacimiento": estado_nacimiento if estado_nacimiento != "SELECCIONE UN ESTADO" else "CDMX",
                    "muni_nac": muni_nac.upper() if isinstance(muni_nac, str) and muni_nac != "SELECCIONE" else "CDMX",
                    "estado_residencia": estado_residencia if estado_residencia != "SELECCIONE UN ESTADO" else "CDMX",
                    "curp_con_nacimiento": curp_con_nacimiento, "cuenta_derechohabiencia": cuenta_derechohabiencia,
                    "vacuna_interes": vacuna_interes, "antecedente_covid": antecedente_covid,
                    "antecedente_influenza": antecedente_influenza, "grupo_sugerido": grupo_sugerido,
                    "ocupacion": ocupacion, "comorbilidades": comorbilidades_dict,
                    "modalidad": st.session_state.modalidad,
                    "rfc": rfc_generado,
                    "val_fecha_app": val_fecha_app,
                    "tipo_jornada": st.session_state.tipo_jornada,
                    "fn_dia": str(fecha_nacimiento.day).zfill(2),
                    "fn_mes": str(fecha_nacimiento.month).zfill(2),
                    "fn_ano": str(fecha_nacimiento.year),
                    "dh": cuenta_derechohabiencia,
                    "tipo_dh": tipo_dh if cuenta_derechohabiencia == "SÍ" else "NO APLICA",
                    "trabaja_cmn": trabaja_cmn,
                    "num_trabajador": num_trabajador.upper() if num_trabajador else "",
                    "personal_salud": personal_salud_val,
                    "categoria": categoria,
                    "servicio": servicio,
                    "coordinacion": coordinacion,
                    "turno": turno_val,
                    "embarazo": "SÍ" if personas_embarazadas else "NO",
                }

                # Llamada a la función de guardado dual (nominal y censo) en la hoja del 20 de Noviembre
                folio_asignado = guardar_registro_censal_20_nov(datos_paciente)

                st.cache_data.clear()
                st.session_state.ultimo_paciente_registrado = {
                    "nombre_completo": f"{paterno.upper()} {materno.upper()} {nombres.upper()}",
                    "curp_con_nacimiento": curp_con_nacimiento, "vacuna_interes": vacuna_interes,
                    "grupo_objetivo": grupo_sugerido, "folio": folio_asignado,
                    "correo_paciente": correo_paciente.strip(),
                    "fecha_aplicacion": fecha_aplicacion_str,
                }
                st.session_state.enviando_registro = False
                st.rerun()
            except Exception as e:
                st.session_state.enviando_registro = False
                st.error("⚠️ Error general al procesar el registro en la hoja de Google Sheets del CMN 20 de Noviembre:")
                st.exception(e)
