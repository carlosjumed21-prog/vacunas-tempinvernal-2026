import datetime
import pandas as pd
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Censo Nominal - Vacunación", page_icon="💉", layout="centered"
)

# Estilo visual limpio y profesional adaptado a entorno médico
st.markdown(
    """
    <style>
        .main-header { font-size: 1.8rem; font-weight: 700; color: #1e3d59; margin-bottom: 0.2rem; }
        .sub-header { font-size: 1rem; color: #576574; margin-bottom: 1.5rem; }
        .section-title { font-size: 1.2rem; font-weight: 600; color: #17b978; margin-top: 1.2rem; margin-bottom: 0.8rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.3rem; }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="main-header">Sistema de Registro Nominal de Vacunación</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-header">Captura de cédula diaria para campañas de inmunización</p>',
    unsafe_allow_html=True,
)


def calcular_edad_detallada(fecha_nac, fecha_ref):
    """Calcula la diferencia exacta en años, meses y días entre dos fechas."""
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


# Lista oficial de los 32 estados de la República Mexicana
estados_mexico = [
    "",
    "Aguascalientes",
    "Baja California",
    "Baja California Sur",
    "Campeche",
    "Chiapas",
    "Chihuahua",
    "Ciudad de México",
    "Coahuila",
    "Colima",
    "Durango",
    "Estado de México",
    "Guanajuato",
    "Guerrero",
    "Hidalgo",
    "Jalisco",
    "Michoacán",
    "Morelos",
    "Nayarit",
    "Nuevo León",
    "Oaxaca",
    "Puebla",
    "Querétaro",
    "Quintana Roo",
    "San Luis Potosí",
    "Sinaloa",
    "Sonora",
    "Tabasco",
    "Tamaulipas",
    "Tlaxcala",
    "Veracruz",
    "Yucatán",
    "Zacatecas",
]

with st.form("form_censo_vacunacion"):

    # --- BLOQUE 1: DATOS GENERALES, FECHA DE REGISTRO Y APLICACIÓN ---
    st.markdown(
        '<div class="section-title">1. Datos Generales y Fechas</div>',
        unsafe_allow_html=True,
    )
    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        fecha_registro = st.date_input(
            "Fecha de Registro (dd/mm/aaaa)",
            value=datetime.date.today(),
            format="DD/MM/YYYY",
        )
    with col_g2:
        fecha_aplicacion = st.date_input(
            "Fecha de Aplicación (dd/mm/aaaa)",
            value=datetime.date.today(),
            format="DD/MM/YYYY",
        )
    with col_g3:
        folio_reg = st.text_input("No. de Registro / Censo (Opcional)")

    # --- BLOQUE 2: IDENTIFICACIÓN DEL PACIENTE Y SEXO ---
    st.markdown(
        '<div class="section-title">2. Identificación del Paciente</div>',
        unsafe_allow_html=True,
    )
    col_n1, col_n2, col_n3 = st.columns(3)
    with col_n1:
        paterno = st.text_input("Apellido Paterno *")
    with col_n2:
        materno = st.text_input("Apellido Materno *")
    with col_n3:
        nombres = st.text_input("Nombre(s) *")

    col_fn1, col_fn2 = st.columns(2)
    with col_fn1:
        # Se muestra la indicación visual previa del formato dd/mm/aaaa
        st.markdown(
            "<span style='font-size: 0.85rem; color: #576574;'>Ejemplo de formato previo: dd/mm/aaaa</span>",
            unsafe_allow_html=True,
        )
        fecha_nacimiento = st.date_input(
            "Fecha de Nacimiento *",
            value=datetime.date(1990, 1, 1),
            min_value=datetime.date(1900, 1, 1),
            max_value=datetime.date.today(),
            format="DD/MM/YYYY",
        )
    with col_fn2:
        sexo = st.selectbox("Sexo *", options=["", "Hombre", "Mujer"])

    # Condicional de embarazo / planes de embarazo si es Mujer
    planes_o_embarazo = "No"
    if sexo == "Mujer":
        st.markdown(
            "<div style='background-color: #f0f4f8; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>",
            unsafe_allow_html=True,
        )
        planes_o_embarazo = st.radio(
            "¿Está embarazada o tiene planes de embarazo?",
            options=["No", "Sí"],
            horizontal=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Cálculo automático de edad en Años, Meses y Días
    calc_anos, calc_meses, calc_dias = calcular_edad_detallada(
        fecha_nacimiento, fecha_aplicacion
    )

    st.markdown(
        '<div class="section-title">Edades Calculadas / Ajustables</div>',
        unsafe_allow_html=True,
    )
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        edad_anos = st.number_input(
            "Años", min_value=0, max_value=120, value=calc_anos
        )
    with col_e2:
        edad_meses = st.number_input(
            "Meses (adicionales / menores de 1 año)",
            min_value=0,
            max_value=11,
            value=calc_meses,
        )
    with col_e3:
        edad_dias = st.number_input(
            "Días (adicionales / recién nacidos)",
            min_value=0,
            max_value=30,
            value=calc_dias,
        )

    # --- BLOQUE 3: DOMICILIO, ESTADOS Y AFILIACIÓN ---
    st.markdown(
        '<div class="section-title">3. Domicilio, Estados y Afiliación</div>',
        unsafe_allow_html=True,
    )
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        estado_nacimiento = st.text_input("Estado de Nacimiento *")
    with col_d2:
        estado_residencia = st.selectbox(
            "Estado de Residencia (Entidad Federativa) *", options=estados_mexico
        )

    col_dom1, col_dom2, col_dom3 = st.columns([2, 1, 1])
    with col_dom1:
        calle = st.text_input("Calle *")
    with col_dom2:
        numero = st.text_input("No. (Ext / Int) *")
    with col_dom3:
        colonia = st.text_input("Colonia *")

    derechohabiencia = st.selectbox(
        "Derechohabiencia *",
        options=[
            "",
            "IMSS",
            "ISSSTE",
            "IMSS-BIENESTAR",
            "PEMEX",
            "SEDENA",
            "SEMAR",
            "ISSFAM",
            "IMSS / IMSS-BIENESTAR",
            "NINGUNA / INSABI / IMSS BIENESTAR (Población Abierta)",
            "OTRA",
        ],
    )

    # --- BLOQUE 4: OCUPACIÓN ---
    st.markdown(
        '<div class="section-title">4. Ocupación</div>', unsafe_allow_html=True
    )
    ocupacion = st.selectbox(
        "Seleccione su Ocupación *",
        options=[
            "",
            "Personal de salud",
            "Jubilado/a",
            "Maestro/a",
            "Administrativo/a",
            "Trabajo en guardería",
            "Otras profesiones",
        ],
    )

    # --- BLOQUE 5: GRUPOS DE RIESGO Y COMORBILIDADES ---
    st.markdown(
        '<div class="section-title">5. Grupos de Riesgo y Comorbilidades</div>',
        unsafe_allow_html=True,
    )
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        # Si se indicó embarazo previamente, se puede reflejar o mantener conectado
        emb = st.checkbox(
            "Embarazadas", value=(True if planes_o_embarazo == "Sí" else False)
        )
        personal_salud_riesgo = st.checkbox(
            "Personal de Salud",
            value=(True if ocupacion == "Personal de salud" else False),
        )
        vih = st.checkbox("VIH / Sida")
        diabetes = st.checkbox("Diabetes Mellitus")
        obesidad = st.checkbox("Obesidad Mórbida")
        cardiopatias = st.checkbox("Cardiopatías Agudas o Crónicas")

    with col_r2:
        epoc = st.checkbox("Enfermedad Pulmonar Crónica (EPOC / Asma)")
        cancer = st.checkbox("Cáncer")
        congenitas = st.checkbox(
            "Enfermedades cardíacas/pulmonares congénitas u otros (salicilatos)"
        )
        insuficiencia_renal = st.checkbox("Insuficiencia Renal")
        inmunosupresion = st.checkbox(
            "Inmunosupresión adquirida (excepto VIH)"
        )
        hipertension = st.checkbox("Hipertensión Arterial Esencial")

    # --- LÓGICA DE AUTODETECCIÓN DE GRUPO OBJETIVO ---
    edad_total_meses = (edad_anos * 12) + edad_meses

    grupo_sugerido = ""
    if 6 <= edad_total_meses <= 59:
        grupo_sugerido = "6 a 59 meses"
    elif edad_anos >= 60:
        grupo_sugerido = "60 y más"
    elif 5 <= edad_anos <= 11:
        grupo_sugerido = "5 a 11 años (Dosis única COVID-19)"
    elif emb or planes_o_embarazo == "Sí":
        grupo_sugerido = "Embarazadas"
    elif personal_salud_riesgo or ocupacion == "Personal de salud":
        grupo_sugerido = "Personal de Salud"
    else:
        grupo_sugerido = "Población general / Otro"

    # --- GRUPO OBJETIVO ---
    st.markdown(
        '<div class="section-title">6. Grupo Objetivo (Detectado Automáticamente)</div>',
        unsafe_allow_html=True,
    )
    lista_grupos = [
        "",
        "6 a 59 meses",
        "60 y más",
        "5 a 11 años (Dosis única COVID-19)",
        "Embarazadas",
        "Personal de Salud",
        "Población general / Otro",
    ]

    indice_default = (
        lista_grupos.index(grupo_sugerido) if grupo_sugerido in lista_grupos else 0
    )

    grupo_objetivo = st.selectbox(
        "Grupo Objetivo (Autocalculado por edad/riesgo, editable)",
        options=lista_grupos,
        index=indice_default,
    )

    # --- BLOQUE 7: ESQUEMA DE VACUNACIÓN ---
    st.markdown(
        '<div class="section-title">7. Biológicos Administrados y Lotes</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**Anti Influenza Estacional**")
    col_inf1, col_inf2 = st.columns(2)
    with col_inf1:
        esquema_influenza = st.selectbox(
            "Tipo de Dosis / Esquema Influenza",
            options=["", "Dosis Anual", "Dosis Única", "1a Dosis", "2a Dosis"],
        )
    with col_inf2:
        lote_influenza = st.text_input("No. de Lote - Influenza")

    st.markdown("**Contra la COVID-19**")
    col_cov1, col_cov2 = st.columns(2)
    with col_cov1:
        esquema_covid = st.selectbox(
            "Tipo de Dosis / Esquema COVID-19",
            options=["", "1a Dosis", "2a Dosis", "Refuerzo", "Dosis Única"],
        )
    with col_cov2:
        lote_covid = st.text_input("No. de Lote - COVID-19")

    st.markdown("---")
    submitted = st.form_submit_button(
        "Guardar y Registrar Censo", use_container_width=True
    )

    if submitted:
        if (
            not paterno
            or not nombres
            or not estado_nacimiento
            or not estado_residencia
            or not calle
            or not numero
            or not colonia
            or not derechohabiencia
            or not ocupacion
        ):
            st.error(
                "Por favor complete los campos obligatorios marcados con (*)."
            )
        else:
            f_reg_str = fecha_registro.strftime("%d/%m/%Y")
            f_nac_str = fecha_nacimiento.strftime("%d/%m/%Y")
            f_app_str = fecha_aplicacion.strftime("%d/%m/%Y")

            st.success(
                f"¡Registro guardado con éxito! Registro: {f_reg_str} | Nacimiento: {f_nac_str} | Ocupación: {ocupacion}"
            )
