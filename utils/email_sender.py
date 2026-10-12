import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st
import urllib.parse

def enviar_comprobante_correo(destinatario_email, nombre_paciente, folio, dosis_str, lotes_str, fecha_val):
    """
    Envía el comprobante de vacunación por correo con un diseño HTML idéntico a la tarjeta de la interfaz.
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
    msg['Subject'] = f"Comprobante Oficial de Vacunación - Folio: {folio}"
    
    # Texto QR idéntico al de la interfaz
    texto_qr = (
        f"ISSSTE - COMPROBANTE OFICIAL VIGILE\n"
        f"FOLIO: {folio}\n"
        f"PACIENTE: {nombre_paciente}\n"
        f"DOSIS: {dosis_str}\n"
        f"LOTES: {lotes_str}\n"
        f"FECHA APLICACIÓN: {fecha_val}\n"
        f"ESTADO: VÁLIDO Y VERIFICADO"
    )
    url_qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=120x120&data={urllib.parse.quote(texto_qr)}"

    # HTML idéntico al diseño de la tarjeta web
    html_cuerpo = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: sans-serif; background-color: #f4f4f4; padding: 20px; }}
        .card-comprobante {{ 
            position: relative; background-color: #ffffff; border: 3px solid #1e5b4f; 
            padding: 16px; border-radius: 10px; color: #161a1d; max-width: 450px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin: 0 auto; 
        }}
        .titulo-ticket {{ font-size: 0.95rem; font-weight: 900; color: #1e5b4f; text-align: center; margin-top: 0; margin-bottom: 10px; }}
        .cuerpo-ticket {{ display: flex; align-items: center; justify-content: space-between; gap: 15px; }}
        .info-container {{ flex: 1; }}
        .qr-container img {{ width: 100px; height: 100px; border: 2px solid #a57f2c; border-radius: 6px; padding: 3px; background: white; }}
        .folio-grande {{ font-size: 1.1rem; font-weight: 900; color: #611232; text-align: center; background-color: #f7f4eb; padding: 8px; border-radius: 6px; border: 2px dashed #a57f2c; margin-top: 12px; }}
        .info-text {{ margin: 5px 0; font-size: 0.85rem; }}
        .footer-msg {{ text-align: center; font-size: 0.75rem; color: #555; margin-top: 15px; }}
    </style>
    </head>
    <body>
        <div class="card-comprobante">
            <div class="titulo-ticket">COMPROBANTE DE VACUNACIÓN OFICIAL - ISSSTE</div>
            <div class="cuerpo-ticket">
                <div class="info-container">
                    <p class="info-text"><b>Paciente:</b> {nombre_paciente}</p>
                    <p class="info-text"><b>Dosis:</b> {dosis_str}</p>
                    <p class="info-text"><b>Lotes:</b> {lotes_str}</p>
                    <p class="info-text"><b>Fecha de Aplicación:</b> {fecha_val}</p>
                </div>
                <div class="qr-container">
                    <img src="{url_qr_api}" alt="QR Verificación">
                </div>
            </div>
            <div class="folio-grande">Folio: {folio}</div>
            <div class="footer-msg">Jornadas de Vacunación Zona Sur • Estado: Válido y Verificado</div>
        </div>
    </body>
    </html>
    """
    
    # Adjuntar versión HTML para que el cliente de correo muestre la tarjeta idéntica
    msg.attach(MIMEText(html_cuerpo, 'html'))
        
    try:
        servidor = smtplib.SMTP_SSL(smtp_server, smtp_port)
        servidor.login(remitente_email, remitente_password)
        servidor.sendmail(remitente_email, destinatario_email, msg.as_string())
        servidor.quit()
        return True, "¡Comprobante visual enviado exitosamente por correo!"
    except Exception as e:
        return False, f"Error al conectar con el servidor de correo: {e}"
