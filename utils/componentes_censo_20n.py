import datetime
import unicodedata
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# --- CARGA DINÁMICA DE CATÁLOGOS DESDE LA PESTAÑA 'LISTAS' ---
@st.cache_data(show_spinner=False)
def cargar_catalogos_excel():
    try:
        df = pd.read_excel("assets/lista vac.xlsx", sheet_name="LISTAS", header=0, dtype=str)
        
        def limpiar_columna(serie):
            if serie is not None and not serie.empty:
                return sorted([str(x).strip().upper() for x in serie.dropna().unique() if str(x).strip() and str(x).strip().upper() not in ["NAN", "NAT", ""]])
            return []

        opt_dh = limpiar_columna(df.iloc[:, 0]) if df.shape[1] > 0 else []
        opt_serv = limpiar_columna(df.iloc[:, 1]) if df.shape[1] > 1 else []
        opt_coord = limpiar_columna(df.iloc[:, 2]) if df.shape[1] > 2 else []
        opt_cat = limpiar_columna(df.iloc[:, 3]) if df.shape[1] > 3 else []
        opt_turno = limpiar_columna(df.iloc[:, 4]) if df.shape[1] > 4 else []

        return (
            opt_dh or ["TRABAJADOR ACTIVO", "JUBILADO / PENSIONADO", "FAMILIAR", "OTRO"],
            opt_serv or ["EPIDEMIOLOGÍA", "URGENCIAS", "PEDIATRÍA", "MEDICINA INTERNA", "CIRUGÍA", "OTRO"],
            opt_coord or ["DIRECCIÓN MÉDICA", "SUBDIRECCIÓN", "ENFERMERÍA", "OTRO"],
            opt_cat or ["MÉDICO", "ENFERMERA", "ADMINISTRATIVO", "OTRO"],
            opt_turno or ["MATUTINO", "VESPERTINO", "NOCTURNO", "JORNADA ACUMULADA"]
        )
    except Exception as e:
        return (
            ["TRABAJADOR ACTIVO", "JUBILADO / PENSIONADO", "FAMILIAR", "OTRO"],
            ["EPIDEMIOLOGÍA", "URGENCIAS", "PEDIATRÍA", "MEDICINA INTERNA", "CIRUGÍA", "OTRO"],
            ["DIRECCIÓN MÉDICA", "SUBDIRECCIÓN", "ENFERMERÍA", "OTRO"],
            ["MÉDICO", "ENFERMERA", "ADMINISTRATIVO", "OTRO"],
            ["MATUTINO", "VESPERTINO", "NOCTURNO", "JORNADA ACUMULADA"]
        )

def calcular_edad_detallada(fecha_nac, fecha_ref):
    if not fecha_nac or not fecha_ref or fecha_nac > fecha_ref:
        return 0, 0, 0
    anos = fecha_ref.year - fecha_nac.year
    meses = fecha_ref.month - fecha_nac.month
    dias = fecha_ref.day - fecha_nac.day
    if dias < 0:
        meses -= 1
        mes_anterior = fecha_ref.month - 1 if fecha_ref.month > 1 else 12
        anio_anterior = fecha_ref.year if fecha_ref.month > 1 else fecha_ref.year - 1
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
    "AGUASCALIENTES": "AS", "BAJA CALIFORNIA": "BC", "BAJA CALIFORNIA SUR": "BS",
    "CAMPECHE": "CC", "CHIAPAS": "CS", "CHIHUAHUA": "CH", "CIUDAD DE MÉXICO": "DF",
    "COAHUILA": "CL", "COLIMA": "CM", "DURANGO": "DG", "ESTADO DE MÉXICO": "MC",
    "GUANAJUATO": "GT", "GUERRERO": "GR", "HIDALGO": "HG", "JALISCO": "JC",
    "MICHOACÁN": "MN", "MORELOS": "MS", "NAYARIT": "NT", "NUEVO LEÓN": "NL",
    "OAXACA": "OC", "PUEBLA": "PL", "QUERÉTARO": "QT", "QUINTANA ROO": "QR",
    "SAN LUIS POTOSÍ": "SP", "SINALOA": "SL", "SONORA": "SR", "TABASCO": "TC",
    "TAMAULIPAS": "TS", "TLAXCALA": "TL", "VERACRUZ": "VZ", "YUCATÁN": "YN", "ZACATECAS": "ZS",
}

municipios_por_estado = {
    "CIUDAD DE MÉXICO": [
        "ÁLVARO OBREGÓN", "AZCAPOTZALCO", "BENITO JUÁREZ", "COYOACÁN", "CUAJIMALPA DE MORELOS",
        "CUAUHTÉMOC", "GUSTAVO A. MADERO", "IZTACALCO", "IZTAPALAPA", "LA MAGDALENA CONTRERAS",
        "MIGUEL HIDALGO", "MILPA ALTA", "TÁHUAC", "TLALPAN", "VENUSTIANO CARRANZA", "XOCHIMILCO"
    ],
    "ESTADO DE MÉXICO": [
        "ECATEPEC DE MORELOS", "NEZAHUALCÓYOTL", "NAUCALPAN DE JUÁREZ", "TOLUCA", "TLANEPANTLA DE BAZ",
        "CHIMALHUACÁN", "CUAUTITLÁN IZCALLI", "ATIZAPÁN DE ZARAGOZA", "IXTAPALUCA", "CHICOLOAPAN",
        "METEPEC", "TEXCOCO", "VALLE DE CHALCO SOLIDARIDAD", "ACAMBAY", "ATLACOMULCO", "OTRO"
    ],
    "PUEBLA": [
        "PUEBLA", "TEHUACÁN", "SAN MARTÍN TEXMELUCAN", "ATLIXCO", "SAN PEDRO CHOLULA",
        "SAN ANDRÉS CHOLULA", "TECAMACHALCO", "HUAUCHINANGO", "ZACATLÁN", "TEZIUTLÁN", "OTRO"
    ],
    "HIDALGO": [
        "PACHUCA DE SOTO", "TULA DE ALLENDE", "TULANCINGO DE BRAVO", "TIZAYUCA", "TEPEJI DEL RÍO", "HUEJUTLA DE REYES", "OTRO"
    ],
    "MORELOS": [
        "CUERNAVACA", "JIUTEPEC", "CUAUTLA", "TEMIXCO", "EMILIANO ZAPATA", "YAUTEPEC", "JOJUTLA", "OTRO"
    ],
    "TLAXCALA": [
        "TLAXCALA", "APIZACO", "HUAMANTLA", "CHIAUTEMPAN", "ZACATELCO", "SAN PABLO DEL MONTE", "OTRO"
    ],
    "VERACRUZ": [
        "VERACRUZ", "XALAPA", "COATZACOALCOS", "CÓRDOBA", "POZA RICA DE HIDALGO", "ORIZABA", "MINATITLÁN", "TUXPAN", "OTRO"
    ]
}

def generar_curp_algoritmica(paterno, materno, nombres, fecha_nac, sexo, est_nac, digitos_extra=""):
    p = limpiar_texto(paterno)
    m = limpiar_texto(materno) if materno else ""
    n = limpiar_texto(nombres)
    if not p or not n or not fecha_nac:
        return "FALTAN DATOS"
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

def generar_rfc_algoritmico(paterno, materno, nombres, fecha_nac):
    p = limpiar_texto(paterno)
    m = limpiar_texto(materno) if materno else ""
    n = limpiar_texto(nombres)
    if not p or not n or not fecha_nac:
        return "FALTAN DATOS"
    nombres_lista = n.split()
    primer_nombre = nombres_lista[0] if nombres_lista else "X"
    if len(nombres_lista) > 1 and primer_nombre in ["JOSE", "MARIA", "MA.", "J."]:
        primer_nombre = nombres_lista[1]
    c1 = p[0] if p else "X"
    c2 = obtener_primera_vocal_interna(p)
    if m:
        c3 = m[0]
    elif len(p) > 1:
        c3 = p[1]
    else:
        c3 = "X"
    c4 = primer_nombre[0] if primer_nombre else "X"
    yy = str(fecha_nac.year)[-2:]
    mm = str(fecha_nac.month).zfill(2)
    dd = str(fecha_nac.day).zfill(2)
    return f"{c1}{c2}{c3}{c4}{yy}{mm}{dd}"

estados_mexico = list(estados_curp.keys())
estados_mexico.insert(0, "SELECCIONE UN ESTADO")

# --- MODAL DE COMPROBANTE CON CÓDIGO QR Y OPCIONES DE DESCARGA ---
@st.dialog("🎉 ¡REGISTRO EXITOSO - TICKET DIGITAL!")
def mostrar_modal_comprobante_20n():
    p = st.session_state.ultimo_paciente_20n
    if p:
        curp_mostrar = p.get("curp", "CURP")
        nombre_val = p["nombre_completo"]
        folio_val = p["folio"]
        vacuna_val = p.get("vacuna_interes", "AMBAS")
        rfc_val = p.get("rfc", "RFC")
        fecha_val = datetime.date.today().strftime("%d/%m/%Y")

        texto_qr = (
            f"CMN 20 DE NOVIEMBRE - REGISTRO NOMINAL\n"
            f"FOLIO: {folio_val}\n"
            f"PACIENTE: {nombre_val}\n"
            f"CURP: {curp_mostrar}\n"
            f"RFC: {rfc_val}\n"
            f"VACUNA: {vacuna_val}\n"
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
            .qr-container {{ text-align: center; }}
            .qr-container canvas {{ width: 95px !important; height: 95px !important; border: 2px solid #a57f2c; border-radius: 6px; padding: 3px; background: white; display: block; }}
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
                        <span>CMN 20 DE NOVIEMBRE</span><span>CMN 20 DE NOVIEMBRE</span>
                    </div>
                    <div class="watermark-row">
                        <span>REGISTRO NOMINAL DE VACUNACIÓN</span><span>REGISTRO NOMINAL</span>
                    </div>
                    <div class="watermark-row">
                        <span>CMN 20 DE NOVIEMBRE</span><span>CMN 20 DE NOVIEMBRE</span>
                    </div>
                    <div class="watermark-row">
                        <span>REGISTRO NOMINAL DE VACUNACIÓN</span><span>REGISTRO NOMINAL</span>
                    </div>
                </div>
                <div class="titulo-ticket">CMN 20 DE NOVIEMBRE - REGISTRO EXITOSO</div>
                <div class="cuerpo-ticket">
                    <div class="info-container">
                        <p class="info-text"><b>Paciente:</b> {nombre_val}</p>
                        <p class="info-text"><b>CURP:</b> {curp_mostrar}</p>
                        <p class="info-text"><b>RFC:</b> {rfc_val}</p>
                        <p class="info-text"><b>Vacuna:</b> {vacuna_val}</p>
                    </div>
                    <div class="qr-container">
                        <canvas id="qr-canvas"></canvas>
                    </div>
                </div>
                <div class="folio-grande">Folio Asignado: {folio_val}</div>
                <p class="leyenda-posterior">Guarde este comprobante para su presentación en el módulo de vacunación.</p>
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
                        size: 150
                    }});
                }});

                function compartirImagenWhatsApp() {{
                    const elemento = document.getElementById('comprobante-captura');
                    html2canvas(elemento, {{ scale: 2, useCORS: true }}).then(canvas => {{
                        canvas.toBlob(blob => {{
                            const fileName = 'Folio_{folio_val}.png';
                            const textoMensaje = `💉 *REGISTRO CMN 20 DE NOVIEMBRE*\\nPaciente: {nombre_val}\\nFolio: *{folio_val}*\\nCURP: {curp_mostrar}\\nVacuna: {vacuna_val}\\nGuarde este comprobante para su validación.`;
                            
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
        if st.button("➕ Nuevo Registro (Reiniciar Formulario)", use_container_width=True):
            st.session_state.ultimo_paciente_20n = None
            st.session_state.form_version += 1
            st.rerun()
