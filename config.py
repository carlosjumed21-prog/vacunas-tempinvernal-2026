import streamlit as st

# --- CONFIGURACIÓN UNIVERSAL DE ESTILOS Y OCULTACIÓN DE BARRA LATERAL ---
def aplicar_configuracion_global(titulo_pagina="Sistema Censo Nominal", icono="💉"):
    st.set_page_config(
        page_title=titulo_pagina,
        page_icon=icono,
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # CSS estricto para ocultar por completo la barra lateral nativa y controles de Streamlit
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="collapsedControl"], section[data-testid="stSidebar"] {
                display: none !important;
                visibility: hidden !important;
            }
            .stApp { background-color: #fbf9f4; }
        </style>
    """, unsafe_allow_html=True)

# --- DICCIONARIO UNIVERSAL DE UNIDADES ISSSTE ---
UNIDADES_ISSSTE = {
    "Seleccione una unidad médica...": {"sigla": "", "dir": ""},
    "20 DE NOVIEMBRE": {
        "sigla": "20N",
        "dir": "Avenida Félix Cuevas 540, Del Valle Sur, Benito Juárez, 03100 Ciudad de México, CDMX",
    },
    "CHURUBUSCO": {
        "sigla": "CHU",
        "dir": "Calzada de Tlalpan 4430, Toriello Guerra, Tlalpan, 14050 Ciudad de México, CDMX",
    },
    "CLIDDA": {
        "sigla": "CLI",
        "dir": "San Fernando 15, Toriello Guerra, Tlalpan, 14050 Ciudad de México, CDMX",
    },
    "COYOACAN": {
        "sigla": "COY",
        "dir": "Avenida Cuauhtémoc 330, Del Carmen, Coyoacán, 04100 Ciudad de México, CDMX",
    },
    "DEL VALLE": {
        "sigla": "DVA",
        "dir": "Cacho 35, Del Valle Norte, Benito Juárez, 03103 Ciudad de México, CDMX",
    },
    "DIVISION DEL NORTE": {
        "sigla": "DVN",
        "dir": "Avenida División del Norte 3233, Xoco, Benito Juárez, 03330 Ciudad de México, CDMX",
    },
    "DR. DARIO FERNANDEZ FIERRO": {
        "sigla": "DFF",
        "dir": "Avenida Revolución 1182, Tlacopac, Álvaro Obregón, 01049 Ciudad de México, CDMX",
    },
    "DR. IGNACIO CHAVEZ": {
        "sigla": "ICH",
        "dir": "Eje 1 Poniente Av. Cuauhtémoc s/n, Doctores, Cuauhtémoc, 06720 Ciudad de México, CDMX",
    },
    "ERMITA": {
        "sigla": "ERM",
        "dir": "Ermita Iztapalapa 67, Ermita, Benito Juárez, 03590 Ciudad de México, CDMX",
    },
    "FUENTES BROTANTES": {
        "sigla": "FBR",
        "dir": "Fuentes Brotantes s/n, Fuentes Brotantes, Tlalpan, 14410 Ciudad de México, CDMX",
    },
    "HG DRA. MATILDE PETRA MONTOYA LAFRAGUA": {
        "sigla": "MPM",
        "dir": "Avenida Tláhuac s/n, San Lorenzo Tezonco, Iztapalapa, 13266 Ciudad de México, CDMX",
    },
    "MILPA ALTA": {
        "sigla": "MIL",
        "dir": "Prolongación Matamoros s/n, Villa Milpa Alta, Milpa Alta, 12000 Ciudad de México, CDMX",
    },
    "NARVARTE": {
        "sigla": "NAR",
        "dir": "Avenida Cuauhtémoc 625, Narvarte Poniente, Benito Juárez, 03020 Ciudad de México, CDMX",
    },
    "TLALPAN": {
        "sigla": "TLA",
        "dir": "Calzada de Tlalpan 4800, Toriello Guerra, Tlalpan, 14050 Ciudad de México, CDMX",
    },
    "VILLA ALVARO OBREGON": {
        "sigla": "VAO",
        "dir": "Calle 10 s/n, Tolteca, Álvaro Obregón, 01150 Ciudad de México, CDMX",
    },
    "XOCHIMILCO": {
        "sigla": "XOC",
        "dir": "Providencia s/n, Barrio San Marcos, Xochimilco, 16050 Ciudad de México, CDMX",
    },
}

MAPA_SIGLAS_INVERSO = {v["sigla"]: k for k, v in UNIDADES_ISSSTE.items() if v["sigla"]}

GOOGLE_SHEET_ID = "1TH2KkQzNe4HwBcuJK_QR4gWfQ-wiyAyyczdTmLzn1Ds"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
