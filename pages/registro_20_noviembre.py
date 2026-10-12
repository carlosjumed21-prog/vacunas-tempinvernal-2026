import datetime
import streamlit as st
from config import MAPA_SIGLAS_INVERSO, aplicar_configuracion_global
from utils.sheets import guardar_registro_censal_20_nov
from aviso_privacidad import mostrar_aviso_privacidad_si_necesario

# Importar todos los componentes y funciones auxiliares desde el archivo modular en utils
from utils.componentes_censo_20n import (
    cargar_catalogos_excel,
    calcular_edad_detallada,
    estados_mexico,
    municipios_por_estado,
    generar_curp_algoritmica,
    generar_rfc_algoritmico,
    mostrar_modal_comprobante_20n
)

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

# Mostrar modal de comprobante si existe un registro previo en la sesión
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
