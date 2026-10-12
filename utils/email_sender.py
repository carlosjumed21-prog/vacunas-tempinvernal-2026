import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import streamlit as st
import io
from PIL import Image, ImageDraw, ImageFont

def generar_imagen_comprobante(nombre_paciente, folio, dosis_str, lotes_str, fecha_val):
    """Genera una imagen PNG limpia del comprobante usando Pillow para adjuntarla al correo."""
    # Crear una imagen en blanco de 600x400 (formato tarjeta)
    img = Image.new('RGB', (600, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Dibujar bordes institucionales (Verde ISSSTE)
    d.rectangle([(10, 10), (590, 390)], outline=(30, 91, 79), width=4)
    
    # Textos del comprobante
    d.rectangle([(14, 14), (586, 70)], fill=(30, 91, 79))
    d.text((30, 28), "COMPROBANTE OFICIAL DE VACUNACIÓN", fill=(255, 255, 255))
    
    # Datos del paciente
    d.text((30, 90), f"Paciente: {nombre_paciente}", fill=(22, 26, 29))
    d.text((30, 130), f"Folio de Registro: {folio}", fill=(97, 18, 50))
    d.text((30, 170), f"Dosis Aplicada: {dosis_str}", fill=(22, 26, 29))
    d.text((30, 210), f"Lotes: {lotes_str}", fill=(22, 26, 29))
    d.text((30, 250), f"Fecha de Aplicación: {fecha_val}", fill=(22, 26, 29))
    
    # Pie de página
    d.rectangle([(14, 330), (586, 386)], fill=(247, 244, 235))
    d.text((30, 345), "Jornadas de Vacunación Zona Sur - ISSSTE\nEstado: Válido y Verificado", fill=(30, 91, 79))
    
    # Guardar en memoria como bytes de imagen PNG
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()

def enviar_comprobante_correo(destinatario_email, nombre_paciente, folio, dosis_str, lotes_str, fecha_val):
    """
    Envía el comprobante de vacunación por correo adjuntando automáticamente la imagen generada.
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
    
    Adjunto encontrará la imagen oficial de su comprobante correspondiente a la jornada de vacunación.
    
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
    
    # Generar y adjuntar la imagen automáticamente
    try:
        img_bytes = generar_imagen_comprobante(nombre_paciente, folio, dosis_str, lotes_str, fecha_val)
        parte = MIMEBase('image', 'png')
        parte.set_payload(img_bytes)
        encoders.encode_base64(parte)
        parte.add_header('Content-Disposition', f'attachment; filename="Comprobante_{folio}.png"')
        msg.attach(parte)
    except Exception as img_err:
        print(f"No se pudo adjuntar la imagen: {img_err}")
        
    try:
        servidor = smtplib.SMTP_SSL(smtp_server, smtp_port)
        servidor.login(remitente_email, remitente_password)
        servidor.sendmail(remitente_email, destinatario_email, msg.as_string())
        servidor.quit()
        return True, "¡Correo y comprobante en imagen enviados exitosamente!"
    except Exception as e:
        return False, f"Error al conectar con el servidor de correo: {e}"
