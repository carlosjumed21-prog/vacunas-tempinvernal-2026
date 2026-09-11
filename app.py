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

with st.form("form_censo_vacunacion"):

    # --- DATOS GENERALES Y FECHA DE APLICACIÓN ---
    st.markdown('<div class="section-title">1. Datos Generales y Fecha</div>', unsafe_allow_html=True)
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_aplicacion = st.date_input(
            "Fecha de Aplicación", value=datetime.date.today()
        )
    with col_f2:
        folio_reg = st.text_input("No. de Registro / Censo (Opcional)")

    # --- IDENTIFICACIÓN DEL PACIENTE ---
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

    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        dia_nac = st.selectbox(
            "Día de Nacimiento", options=[""] + [str(i).zfill(2) for i in range(1, 32)]
        )
    with col_d2:
        mes_nac = st.selectbox(
            "Mes de Nacimiento",
            options=[
                "",
                "Enero",
                "Febrero",
                "Marzo",
                "Abril",
                "Mayo",
                "Junio",
                "Julio",
                "Agosto",
                "Septiembre",
                "Octubre",
                "Noviembre",
                "Diciembre",
            ],
        )
    with col_d3:
        anio_nac = st.number_input(
            "Año de Nacimiento", min_value=1900, max_value=2026, value=1990, step=1
        )

    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        edad_anos = st.number_input("Edad (Años)", min_value=0, max_value=120, value=0)
    with col_e2:
        edad_meses = st.number_input(
            "Edad (Meses - menores de 1 año)", min_value=0, max_value=11, value=0
        )
    with col_e3:
        sexo = st.selectbox("Sexo *", options=["", "Masculino", "Femenino"])

    # --- DOMICILIO Y DERECHOHABIENCIA ---
    st.markdown(
        '<div class="section-title">3. Domicilio y Afiliación</div>',
        unsafe_allow_html=True,
    )
    col_dom1, col_dom2 = st.columns([2, 1])
    with col_dom1:
        calle_num = st.text_input("Calle y No. *")
    with col_dom2:
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

    # --- GRUPO OBJETIVO ---
    st.markdown(
        '<div class="section-title">4. Grupo Objetivo</div>', unsafe_allow_html=True
    )
    grupo_objetivo = st.selectbox(
        "Seleccione el Grupo Objetivo",
        options=[
            "",
            "6 a 59 meses",
            "60 y más",
            "5 a 11 años (Dosis única COVID-19)",
            "Población general / Otro",
        ],
    )

    # --- GRUPOS DE RIESGO Y COMORBILIDADES ---
    st.markdown(
        '<div class="section-title">5. Grupos de Riesgo y Comorbilidades</div>',
        unsafe_allow_html=True,
    )
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        emb = st.checkbox("Embarazadas")
        personal_salud = st.checkbox("Personal de Salud")
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

    # --- ESQUEMA DE VACUNACIÓN ---
    st.markdown(
        '<div class="section-title">6. Biológicos Administrados y Lotes</div>',
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
        if not paterno or not nombres or not calle_num or not derechohabiencia:
            st.error(
                "Por favor complete los campos obligatorios marcados con (*)."
            )
        else:
            # Aquí puedes conectar la lógica para guardar en Google Sheets usando gspread o almacenar en CSV local/base de datos.
            st.success(
                "¡Registro capturado exitosamente y agregado al censo nominal!"
            )
