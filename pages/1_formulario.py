import datetime
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st
import streamlit.components.v1 as components
from aviso_privacidad import mostrar_aviso_privacidad_si_necesario
from config import MAPA_SIGLAS_INVERSO, aplicar_configuracion_global
from utils.logica_registro import (
    calcular_edad_detallada,
    determinar_grupo_desde_sheets,
    estados_mexico,
    generar_curp_algoritmica,
    generar_folio_personalizado,
    lista_ocupaciones,
    meses_dict,
    verificar_curp_duplicada,
)
from utils.sheets import guardar_registro_censal

aplicar_configuracion_global("Censo Nominal - Registro", "💉")

# --- LLAMADA A LA VENTANA EMERGENTE (MODAL) DEL AVISO DE PRIVACIDAD ---
mostrar_aviso_privacidad_si_necesario()

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
        .card-grupo { background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 15px; }
        .card-info-header { background-color: #f7f4eb; border: 2px solid #1e5b4f; padding: 12px; border-radius: 8px; text-align: center; font-weight: 700; color: #1e5b4f; font-size: 1.1rem !important; margin-bottom: 15px; }
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

nombre_base_unidad = MAPA_SIGLAS_INVERSO.get(sigla_url, "20 DE NOVIEMBRE")
sufijo_js = params.get("js", "")
modalidad_url = params.get("modalidad", "INTRAMUROS").upper()
es_admin = (
    params.get("admin", "").lower() in ["true", "1", "si", "yes"]
    or params.get("rol", "").lower() == "admin"
)

st.session_state.siglas_unidad = sigla_url
st.session_state.nombre_unidad = (
    f"{nombre_base_unidad} (Brigada {sufijo_js})"
    if sufijo_js
    else nombre_base_unidad
)
st.session_state.tipo_jornada = params.get("jornada", "I")
st.session_state.modalidad = (
    modalidad_url
    if modalidad_url in ["INTRAMUROS", "EXTRAMUROS"]
    else "INTRAMUROS"
)

# --- FECHAS Y FOLIO INICIAL ---
fecha_sistema = datetime.date.today()
fecha_url_str = params.get("fecha", fecha_sistema.strftime("%Y-%m-%d"))
try:
  val_fecha_app = datetime.datetime.strptime(fecha_url_str, "%Y-%m-%d").date()
except:
  val_fecha_app = fecha_sistema

folio_inicial = "POR ASIGNAR"

if "ultimo_paciente_registrado" not in st.session_state:
  st.session_state.ultimo_paciente_registrado = None
if "paciente_duplicado_info" not in st.session_state:
  st.session_state.paciente_duplicado_info = None

if "ant_cov" not in st.session_state:
  st.session_state.ant_cov = None
if "ant_inf" not in st.session_state:
  st.session_state.ant_inf = None
if "input_vacuna" not in st.session_state:
  st.session_state.input_vacuna = None


# --- FUNCIÓN DE ENVÍO DE CORREO DESDE SECRETS ---
def enviar_comprobante_por_correo(destinatario, p):
  try:
    remitente = st.secrets["email"]["sender_email"]
    password = st.secrets["email"]["sender_password"]
    servidor = st.secrets["email"]["smtp_server"]
    puerto = st.secrets["email"]["smtp_port"]

    asunto = f"Comprobante de Vacunación - Folio: {p['folio']}"

    cuerpo = f"""
    Estimado/a {p['nombre_completo']},
    
    Su registro para la jornada de vacunación se ha completado exitosamente.
    
    Detalles de su registro:
    - Folio: {p['folio']}
    - CURP: {p['curp_con_nacimiento']}
    - Vacuna de interés: {p['vacuna_interes']}
    - Grupo objetivo: {p['grupo_objetivo']}
    
    Conserve este comprobante y preséntelo en la unidad.
    """

    msg = MIMEMultipart()
    msg["From"] = remitente
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "plain"))

    server = smtplib.SMTP(servidor, puerto)
    server.starttls()
    server.login(remitente, password)
    server.sendmail(remitente, destinatario, msg.as_string())
    server.quit()
    return True
  except Exception as e:
    st.error(f"Error al enviar el correo: {e}")
    return False


@st.dialog("🎉 ¡REGISTRO EXITOSO - TICKET DIGITAL!")
def mostrar_modal_comprobante():
  p = st.session_state.ultimo_paciente_registrado
  if p:
    curp_mostrar = p.get("curp_con_nacimiento", "CURP")
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
                position: relative; background-color: #ffffff; border: 3px solid #1e5b4f; 
                padding: 12px; border-radius: 10px; color: #161a1d; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 10px; overflow: hidden; 
            }}
            .titulo-ticket {{ font-size: 0.90rem !important; font-weight: 900 !important; color: #1e5b4f !important; text-align: center; margin: 0 0 6px 0; }}
            .cuerpo-ticket {{ display: flex; align-items: center; gap: 12px; }}
            .info-container {{ flex: 1; }}
            .qr-container {{ width: 110px; text-align: center; }}
            .qr-container canvas {{ width: 100% !important; height: auto !important; border: 2px solid #a57f2c; border-radius: 6px; padding: 3px; background: white; display: block; }}
            .folio-grande {{ font-size: 1.10rem !important; font-weight: 900 !important; color: #611232 !important; text-align: center; background-color: #f7f4eb; padding: 5px; border-radius: 6px; border: 2px dashed #a57f2c; margin-top: 6px; }}
            .info-text {{ margin: 3px 0; font-size: 0.78rem; }}
            .leyenda-posterior {{ font-size: 0.68rem !important; font-weight: 700 !important; color: #611232 !important; text-align: center; margin: 5px 0 0 0; }}
        </style>
        </head>
        <body>
            <div id="comprobante-captura" class="card-comprobante">
                <div class="titulo-ticket">FOLIO DE VACUNACION REGISTRADO</div>
                <div class="cuerpo-ticket">
                    <div class="info-container">
                        <p class="info-text"><b>Paciente:</b> {nombre_val}</p>
                        <p class="info-text"><b>CURP:</b> {curp_mostrar}</p>
                        <p class="info-text"><b>Vacuna:</b> {vacuna_val}</p>
                        <p class="info-text"><b>Grupo:</b> {grupo_val}</p>
                    </div>
                    <div class="qr-container"><canvas id="qr-canvas"></canvas></div>
                </div>
                <div class="folio-grande">Folio: {folio_val}</div>
                <p class="leyenda-posterior">Posterior a su asistencia se le entregará un comprobante oficial.</p>
            </div>
            <script>
                window.addEventListener('DOMContentLoaded', () => {{
                    new QRious({{ element: document.getElementById('qr-canvas'), value: {repr(texto_qr)}, size: 250 }});
                }});
            </script>
        </body>
        </html>
        """
    components.html(html_comprobante_component, height=260)

    # Widget para capturar el correo electrónico del destinatario dentro del diálogo
    correo_destino = st.text_input(
        "📧 Enviar comprobante por correo electrónico:",
        placeholder="ejemplo@correo.com",
    )

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
      if st.button("📤 Enviar Correo", use_container_width=True):
        if not correo_destino:
          st.warning("⚠️ Ingrese una dirección de correo válida.")
        else:
          with st.spinner("Enviando correo..."):
            exito = enviar_comprobante_por_correo(correo_destino, p)
            if exito:
              st.success(f"¡Comprobante enviado a {correo_destino}!")

    with col_btn2:
      if st.button("➕ Nuevo Registro", use_container_width=True):
        st.session_state.ultimo_paciente_registrado = None
        keys_a_limpiar = [
            "input_paterno",
            "input_materno",
            "input_nombres",
            "sel_dia",
            "sel_mes",
            "sel_anio",
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
            if "chk_" in k:
              st.session_state[k] = False
            elif "sel_" in k:
              if k == "sel_dia":
                st.session_state[k] = "Día"
              elif k == "sel_mes":
                st.session_state[k] = "Mes"
              elif k == "sel_anio":
                st.session_state[k] = "Año"
            elif k in [
                "input_sexo",
                "input_derecho",
                "input_estnac",
                "input_estres",
                "input_ocupacion",
            ]:
              st.session_state[k] = "SELECCIONE UNA OPCIÓN"
            elif "ant_" in k or "input_vacuna" in k:
              st.session_state[k] = None
            else:
              st.session_state[k] = ""
        st.rerun()


@st.dialog("⚠️ ¡PACIENTE YA REGISTRADO!")
def mostrar_modal_duplicado():
  p = st.session_state.paciente_duplicado_info
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
        unsafe_allow_html=True,
    )
    if st.button("Entendido (Reiniciar)", use_container_width=True):
      st.session_state.paciente_duplicado_info = None
      st.rerun()


if st.session_state.ultimo_paciente_registrado is not None:
  mostrar_modal_comprobante()

if st.session_state.paciente_duplicado_info is not None:
  mostrar_modal_duplicado()

st.markdown(
    '<p class="main-header">Sistema de Registro Nominal de Vacunación</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p class="sub-header">Unidad: <b>{st.session_state.nombre_unidad}</b> | Modalidad: <b>{st.session_state.modalidad}</b></p>',
    unsafe_allow_html=True,
)

# --- PANEL DE DATOS SIMULADOS ---
if es_admin:
  with st.expander(
      "🛠️ Panel de Administración (Datos de Prueba)", expanded=False
  ):
    if st.button("🧪 Rellenar con Datos Simulados"):
      st.session_state.input_paterno = random.choice(
          ["PÉREZ", "GÓMEZ", "LÓPEZ", "MARTÍNEZ", "RODRÍGUEZ"]
      )
      st.session_state.input_materno = random.choice(
          ["HERNÁNDEZ", "GARCÍA", "SÁNCHEZ", "RAMÍREZ", "TORRES"]
      )
      st.session_state.input_nombres = random.choice(
          ["JUAN CARLOS", "MARÍA GUADALUPE", "JOSE LUIS", "ANA KAREN", "ROBERTO"]
      )
      st.session_state.sel_dia = str(random.randint(1, 28)).zfill(2)
      st.session_state.sel_mes = random.choice(list(meses_dict.keys()))
      st.session_state.sel_anio = str(random.randint(1975, 2010))
      st.session_state.input_sexo = random.choice(["HOMBRE", "MUJER"])
      st.session_state.input_estnac = random.choice(estados_mexico[1:])
      st.session_state.input_estres = st.session_state.input_estnac
      st.session_state.input_calle = "AV. REVOLUCIÓN"
      st.session_state.input_num = str(random.randint(100, 999))
      st.session_state.input_colonia = "CENTRO"
      st.session_state.input_derecho = "SÍ"
      st.session_state.input_ocupacion = random.choice(lista_ocupaciones[1:])
      st.session_state.ant_cov = random.choice(["SÍ", "NO", "LO DESCONOCE"])
      st.session_state.ant_inf = random.choice(["SÍ", "NO", "LO DESCONOCE"])
      st.session_state.input_vacuna = random.choice(
          ["AMBAS", "COVID-19", "INFLUENZA"]
      )
      if st.session_state.input_sexo == "MUJER":
        st.session_state.chk_gestante = random.choice(["NO", "SÍ"])
      st.rerun()

# --- APARTADO 1: FECHAS Y FOLIO ---
st.markdown(
    '<div class="section-title">1. Control de Fechas y Folio</div>',
    unsafe_allow_html=True,
)
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
  st.markdown(
      f'<div class="card-info-header">📅 Fecha de Registro<br><b>{fecha_sistema.strftime("%d/%m/%Y")}</b></div>',
      unsafe_allow_html=True,
  )
with col_f2:
  st.markdown(
      f'<div class="card-info-header">🗓️ Fecha de Aplicación<br><b>{val_fecha_app.strftime("%d/%m/%Y")}</b></div>',
      unsafe_allow_html=True,
  )
with col_f3:
  st.markdown(
      f'<div class="card-info-header">🔖 Folio de Registro<br><b>{folio_inicial}</b></div>',
      unsafe_allow_html=True,
  )

# --- IDENTIFICACIÓN DEL PACIENTE ---
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

st.markdown(
    "<label style='font-size: 1.1rem !important; font-weight: 600 !important;"
    " color: #161a1d !important;'>Fecha de Nacimiento *</label>",
    unsafe_allow_html=True,
)
col_d, col_m, col_a = st.columns(3)
with col_d:
  dia_sel = st.selectbox(
      "Día",
      options=["Día"] + [str(d).zfill(2) for d in range(1, 32)],
      key="sel_dia",
      label_visibility="collapsed",
  )
with col_m:
  mes_sel = st.selectbox(
      "Mes",
      options=["Mes"] + list(meses_dict.keys()),
      key="sel_mes",
      label_visibility="collapsed",
  )
with col_a:
  anio_sel = st.selectbox(
      "Año",
      options=["Año"] + [str(a) for a in range(datetime.date.today().year, 1919, -1)],
      key="sel_anio",
      label_visibility="collapsed",
  )

fecha_nacimiento = None
if dia_sel != "Día" and mes_sel != "Mes" and anio_sel != "Año":
  try:
    fecha_nacimiento = datetime.date(
        int(anio_sel), meses_dict[mes_sel], int(dia_sel)
    )
  except ValueError:
    st.error("⚠️ La combinación de fecha seleccionada no es válida.")

if fecha_nacimiento:
  st.markdown(
      f'<div style="background-color: #f7f4eb; border: 2px solid #1e5b4f;'
      f' padding: 10px; border-radius: 8px; text-align: center; margin-bottom:'
      f' 15px;"><span style="font-size: 1.1rem; font-weight: 800; color:'
      f' #1e5b4f;">✅ Fecha Seleccionada:'
      f' {fecha_nacimiento.strftime("%d/%m/%Y")}</span></div>',
      unsafe_allow_html=True,
  )

col_fn2, col_fn3 = st.columns(2)
with col_fn2:
  sexo = st.selectbox(
      "Sexo *", options=["SELECCIONE UNA OPCIÓN", "HOMBRE", "MUJER"], key="input_sexo"
  )
with col_fn3:
  estado_nacimiento = st.selectbox(
      "Estado de Nacimiento *", options=estados_mexico, key="input_estnac"
  )

personas_gestantes = "NO"
if sexo == "MUJER":
  personas_gestantes = st.radio(
      "¿Es una persona gestante?",
      options=["NO", "SÍ"],
      index=None,
      horizontal=True,
      key="chk_gestante",
  )
else:
  st.session_state.chk_gestante = None

calc_anos, calc_meses, _ = (
    calcular_edad_detallada(fecha_nacimiento, val_fecha_app)
    if fecha_nacimiento
    else (0, 0, 0)
)
st.markdown(
    f'<div class="card-edad">📅 Edad calculada: {calc_anos} Años,'
    f" {calc_meses} Meses</div>",
    unsafe_allow_html=True,
)

edad_total_meses = (calc_anos * 12) + calc_meses

st.markdown("<br>", unsafe_allow_html=True)
col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
with col_img2:
  try:
    st.image(
        "assets/INE.png", width=350, caption="📌 Ubicación del Dígito Verificador"
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

# --- DOMICILIO Y AFILIACIÓN ---
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

# --- OCUPACIÓN ---
st.markdown(
    '<div class="section-title">4. Ocupación</div>', unsafe_allow_html=True
)
if fecha_nacimiento and edad_total_meses < 59:
  st.info(
      "ℹ️ Menor de 59 meses (< 5 años): Ocupación asignada automáticamente como"
      " 'NO APLICA'."
  )
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
      "Seleccione su Ocupación *", options=lista_ocupaciones, key="input_ocupacion"
  )

# --- COMORBILIDADES ---
st.markdown(
    '<div class="section-title">5. Grupos de Riesgo y Comorbilidades</div>',
    unsafe_allow_html=True,
)
es_personal_salud_ocupacion = "PERSONAL DE SALUD" in ocupacion.upper()
es_embarazada_activa = sexo == "MUJER" and personas_gestantes == "SÍ"

if es_embarazada_activa:
  st.session_state.chk_personas_embarazadas = True
elif sexo != "MUJER" or personas_gestantes != "SÍ":
  st.session_state.chk_personas_embarazadas = False

if es_personal_salud_ocupacion:
  st.session_state.chk_personal_salud_riesgo = True
elif not es_personal_salud_ocupacion:
  st.session_state.chk_personal_salud_riesgo = False

col_r1, col_r2 = st.columns(2)
with col_r1:
  personas_embarazadas = st.checkbox(
      "EMBARAZADAS", disabled=es_embarazada_activa, key="chk_personas_embarazadas"
  )
  personal_salud_riesgo = st.checkbox(
      "PERSONAL DE SALUD",
      disabled=es_personal_salud_ocupacion,
      key="chk_personal_salud_riesgo",
  )
  vih = st.checkbox("VIH/sida", key="chk_vih")
  diabetes = st.checkbox("DIABETES MELLITUS", key="chk_diabetes")
  obesidad = st.checkbox("OBESIDAD MÓRBIDA", key="chk_obesidad")
  cardiopatias = st.checkbox(
      "CARDIOPATÍAS AGUDAS O CRÓNICAS", key="chk_cardiopatias"
  )
  enfermedad_pulmonar = st.checkbox(
      "ENFERMEDAD PULMONAR CRÓNICA, INCLUYE EPOC Y ASMA",
      key="chk_enfermedad_pulmonar",
  )

with col_r2:
  cancer = st.checkbox("CÁNCER", key="chk_cancer")
  cardiacas_congenitas = st.checkbox(
      "ENFERMEDADES CARDIACAS O PULMONARES CONGÉNITAS U OTROS PADECIMIENTOS",
      key="chk_cardiacas_congenitas",
  )
  insuficiencia_renal = st.checkbox("INSUFICIENCIA RENAL", key="chk_insufren")
  inmunosupresion = st.checkbox(
      "INMUNOSUPRESIÓN ADQUIRIDA", key="chk_inmunosupresion"
  )
  discapacidades = st.checkbox("DISCAPACIDADES", key="chk_discapacidad")
  fibrosis_quistica = st.checkbox("FIBROSIS QUÍSTICA", key="chk_fibrosis")
  hipertension = st.checkbox("HIPERTENSIÓN ARTERIAL", key="chk_hipertension")
  otro_riesgo = st.checkbox("OTRO", key="chk_otro")
  texto_otro_riesgo = (
      st.text_input("Especifique otro grupo de riesgo:", key="txt_otro_riesgo")
      if otro_riesgo
      else ""
  )

# --- ANTECEDENTE Y VACUNA ---
st.markdown(
    '<div class="section-title">6. Antecedente Vacunal y 8. Vacuna de'
    " Interés</div>",
    unsafe_allow_html=True,
)
col_av1, col_av2 = st.columns(2)
with col_av1:
  antecedente_covid = st.radio(
      "¿Cuenta con dosis previa de COVID-19? *",
      options=["SÍ", "NO", "LO DESCONOCE"],
      index=None,
      horizontal=True,
      key="ant_cov",
  )
with col_av2:
  antecedente_influenza = st.radio(
      "¿Cuenta con dosis previa de Influenza? *",
      options=["SÍ", "NO", "LO DESCONOCE"],
      index=None,
      horizontal=True,
      key="ant_inf",
  )

vacuna_interes = st.radio(
    "Seleccione la vacuna de su interés: *",
    options=["AMBAS", "COVID-19", "INFLUENZA"],
    index=None,
    horizontal=True,
    key="input_vacuna",
)

tiene_comorbilidades = (
    vih
    or diabetes
    or obesidad
    or cardiopatias
    or enfermedad_pulmonar
    or cancer
    or cardiacas_congenitas
    or insuficiencia_renal
    or inmunosupresion
    or discapacidades
    or fibrosis_quistica
    or hipertension
    or otro_riesgo
    or personas_embarazadas
    or personal_salud_riesgo
)

grupo_sugerido = (
    determinar_grupo_desde_sheets(
        vacuna_interes,
        edad_total_meses,
        calc_anos,
        "SÍ" if personas_embarazadas else personas_gestantes,
        ocupacion,
        tiene_comorbilidades,
    )
    if vacuna_interes
    else "POR ASIGNAR"
)

st.markdown(
    '<div class="section-title">7. Grupo Objetivo</div>', unsafe_allow_html=True
)
st.markdown(
    f'<div class="card-grupo">🎯 Grupo Objetivo: {grupo_sugerido}</div>',
    unsafe_allow_html=True,
)

st.markdown("---")
if st.button("Registrarme para la jornada", use_container_width=True):
  if not fecha_nacimiento:
    st.error("⚠️ Seleccione correctamente el Día, Mes y Año de Nacimiento.")
  elif not paterno.strip() or not materno.strip() or not nombres.strip():
    st.error("⚠️ Complete Apellido Paterno, Materno y Nombre(s).")
  elif sexo == "SELECCIONE UNA OPCIÓN":
    st.error("⚠️ Seleccione una opción en Sexo.")
  elif vacuna_interes is None:
    st.error("⚠️ Seleccione la vacuna de su interés.")
  else:
    duplicado, folio_previo = verificar_curp_duplicada(
        curp_con_nacimiento,
        sigla_url,
        sufijo_js,
        st.session_state.tipo_jornada,
        val_fecha_app,
    )

    if duplicado:
      st.session_state.paciente_duplicado_info = {
          "nombre": f"{paterno.upper()} {materno.upper()} {nombres.upper()}",
          "folio": folio_previo,
      }
      st.rerun()
    else:
      try:
        folio_asignado = generar_folio_personalizado(
            val_fecha_app, st.session_state.modalidad, sigla_url
        )

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
            "estado_nacimiento": (
                estado_nacimiento
                if estado_nacimiento != "SELECCIONE UN ESTADO"
                else "CDMX"
            ),
            "estado_residencia": (
                estado_residencia
                if estado_residencia != "SELECCIONE UN ESTADO"
                else "CDMX"
            ),
            "curp_con_nacimiento": curp_con_nacimiento,
            "cuenta_derechohabiencia": cuenta_derechohabiencia,
            "vacuna_interes": vacuna_interes,
            "antecedente_covid": antecedente_covid,
            "antecedente_influenza": antecedente_influenza,
            "grupo_sugerido": grupo_sugerido,
            "ocupacion": ocupacion,
            "comorbilidades": comorbilidades_dict,
            "modalidad": st.session_state.modalidad,
        }

        guardar_registro_censal(
            sigla_url=sigla_url,
            sufijo_js=sufijo_js,
            tipo_jornada=st.session_state.tipo_jornada,
            val_fecha_app=val_fecha_app,
            nombre_unidad_completo=st.session_state.nombre_unidad,
            datos_paciente=datos_paciente,
        )

        st.cache_data.clear()
        st.session_state.ultimo_paciente_registrado = {
            "nombre_completo": (
                f"{paterno.upper()} {materno.upper()} {nombres.upper()}"
            ),
            "curp_con_nacimiento": curp_con_nacimiento,
            "vacuna_interes": vacuna_interes,
            "grupo_objetivo": grupo_sugerido,
            "folio": folio_asignado,
        }
        st.rerun()
      except Exception as e:
        st.error("⚠️ Error general al procesar el registro en Google Sheets:")
        st.exception(e)
