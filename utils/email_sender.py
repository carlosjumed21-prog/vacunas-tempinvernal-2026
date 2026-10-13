import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import urllib.parse
import streamlit as st

def enviar_correo_ticket(destinatario_email, nombre_paciente, folio, dosis_str, lotes_str, fecha_val, tipo="folio"):
    try:
        smtp_server = st.secrets["SMTP_SERVER"]
        smtp_port = int(st.secrets["SMTP_PORT"])
        remitente_email = st.secrets["SMTP_USER"]
        remitente_password = st.secrets["SMTP_PASSWORD"]
    except Exception as e:
        return False, f"Falta configuración SMTP en secrets: {e}"

    if not destinatario_email or "@" not in destinatario_email:
        return False, "Correo inválido"

    if tipo == "comprobante":
        subject = "COMPROBANTE DE VACUNACIÓN OFICIAL - VIGILE"
        titulo = "COMPROBANTE DE VACUNACIÓN OFICIAL"
        texto_qr = (
            "ISSSTE - COMPROBANTE OFICIAL VIGILE\n"
            f"FOLIO: {folio}\n"
            f"PACIENTE: {nombre_paciente}\n"
            f"VACUNA: {dosis_str}\n"
            f"GRUPO/LOTES: {lotes_str}\n"
            f"FECHA APLICACIÓN: {fecha_val}\n"
            "ESTADO: REGISTRADO"
        )
    else:
        subject = "TICKET DIGITAL DE REGISTRO - VIGILE"
        titulo = "FOLIO DE VACUNACION REGISTRADO"
        texto_qr = (
            "ISSSTE - REGISTRO DE FOLIO VIGILE\n"
            f"FOLIO: {folio}\n"
            f"PACIENTE: {nombre_paciente}\n"
            f"VACUNA: {dosis_str}\n"
            f"GRUPO/LOTES: {lotes_str}\n"
            f"FECHA APLICACIÓN: {fecha_val}\n"
            "ESTADO: REGISTRADO"
        )

    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(texto_qr)}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background:#f7f9f8; padding:20px;">
      <div style="max-width:460px; margin:0 auto; background:#fff; border:3px solid #1e5b4f; border-radius:10px; padding:20px;">
        <h2 style="text-align:center; color:#1e5b4f;">{titulo}</h2>
        <p><b>Paciente:</b> {nombre_paciente}</p>
        <p><b>Vacuna:</b> {dosis_str}</p>
        <p><b>Grupo/Lotes:</b> {lotes_str}</p>
        <p><b>Fecha:</b> {fecha_val}</p>

        <div style="text-align:center;">
          <img src="{qr_url}" alt="QR" width="110">
        </div>

        <div style="background:#f7f4eb; padding:8px; text-align:center; font-weight:bold; color:#611232; margin-top:10px;">
          Folio: {folio}
        </div>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = remitente_email
    msg["To"] = destinatario_email.strip()
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    try:
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port, context=ssl.create_default_context(), timeout=20) as server:
                server.login(remitente_email, remitente_password)
                server.sendmail(remitente_email, destinatario_email.strip(), msg.as_string())
        else:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(remitente_email, remitente_password)
                server.sendmail(remitente_email, destinatario_email.strip(), msg.as_string())

        return True, "¡Correo enviado exitosamente!"
    except Exception as e:
        return False, f"Error SMTP: {e}"
