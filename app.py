import streamlit as st

# Configuración de página de Streamlit
st.set_page_config(
    page_title="Sistema Censo Nominal VIGILE",
    page_icon="💉",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        /* Ocultar elementos nativos de Streamlit Cloud */
        header[data-testid="stHeader"] { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        
        /* Recuperar el fondo institucional elegante */
        .stApp {
            background-color: #f7f4eb !important;
        }
        
        /* Limpiar contenedores y márgenes */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            max-width: 800px;
        }
        
        /* Estilos institucionales personalizados */
        .main-header { 
            font-size: 2.2rem !important; 
            font-weight: 800 !important; 
            color: #1e5b4f !important; 
            margin-bottom: 0.2rem; 
            border-bottom: 3px solid #a57f2c; 
            padding-bottom: 10px; 
            text-align: center; 
        }
        .sub-header { 
            font-size: 1.2rem !important; 
            color: #611232 !important; 
            margin-bottom: 1.5rem; 
            font-weight: 700 !important; 
            text-align: center; 
        }
        .card-menu { 
            background-color: #ffffff; 
            border: 2px solid #a57f2c; 
            padding: 20px; 
            border-radius: 10px; 
            text-align: center; 
            margin-bottom: 20px; 
        }
        .stButton>button { 
            background-color: #1e5b4f !important; 
            color: white !important; 
            font-size: 1.1rem !important; 
            font-weight: bold !important; 
            border-radius: 6px !important; 
            padding: 0.6rem 1.1rem !important; 
            width: 100%;
        }
        
        /* Contenedor unificado y limpio para el login con fondo blanco total */
        .auth-box { 
            background: #ffffff; 
            padding: 30px; 
            border-radius: 12px; 
            border: 2px solid #a57f2c; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
            margin: 0 auto;
        }
        
        /* Forzar que el formulario interno se integre sin bordes ni cajas separadas */
        [data-testid="stForm"] {
            background-color: transparent !important;
            border: none !important;
            padding: 0 !important;
            box-shadow: none !important;
        }

        .footer-text { 
            text-align: center; 
            color: #611232; 
            font-weight: 600; 
            font-size: 0.85rem; 
            margin-top: 3rem; 
            border-top: 1px solid #e6d194;
            padding-top: 15px;
        }
    </style>
""", unsafe_allow_html=True)

# Inicializar estados de sesión para el control de acceso
if "auth_registro" not in st.session_state:
    st.session_state["auth_registro"] = False

# ===========================================================
# BLOQUE DE AUTENTICACIÓN INICIAL
# ===========================================================
if not st.session_state.get("auth_registro", False) and not st.session_state.get("authenticated", False):
    
    st.markdown('<p class="main-header">Sistema de Jornadas de Vacunación</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">🔐 Autenticación Requerida - Registro Nominal</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        # Contenedor unificado blanco
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; margin-bottom: 1.2rem; color: #161a1d; font-weight: 500;'>Introduce tu correo institucional autorizado y la contraseña operativa para acceder al sistema.</p>", unsafe_allow_html=True)
        
        with st.form("form_auth_principal"):
            usuario_input = st.text_input("Correo electrónico / Usuario").strip().lower()
            password_input = st.text_input("Contraseña", type="password").strip()
            submitted = st.form_submit_button("Validar Acceso", use_container_width=True)
            
            if submitted:
                correos_autorizados = {
                    "carlosju.med21@gmail.com": "OtaniOrochi26",
                    "wendy.hernandeza@issste.gob.mx": "MedPrev26"
                }
                
                password_operativa = "OperativoInv26"
                
                admin_user = st.secrets.get("ADMIN_USER", "admin").strip().lower()
                admin_pass = st.secrets.get("ADMIN_PASSWORD", "VIGILE2026").strip()
                
                acceso_permitido = False
                
                if usuario_input == admin_user and password_input == admin_pass:
                    acceso_permitido = True
                elif usuario_input in correos_autorizados and password_input == correos_autorizados[usuario_input]:
                    acceso_permitido = True
                elif password_input == password_operativa and "@" in usuario_input:
                    acceso_permitido = True
                    
                if acceso_permitido:
                    st.session_state["auth_registro"] = True
                    st.success("¡Credenciales correctas! Ingresando al sistema...")
                    st.rerun()
                else:
                    st.error("Correo o contraseña incorrectos. Verifique sus datos o espacios en blanco.")
        
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
        <div class="footer-text">
            Subdelegación Sur ISSSTE<br>
            Medicina Preventiva - Epidemiología<br>
            © 2026 Carlos Ju R2 Epidemiología. Proyecto de Captura de Jornadas de Vacunación.<br>
            Todos los derechos reservados. Prohibida su reproducción total o parcial sin autorización.
        </div>
    """, unsafe_allow_html=True)

# ===========================================================
# APLICACIÓN PRINCIPAL (Visible solo tras autenticarse)
# ===========================================================
else:
    col_top1, col_top2, col_top3 = st.columns([2, 2, 1])
    with col_top3:
        if st.button("🚪 Cerrar Sesión", use_container_width=True, key="btn_logout"):
            st.session_state["auth_registro"] = False
            st.session_state["authenticated"] = False
            st.rerun()

    st.markdown('<p class="main-header">Sistema de Jornadas de Vacunación y Censo Nominal</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Módulo Principal de Acceso Institucional</p>', unsafe_allow_html=True)

    params = st.query_params
    unidad_url = params.get("unidad", "").upper()
    jornada_url = params.get("jornada", "I").upper()

    if jornada_url == "E":
        modalidad_texto = "EXTRAMUROS"
    elif jornada_url == "M":
        modalidad_texto = "BRIGADA MÓVIL"
    else:
        modalidad_texto = "INTRAMUROS"

    pagina_formulario = "pages/registro_20_noviembre.py" if unidad_url == "20N" else "pages/1_formulario.py"

    if unidad_url:
        st.markdown(f"""
            <div style="background-color: #ffffff; border: 2px solid #1e5b4f; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                <span style="font-weight: bold; color: #1e5b4f; font-size: 1.1rem;">🔗 Enlace Institucional Detectado</span><br>
                <span>Unidad clave: <b>{unidad_url}</b> | Modalidad: <b>{modalidad_texto}</b></span><br>
                <span style="font-size: 0.85rem; color: #611232;">{'✨ Redirección especializada activada para CMN 20 de Noviembre.' if unidad_url == '20N' else ''}</span>
            </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
            <div class="card-menu">
                <h3>📝 Registro Nominal</h3>
                <p>Acceso al formulario de captura para pacientes en jornadas de vacunación.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Ir al Formulario de Registro", use_container_width=True):
            st.switch_page(pagina_formulario)

    with col2:
        st.markdown("""
            <div class="card-menu">
                <h3>📋 Operatividad</h3>
                <p>Captura de dosis aplicadas, lotes y comprobantes.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Ir a Consulta CENSIA", use_container_width=True):
            st.switch_page("pages/2_consulta_censia.py")

    st.markdown("""
        <div class="footer-text">
            Subdelegación Sur ISSSTE<br>
            Medicina Preventiva - Epidemiología<br>
            © 2026 Carlos Ju R2 Epidemiología. Proyecto de Captura de Jornadas de Vacunación.<br>
            Todos los derechos reservados. Prohibida su reproducción total o parcial sin autorización.
        </div>
    """, unsafe_allow_html=True)
