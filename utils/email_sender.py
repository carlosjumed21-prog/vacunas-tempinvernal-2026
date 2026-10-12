import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st

def enviar_comprobante_correo(destinatario_email, nombre_paciente, folio, dosis_str, lotes_str, fecha_val):
    """
    Envía el comprobante de vacunación por correo usando las credenciales SMTP de st.secrets.
    """
    try:
        smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(st.secrets.get("SMTP_PORT", 465))
        remitente_email = st.secrets["SMTP_USER"]
        remitente_password = st.secrets["SMTP_PASSWORD"]
    except KeyError as e:
        return False, f"Falta configurar la credencial de correo en los secretos: {e}"
    
    msg = MIMEMultipart()
    msg['From'] = remitente_email
    msg['To'] = destinatario_email
    msg['Subject'] = f"Comprobante Oficial de Vacunación - Folio: {folio}"
    
    cuerpo = f"""
    Estimado/a {nombre_paciente},
    
    Adjunto y registrado con éxito su comprobante de vacunación de la Jornada de Salud.
    
    DETALLES DEL REGISTRO:
    - Folio: {folio}
    - Dosis Aplicada: {dosis_str}
    - Lotes: {lotes_str}
    - Fecha de Aplicación: {fecha_val}
    
    Atentamente,
    Jornadas de Vacunación Zona Sur
    ISSSTE
    """
    msg.attach(MIMEText(cuerpo, 'plain'))
        
    try:
        # Usamos SMTP_SSL directo para el puerto 465 (más estable en la nube)
        servidor = smtplib.SMTP_SSL(smtp_server, smtp_port)
        servidor.login(remitente_email, remitente_password)
        servidor.sendmail(remitente_email, destinatario_email, msg.as_string())
        servidor.quit()
        return True, "¡Correo enviado exitosamente!"
    except Exception as e:
        return False, f"Error al conectar con el servidor de correo: {e}"
