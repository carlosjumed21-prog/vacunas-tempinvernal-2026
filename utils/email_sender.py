import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st
import urllib.parse

def enviar_comprobante_correo(destinatario_email, nombre_paciente, folio, dosis_str, lotes_str, fecha_val, tipo="folio"):
    """
    Envía por correo el Folio de Registro (para formulario) o el Comprobante Oficial (para consulta),
    respetando el asunto y el diseño visual de cada interfaz.
    """
    try:
        smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(st.secrets.get("SMTP_PORT", 465))
        remitente_email = st.secrets["SMTP_USER"]
        remitente_password = st.secrets["SMTP_PASSWORD"]
    except KeyError as e:
        return False, f"Falta configurar la credencial de correo en los secretos: {e}"
    
    msg = MIMEMultipart('alternative')
    msg['From'] = remitente_email
    msg['To'] = destinatario_email
    
    # Asuntos diferenciados según la interfaz de origen
    if tipo == "comprobante":
        msg['Subject'] = "COMPROBANTE DE VACUNACIÓN - GRACIAS POR CUIDAR DE SU SALUD"
        titulo_tarjeta = "COMPROBANTE DE VACUNACIÓN OFICIAL"
        texto_marca_agua = "COMPROBANTE OFICIAL VIGILE"
        texto_qr_header = "ISSSTE - COMPROBANTE OFICIAL VIGILE"
        leyenda_inferior = ""
        color_marca = "rgba(30, 91, 79, 0.08)"
    else:
        msg['Subject'] = "FOLIO DE REGISTRO - NO ES UN COMPROBANTE"
        titulo_tarjeta = "FOLIO DE VACUNACION REGISTRADO"
        texto_marca_agua = "NO ES UN COMPROBANTE OFICIAL"
        texto_qr_header = "ISSSTE - REGISTRO DE FOLIO VIGILE"
        leyenda_inferior = "Posterior a la asistencia de la aplicación de la vacuna se le entregará un comprobante oficial."
        color_marca = "rgba(97, 18, 50, 0.10)"

    texto_qr = (
        f"{texto_qr_header}\n"
        f"FOLIO: {folio}\n"
        f"PACIENTE: {nombre_paciente}\n"
        f"DOSIS/VACUNA: {dosis_str}\n"
        f"LOTES/GRUPO: {lotes_str}\n"
        f"FECHA APLICACIÓN: {fecha_val}\n"
        f"ESTADO: REGISTRADO"
    )
    url_qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=130x130&data={urllib.parse.quote(texto_qr)}"

    html_cuerpo = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: sans-serif; background-color: #f4f4f4; padding: 20px; }}
        .card-comprobante {{ 
            position: relative; background-color: #ffffff; border: 3px solid #1e5b4f; 
            padding: 16px; border-radius: 10px; color: #161a1d; max-width: 480px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin: 0 auto; overflow: hidden;
        }}
        .watermark-overlay {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            display: flex; flex-direction: column; justify-content: space-evenly; align-items: center;
            pointer-events: none; z-index: 1; overflow: hidden;
        }}
        .watermark-row {{
            display: flex; gap: 15px; white-space: nowrap; font-size: 0.75rem; font-weight: 900;
            color: {color_marca}; text-transform: uppercase; letter-spacing: 1px; transform: rotate(-25deg);
        }}
        .titulo-ticket {{ font-size: 0.95rem; font-weight: 900; color: #1e5b4f; text-align: center; margin: 0 0 10px 0; z-index: 2; position: relative; }}
        .cuerpo-ticket {{ display: flex; align-items: center; justify-content: space-between; gap: 15px; z-index: 2; position: relative; }}
        .info-container {{ flex: 1; z-index: 2; position: relative; }}
        .qr-container img {{ width: 110px; height: 110px; border: 2px solid #a57f2c; border-radius: 6px; padding: 3px; background: white; }}
        .folio-grande {{ font-size: 1.15rem; font-weight: 900; color: #611232; text-align: center; background-color: #f7f4eb; padding: 8px; border-radius: 6px; border: 2px dashed #a57f2c; margin-top: 12px; z-index: 2; position: relative; }}
        .info-text {{ margin: 4px 0; font-size: 0.82rem; }}
        .leyenda-posterior {{ font-size: 0.72rem; font-weight: 700; color: #611232; text-align: center; margin-top: 8px; z-index: 2; position: relative; }}
    </style>
    </head>
    <body>
        <div class="card-comprobante">
            <div class="watermark-overlay">
                <div class="watermark-row"><span>{texto_marca_agua}</span><span>{texto_marca_agua}</span></div>
                <div class="watermark-row"><span>{texto_marca_agua}</span><span>{texto_marca_agua}</span></div>
                <div class="watermark-row"><span>{texto_marca_agua}</span><span>{texto_marca_agua}</span></div>
            </div>
            <div class="titulo-ticket">{titulo_tarjeta}</div>
            <div class="cuerpo-ticket">
                <div class="info-container">
                    <p class="info-text"><b>Paciente:</b> {nombre_paciente}</p>
                    <p class="info-text"><b>Dosis/Vacuna:</b> {dosis_str}</p>
                    <p class="info-text"><b>Lotes/Grupo:</b> {lotes_str}</p>
                    <p class="info-text"><b>Fecha Aplicación:</b> {fecha_val}</p>
                </div>
                <div class="qr-container">
                    <img src="{url_qr_api}" alt="QR Verificación">
                </div>
            </div>
            <div class="folio-grande">Folio: {folio}</div>
            {"<div class='leyenda-posterior'>" + leyenda_inferior + "</div>" if leyenda_inferior else ""}
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_cuerpo, 'html'))
        
    try:
        servidor = smtplib.SMTP_SSL(smtp_server, smtp_port)
        servidor.login(remitente_email, remitente_password)
        servidor.sendmail(remitente_email, destinatario_email, msg.as_string())
        servidor.quit()
        return True, "¡Correo enviado exitosamente!"
    except Exception as e:
        return False, f"Error al conectar con el servidor de correo: {e}"
