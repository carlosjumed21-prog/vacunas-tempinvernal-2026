import datetime
import random
import streamlit as st
import streamlit.components.v1 as components
from config import MAPA_SIGLAS_INVERSO, aplicar_configuracion_global
from utils.sheets import guardar_registro_censal, obtener_cliente_gspread
from config import GOOGLE_SHEET_ID
from aviso_privacidad import mostrar_aviso_privacidad_si_necesario
from utils.email_sender import enviar_comprobante_correo
from utils.logica_registro import (
    calcular_edad_detallada, generar_curp_algoritmica,
    determinar_grupo_desde_sheets, verificar_curp_duplicada,
    estados_mexico, lista_ocupaciones, meses_dict
)

aplicar_configuracion_global("Censo Nominal - Registro", "💉")


def safe_rerun():
    """Rerun compatible con distintas versiones de Streamlit."""
    try:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
            return
    except Exception:
        pass
    try:
        from streamlit.runtime.scriptrunner.script_runner import RerunException
        raise RerunException()
    except Exception:
        st.session_state["_rerun_toggle"] = not st.session_state.get("_rerun_toggle", False)


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
        label, .stRadio label, .stCheckbox label, .stSelectbox label, .stDateInput label, .stTextInput label { font-size: 1.1rem !important; font-weight: 600 !important; color: #161a1d !important; }
        .stCheckbox { margin-bottom: 8px !important; }
        .card-edad { background-color: #f7f4eb; border: 2px solid #a57f2c; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #611232; font-size: 1.3rem !important; margin-bottom: 12px; }
        .card-curp { background-color: #f7f4eb; border: 2px solid #611232; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.2rem !important; margin-bottom: 12px; }
        .card-grupo { background-color: #e8f0ec; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #1e5b4f; font-size: 1.3rem !important; margin-bottom: 12px; }
        .card-info-header { background-color: #f7f4eb; border: 2px solid #1e5b4f; padding: 12px; border-radius: 8px; text-align: center; font-weight: 700; color: #1e5b4f; font-size: 1.1rem !important; margin-bottom: 8px; }
        .stButton>button { background-color: #1e5b4f !important; color: white !important; font-size: 1.2rem !important; font-weight: bold !important; border-radius: 6px !important; padding: 0.6rem 1.1rem !important; }
        input[type="text"] { text-transform: uppercase !important; font-size: 1.1rem !important; }
        div[data-baseweb="select"] > div { font-size: 1rem !important; white-space: normal !important; }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------- NUEVA FUNCIÓN: obtener_folio_proyectado (lazy + cacheada) ----------
@st.cache_data(ttl=60)
def obtener_folio_proyectado(sigla_url, sufijo_js, val_fecha_app, modalidad):
    """
    Calcula el folio proyectado consultando únicamente la columna B (folios)
    para localizar la primera fila libre y así evitar leer toda la hoja.
    Cacheada por (sigla_url, sufijo_js, val_fecha_app, modalidad) durante TTL.
    """
    try:
        client_temp = obtener_cliente_gspread()
        spreadsheet_temp = client_temp.open_by_key(GOOGLE_SHEET_ID)
        nombre_hoja_temp = f"{sigla_url}_{sufijo_js}" if sufijo_js else sigla_url
        ws_temp = spreadsheet_temp.worksheet(nombre_hoja_temp)

        col_b = ws_temp.col_values(2)
        fila_dest_temp = 14
        if len(col_b) >= 14:
            idx_t = 13
            while idx_t < len(col_b):
                if not col_b[idx_t].strip():
                    fila_dest_temp = idx_t + 1
                    break
                idx_t += 2
            else:
                fila_dest_temp = len(col_b) + 1
                if (fila_dest_temp - 14) % 2 != 0:
                    fila_dest_temp += 1

        consecutivo_temp = ((fila_dest_temp - 14) // 2) + 1
        f_str = val_fecha_app.strftime("%Y%m%d")
        m_str = "INT" if modalidad == "INTRAMUROS" else "EXT"
        s_3 = (sigla_url[:3].upper()).ljust(3, "X")
        folio_proyectado = f"{f_str}-{m_str}-{s_3}-{str(consecutivo_temp).zfill(4)}"
        return folio_proyectado
    except Exception:
        return f"{val_fecha_app.strftime('%Y%m%d')}-INT-{sigla_url[:3].upper().ljust(3, 'X')}-0001"

# ---------------------------------------------------------------------------

# --- RECUPERACIÓN DE PARÁMETROS DE URL ---
params = st.query_params
sigla_url = params.get("unidad", "20N").upper()

nombre_base_unidad = MAPA_SIGLAS_INVERSO.get(sigla_url, "20 DE NOVIEMBRE")
sufijo_js = params.get("js", "")
modalidad_url = params.get("modalidad", "INTRAMUROS").upper()
es_admin = params.get("admin", "").lower() in ["true", "1", "si", "yes"] or params.get("rol", "").lower() == "admin"

st.session_state.siglas_unidad = sigla_url
st.session_state.nombre_unidad = f"{nombre_base_unidad} (Brigada {sufijo_js})" if sufijo_js else nombre_base_unidad
st.session_state.tipo_jornada = params.get("jornada", "I")
st.session_state.modalidad = modalidad_url if modalidad_url in ["INTRAMUROS", "EXTRAMUROS"] else "INTRAMUROS"

# --- FECHAS Y CÁLCULO SEGURO DEL SIGUIENTE FOLIO DESDE GOOGLE SHEETS ---
fecha_sistema = datetime.date.today()
fecha_url_str = params.get("fecha", fecha_sistema.strftime("%Y-%m-%d"))
try:
    val_fecha_app = datetime.datetime.strptime(fecha_url_str, "%Y-%m-%d").date()
except:
    val_fecha_app = fecha_sistema

if "folio_proyectado_cached" not in st.session_state:
    st.session_state["folio_proyectado_cached"] = None

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


# --- PROCESAR ACCIÓN: Nuevo Registro solicitada desde el modal ---
if st.session_state.get("accion_nuevo_registro", False):
    keys_a_limpiar = [
        "input_paterno", "input_materno", "input_nombres", "sel_dia", "sel_mes", "sel_anio",
        "input_sexo", "input_estnac", "input_estres", "input_calle", "input_num", "input_col",
        "input_derecho", "input_ocupacion", "input_digitos", "input_vacuna", "ant_cov", "ant_inf",
        "input_correo_paciente",
        "chk_personas_embarazadas", "chk_personal_salud_riesgo", "chk_vih", "chk_diabetes", "chk_obesidad",
        "chk_cardiopatias", "chk_enfermedad_pulmonar", "chk_cancer", "chk_cardiacas_congenitas",
        "chk_insufren", "chk_inmunosupresion", "chk_discapacidad", "chk_fibrosis", "chk_hipertension",
        "chk_otro", "txt_otro_riesgo", "chk_gestante",
        # control adicional
        "folio_proyectado_cached", "submission_id", "enviando_registro", "ultimo_paciente_registrado", "paciente_duplicado_info"
    ]

    for k in keys_a_limpiar:
        if k in st.session_state:
            if k.startswith("chk_"):
                st.session_state[k] = False
            elif k.startswith("sel_"):
                if k == "sel_dia":
                    st.session_state[k] = "Día"
                elif k == "sel_mes":
                    st.session_state[k] = "Mes"
                elif k == "sel_anio":
                    st.session_state[k] = "Año"
                else:
                    st.session_state[k] = ""
            elif k in ["input_sexo", "input_derecho", "input_estnac", "input_estres", "input_ocupacion"]:
                st.session_state[k] = "SELECCIONE UNA OPCIÓN"
            elif k in ["ant_cov", "ant_inf", "input_vacuna", "submission_id"]:
                st.session_state[k] = None
            else:
                st.session_state[k] = ""

    # limpiar query params para evitar re-prefill (opcional)
    try:
        st.experimental_set_query_params()
    except Exception:
        pass

    # Resetear la bandera (la llamada al modal ya forzó rerun)
    st.session_state["accion_nuevo_registro"] = False


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
            f"ISSSTE - REGISTRO DE FOLIO VIGILE\n"
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
            .folio-grande {{ font-size: 1.10rem !important; font-weight: 900 !important; color: #611232 !important; text-align: center; background-color: #f7f4eb; padding: 5px; border-radius: 6px; }}
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
                    <div class="watermark-row"><span>NO ES UN COMPROBANTE OFICIAL</span><span>NO ES UN COMPROBANTE OFICIAL</span></div>
                    <div class="watermark-row"><span>NO ES UN COMPROBANTE OFICIAL</span><span>NO ES UN COMPROBANTE OFICIAL</span></div>
                    <div class="watermark-row"><span>NO ES UN COMPROBANTE OFICIAL</span><span>NO ES UN COMPROBANTE OFICIAL</span></div>
                </div>
                <div class="titulo-ticket">FOLIO DE VACUNACION REGISTRADO</div>
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
                <p class="leyenda-posterior">Posterior a la asistencia de la aplicación de la vacuna se le entregará un comprobante oficial.</p>
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
            # marcamos la intención de nuevo registro y forzamos un rerun; la limpieza
            # efectiva se realizará al inicio de la siguiente ejecución para garantizar
            # un reinicio limpio del formulario.
            st.session_state["accion_nuevo_registro"] = True
            safe_rerun()


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
            safe_rerun()

# --- LLAMADAS A MODALES SEGÚN EL ESTADO ---
if st.session_state.get("ultimo_paciente_registrado") is not None:
    mostrar_modal_comprobante()

if st.session_state.get("paciente_duplicado_info") is not None:
    mostrar_modal_duplicado()

st.markdown('<p class="main-header">Sistema de Registro Nominal de Vacunación</p>', unsafe_allow_html=True)
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
            st.session_state.input_estnac = random.choice(estados_mexio[1:])
            st.session_state.input_estres = st.session_state.input_estnac
            st.session_state.input_calle = "AV. REVOLUCIÓN"
            st.session_state.input_num = str(random.randint(100, 999))
            st.session_state.input_colonia = "CENTRO"
            st.session_state.input_derecho = "SÍ"
            st.session_state.input_ocupacion = random.choice(lista_ocupaciones[1:])
            st.session_state.input_correo_paciente = "carlosju.med21@gmail.com"
            st.session_state.ant_cov = random.choice(["SÍ", "NO", "LO DESCONOCE"])
            st.session_state.ant_inf = random.choice(["SÍ", "NO", "LO DESCONOCE"])
            st.session_state.input_vacuna = random.choice(["AMBAS", "COVID-19", "INFLUENZA"])
            if st.session_state.input_sexo == "MUJER":
                st.session_state.chk_gestante = random.choice(["NO", "SÍ"])
            safe_rerun()

# --- APARTADO 1: FECHAS Y FOLIO ---
st.markdown('<div class="section-title">1. Control de Fechas y Folio</div>', unsafe_allow_html=True)
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    st.markdown(
        f'<div class="card-info-header">📅 Fecha de Registro<br><b>{fecha_sistema.strftime("%d/%m/%Y")}</b></div>',
        unsafe_allow_html=True
    )
with col_f2:
    st.markdown(
        f'<div class="card-info-header">🗓️ Fecha de Aplicación<br><b>{val_fecha_app.strftime("%d/%m/%Y")}</b></div>',
        unsafe_allow_html=True
    )
with col_f3:
    # Para el formulario público NO mostramos ni calculamos el folio antes del registro.
    # Mostramos un placeholder indicando que el folio se asignará al finalizar el registro.
    # Si es un administrador (es_admin), dejamos un botón para calcular folio proyectado (solo para pruebas/operación).
    if es_admin:
        folio_cached = st.session_state.get("folio_proyectado_cached")
        if folio_cached:
            st.markdown(f'<div class="card-info-header">🔖 Folio de Registro (Proyectado)<br><b>{folio_cached}</b></div>', unsafe_allow_html=True)
            if st.button("🧾 Borrar folio proyectado (limpiar cache)", key="btn_clear_folio"):
                st.session_state["folio_proyectado_cached"] = None
                safe_rerun()
        else:
            st.markdown(f'<div class="card-info-header">🔖 Folio de Registro (Proyección solo para administración)<br><b>— (Pulse calcular)</b></div>', unsafe_allow_html=True)
            if st.button("Calcular folio proyectado (Admin)", key="btn_calcular_folio_admin"):
                with st.spinner("Calculando folio proyectado desde Google Sheets..."):
                    folio_calculado = obtener_folio_proyectado(sigla_url, sufijo_js, val_fecha_app, st.session_state.modalidad)
                    st.session_state["folio_proyectado_cached"] = folio_calculado
                safe_rerun()
    else:
        # Texto para usuarios públicos: se asignará un folio al finalizar el registro
        st.markdown(
            f'<div class="card-info-header">🔖 Folio de Registro<br><b>— (Se asignará al finalizar el registro)</b></div>',
            unsafe_allow_html=True
        )

# --- IDENTIFICACIÓN DEL PACIENTE ---
...