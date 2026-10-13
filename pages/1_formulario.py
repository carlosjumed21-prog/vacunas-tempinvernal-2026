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
        # Streamlit 1.21+ tiene st.rerun()
        st.rerun()
        return
    except Exception:
        pass

    try:
        # Compatibilidad con versiones que aún exponen experimental_rerun
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
            return
    except Exception:
        pass

    # Último recurso: toggle en session_state para forzar re-render
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

# --- FECHAS Y ESTADOS INICIALES ---
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

if "ant_cov" not in st.session_state:
    st.session_state.ant_cov = None
if "ant_inf" not in st.session_state:
    st.session_state.ant_inf = None
if "input_vacuna" not in st.session_state:
    st.session_state.input_vacuna = None

# --- CALLBACKS PARA BOTONES (UNA SOLA EJECUCIÓN POR CLIC) ---

def limpiar_nuevo_registro():
    """Limpia campos y regresa al formulario principal."""
    st.session_state.ultimo_paciente_registrado = None

    keys_a_limpiar = [
        "input_paterno", "input_materno", "input_nombres",
        "sel_dia", "sel_mes", "sel_anio", "input_sexo",
        "input_estnac", "input_estres", "input_calle",
        "input_num", "input_col", "input_correo_paciente",
        "input_derecho", "input_ocupacion", "input_digitos",
        "ant_cov", "ant_inf", "input_vacuna", "chk_gestante",
        "chk_personas_embarazadas", "chk_personal_salud_riesgo",
        "chk_vih", "chk_diabetes", "chk_obesidad", "chk_cardiopatias",
        "chk_enfermedad_pulmonar", "chk_cancer", "chk_cardiacas_congenitas",
        "chk_insufren", "chk_inmunosupresion", "chk_discapacidad",
        "chk_fibrosis", "chk_hipertension", "chk_otro", "txt_otro_riesgo",
        "input_colonia", "input_correo_registro_modal", "_registro_error", "_registro_exception"
    ]

    for k in keys_a_limpiar:
        st.session_state.pop(k, None)

    safe_rerun()


def limpiar_paciente_duplicado():
    """Cerrar modal de duplicado y reiniciar vista."""
    st.session_state.paciente_duplicado_info = None
    safe_rerun()


def procesar_registro_callback():
    """Procesa el registro: valida, verifica duplicado y guarda en Sheets."""
    try:
        # Leer campos desde session_state (vienen de widgets)
        paterno = st.session_state.get("input_paterno", "") or ""
        materno = st.session_state.get("input_materno", "") or ""
        nombres = st.session_state.get("input_nombres", "") or ""
        dia_sel = st.session_state.get("sel_dia", "Día")
        mes_sel = st.session_state.get("sel_mes", "Mes")
        anio_sel = st.session_state.get("sel_anio", "Año")
        sexo = st.session_state.get("input_sexo", "SELECCIONE UNA OPCIÓN")
        estado_nacimiento = st.session_state.get("input_estnac", "SELECCIONE UN ESTADO")
        estado_residencia = st.session_state.get("input_estres", "SELECCIONE UN ESTADO")
        calle = st.session_state.get("input_calle", "") or ""
        numero = st.session_state.get("input_num", "") or ""
        colonia = st.session_state.get("input_col", "") or st.session_state.get("input_colonia", "") or ""
        correo_paciente = (st.session_state.get("input_correo_paciente", "") or "").strip()
        cuenta_derechohabiencia = st.session_state.get("input_derecho", "")
        ocupacion = st.session_state.get("input_ocupacion", lista_ocupaciones[0]) or lista_ocupaciones[0]
        digitos_faltantes = st.session_state.get("input_digitos", "") or ""
        personas_gestantes = st.session_state.get("chk_gestante", "NO") if st.session_state.get("input_sexo","") == "MUJER" else "NO"

        # Comorbilidades (booleans)
        personas_embarazadas = st.session_state.get("chk_personas_embarazadas", False)
        personal_salud_riesgo = st.session_state.get("chk_personal_salud_riesgo", False)
        vih = st.session_state.get("chk_vih", False)
        diabetes = st.session_state.get("chk_diabetes", False)
        obesidad = st.session_state.get("chk_obesidad", False)
        cardiopatias = st.session_state.get("chk_cardiopatias", False)
        enfermedad_pulmonar = st.session_state.get("chk_enfermedad_pulmonar", False)
        cancer = st.session_state.get("chk_cancer", False)
        cardiacas_congenitas = st.session_state.get("chk_cardiacas_congenitas", False)
        insuficiencia_renal = st.session_state.get("chk_insufren", False)
        inmunosupresion = st.session_state.get("chk_inmunosupresion", False)
        discapacidades = st.session_state.get("chk_discapacidad", False)
        fibrosis_quistica = st.session_state.get("chk_fibrosis", False)
        hipertension = st.session_state.get("chk_hipertension", False)
        otro_riesgo = st.session_state.get("chk_otro", False)
        texto_otro_riesgo = st.session_state.get("txt_otro_riesgo", "") or ""

        vacuna_interes = st.session_state.get("input_vacuna", None)
        # Fecha de aplicación y unidad
        sigla = sigla_url
        sufijo = sufijo_js
        tipo_jornada = st.session_state.get("tipo_jornada", "I")
        fecha_aplicacion = val_fecha_app

        # Validaciones
        if dia_sel == "Día" or mes_sel == "Mes" or anio_sel == "Año":
            st.session_state["_registro_error"] = "⚠️ Seleccione correctamente el Día, Mes y Año de Nacimiento."
            safe_rerun()
            return

        if not paterno.strip() or not materno.strip() or not nombres.strip():
            st.session_state["_registro_error"] = "⚠️ Complete Apellido Paterno, Materno y Nombre(s)."
            safe_rerun()
            return

        if not correo_paciente:
            st.session_state["_registro_error"] = "⚠️ Ingrese el correo electrónico para enviarle su comprobante de folio."
            safe_rerun()
            return

        if sexo == "SELECCIONE UNA OPCIÓN":
            st.session_state["_registro_error"] = "⚠️ Seleccione una opción en Sexo."
            safe_rerun()
            return

        if vacuna_interes is None:
            st.session_state["_registro_error"] = "⚠️ Seleccione la vacuna de su interés."
            safe_rerun()
            return

        # Construir fecha_nacimiento
        try:
            fecha_nacimiento = datetime.date(int(anio_sel), meses_dict[mes_sel], int(dia_sel))
        except Exception:
            st.session_state["_registro_error"] = "⚠️ La combinación de fecha seleccionada no es válida."
            safe_rerun()
            return

        # Calcular edad
        calc_anos, calc_meses, _ = calcular_edad_detallada(fecha_nacimiento, fecha_aplicacion)
        edad_total_meses = (calc_anos * 12) + calc_meses

        # Generar CURP algorítmica
        curp_alg = generar_curp_algoritmica(paterno, materno, nombres, fecha_nacimiento, sexo, estado_nacimiento, digitos_faltantes)
        curp_con_nacimiento = f"{curp_alg}/{estado_nacimiento.upper()}" if estado_nacimiento != "SELECCIONE UN ESTADO" and "COMPLETA" not in curp_alg else curp_alg

        tiene_comorbilidades = (
            bool(vih) or bool(diabetes) or bool(obesidad) or bool(cardiopatias) or bool(enfermedad_pulmonar) or bool(cancer) or
            bool(cardiacas_congenitas) or bool(insuficiencia_renal) or bool(inmunosupresion) or bool(discapacidades) or
            bool(fibrosis_quistica) or bool(hipertension) or bool(otro_riesgo)
        )

        grupo_sugerido = determinar_grupo_desde_sheets(
            vacuna_interes,
            edad_total_meses,
            calc_anos,
            "SÍ" if personas_gestantes == "SÍ" else "NO",
            ocupacion,
            tiene_comorbilidades
        ) if vacuna_interes else "SIN DATO"

        # Verificar duplicado por CURP
        try:
            duplicado_local, folio_previo = verificar_curp_duplicada(curp_con_nacimiento, sigla, sufijo, tipo_jornada, fecha_aplicacion)
        except Exception as e:
            st.session_state["_registro_exception"] = f"Error verificando duplicado: {e}"
            safe_rerun()
            return

        if duplicado_local:
            st.session_state.paciente_duplicado_info = {
                "nombre": f"{paterno.upper()} {materno.upper()} {nombres.upper()}",
                "folio": folio_previo
            }
            safe_rerun()
            return

        # Preparar dict de comorbilidades y datos del paciente
        comorbilidades_dict = {
            "personas_embarazadas": personas_gestantes, "personal_salud_riesgo": "SÍ" if personal_salud_riesgo else "NO",
            "vih": "SÍ" if vih else "NO", "diabetes": "SÍ" if diabetes else "NO", "obesidad": "SÍ" if obesidad else "NO",
            "cardiopatias": "SÍ" if cardiopatias else "NO", "enfermedad_pulmonar": "SÍ" if enfermedad_pulmonar else "NO",
            "cancer": "SÍ" if cancer else "NO", "cardiacas_congenitas": "SÍ" if cardiacas_congenitas else "NO",
            "insuficiencia_renal": "SÍ" if insuficiencia_renal else "NO", "inmunosupresion": "SÍ" if inmunosupresion else "NO",
            "discapacidades": "SÍ" if discapacidades else "NO", "fibrosis_quistica": "SÍ" if fibrosis_quistica else "NO",
            "hipertension": "SÍ" if hipertension else "NO", "otro": "SÍ" if otro_riesgo else "NO", "texto_otro": texto_otro_riesgo.upper() if texto_otro_riesgo else "",
        }

        datos_paciente = {
            "paterno": paterno, "materno": materno, "nombres": nombres,
            "fecha_nacimiento": fecha_nacimiento, "calc_anos": calc_anos, "calc_meses": calc_meses,
            "sexo": sexo, "calle": calle,*

