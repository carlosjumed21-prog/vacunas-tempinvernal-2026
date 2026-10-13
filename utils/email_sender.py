import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
import streamlit as st
import urllib.parse
import traceback

def enviar_comprobante_correo(destinatario_email, nombre_paciente="PACIENTE", folio="S/F",
                             dosis_str="VACUNA", lotes_str="S/N", fecha_val="", tipo="folio",
                             debug=False):
    """
    Envía por correo el Ticket Digital o Comprobante Oficial con registro extendido de errores.
    Devuelve (bool, mensaje). En caso de error el segundo valor incluye detalle.
    """
    if not destinatario_email or "@" not in destinatario_email:
        return False, f"⚠️ Correo inválido: '{destinatario_email}'"

    nombre_paciente = str(nombre_paciente or "PACIENTE").upper()
    folio = str(folio or "S/F")
    dosis_str = str(dosis_str or "VACUNA")
    lotes_str = str(lotes_str or "S/N")
    fecha_val = str(fecha_val or "")

    try:
        smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(st.secrets.get("SMTP_PORT", 465))
        remitente_email = st.secrets["SMTP_USER"]
        remitente_password = st.secrets["SMTP_PASSWORD"]
    except KeyError as e:
        error_msg = f"⚠️ Falta configurar la credencial de correo en los secretos (KeyError: {e})."
        st.error(error_msg)
        return False, error_msg

    msg = MIMEMultipart('alternative')
    msg['From'] = formataddr(("Vigile", remitente_email))
    # Si hay múltiples destinatarios separados por coma, soportarlos:
    destinatarios = [d.strip() for d in destinatario_email.split(",") if d.strip()]
    msg['To'] = ", ".join(destinatarios)

    if tipo == "comprobante":
        msg['Subject'] = "COMPROBANTE DE VACUNACIÓN OFICIAL - VIGILE"
        titulo_tarjeta = "COMPROBANTE DE VACUNACIÓN OFICIAL"
        texto_qr_header = "ISSSTE - COMPROBANTE OFICIAL VIGILE"
        color_borde = "#1e5b4f"
    else:
        msg['Subject'] = "TICKET DIGITAL DE REGISTRO - VIGILE"
        titulo_tarjeta = "FOLIO DE VACUNACION REGISTRADO"
        texto_qr_header = "ISSSTE - REGISTRO DE FOLIO VIGILE"
        color_borde = "#1e5b4f"

    texto_qr = (
        f"{texto_qr_header}\n"
        f"FOLIO: {folio}\n"
        f"PACIENTE: {nombre_paciente}\n"
        f"VACUNA: {dosis_str}\n"
        f"GRUPO/LOTES: {lotes_str}\n"
        f"FECHA APLICACIÓN: {fecha_val}\n"
        f"ESTADO: REGISTRADO"
    )
    url_qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(texto_qr)}"

    html_cuerpo = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: sans-serif; background-color: #f7f9f8; padding: 20px;">
        <div style="background-color: #ffffff; border: 3px solid {color_borde}; padding: 20px; border-radius: 10px; max-width: 460px; margin: 0 auto;">
            <h2 style="color: #1e5b4f; text-align: center;">{titulo_tarjeta}</h2>
            <p><b>Paciente:</b> {nombre_paciente}</p>
            <p><b>Vacuna:</b> {dosis_str}</p>
            <p><b>Grupo/Lotes:</b> {lotes_str}</p>
            <p><b>Fecha:</b> {fecha_val}</p>
            <div style="text-align: center;"><img src="{url_qr_api}" alt="QR" width="110"></div>
            <div style="background-color: #f7f4eb; padding: 8px; text-align: center; font-weight: bold; color: #611232; margin-top: 10px;">Folio: {folio}</div>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_cuerpo, 'html'))

    context = ssl.create_default_context()

    try:
        if debug:
            print(f"DEBUG: Intentando conectar a {smtp_server}:{smtp_port} con usuario {remitente_email}...")
        # Manejo explícito para 465 (SSL) y 587 (STARTTLS). Otros puertos intentan SSL por defecto.
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context, timeout=15) as servidor:
                servidor.login(remitente_email, remitente_password)
                servidor.sendmail(remitente_email, destinatarios, msg.as_string())
        else:
            # Usa STARTTLS (puerto típico 587). Ehlo/starttls/ehlo pattern.
            with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as servidor:
                servidor.ehlo()
                try:
                    servidor.starttls(context=context)
                    servidor.ehlo()
                except Exception as tls_err:
                    # Si starttls falla, capturarlo y devolver detalle.
                    raise RuntimeError(f"Fallo STARTTLS: {tls_err}")
                servidor.login(remitente_email, remitente_password)
                servidor.sendmail(remitente_email, destinatarios, msg.as_string())

        if debug:
            print("DEBUG: ¡Correo enviado con éxito!")
        return True, "¡Correo enviado exitosamente!"
    except smtplib.SMTPAuthenticationError as auth_err:
        detalle = traceback.format_exc()
        st.error("❌ Error de autenticación SMTP. Verifica usuario/contraseña (usa App Password si corresponde).")
        return False, f"SMTPAuthenticationError: {auth_err}\n{detalle}"
    except Exception as e:
        detalle_error = traceback.format_exc()
        if debug:
            print(f"ERROR CRÍTICO SMTP:\n{detalle_error}")
        st.error(f"❌ Error detallado al enviar correo: {str(e)}")
        return False, f"Error SMTP: {str(e)}\n{detalle_error}"
