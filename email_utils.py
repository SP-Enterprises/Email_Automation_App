import mammoth
import pandas as pd
from jinja2 import Template
from email.mime.text import MIMEText
import smtplib
import os
from dotenv import load_dotenv
from flask_login import current_user
import fitz  # PyMuPDF
import docx
import html2text
import re
from docx import Document
import base64
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from docx import Document
from bs4 import BeautifulSoup

load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

def load_contacts(file_path):
    return pd.read_excel(file_path)

def load_template(template_path):
    with open(template_path, 'r', encoding='utf-8') as file:
        return Template(file.read())
    
def html_to_plain_text(html):
    return html2text.html2text(html)

def extract_docx_with_images(file_storage):
    docx_data = file_storage.read()
    file_stream = io.BytesIO(docx_data)
    document = Document(file_stream)

    html_parts = []

    rels = document.part._rels
    image_map = {}

    # Map image relationships to base64
    for rel in rels:
        rel_obj = rels[rel]
        if "image" in rel_obj.target_ref:
            image_part = rel_obj.target_part
            image_bytes = image_part.blob
            ext = rel_obj.target_ref.split('.')[-1]
            image_base64 = base64.b64encode(image_bytes).decode()
            cid = rel_obj.rId
            image_map[cid] = f'data:image/{ext};base64,{image_base64}'

    for para in document.paragraphs:
        text = para.text.strip()
        if text:
            html_parts.append(f"<p>{text}</p>")

    #add images at appropriate positions (crude solution, or refine with python-docx-html later)
    for cid, img_src in image_map.items():
        html_parts.append(f'<img src="{img_src}" alt="Image" style="max-width: 100%; margin-top: 10px;" />')

    return "\n".join(html_parts)

# ✅ Needed for render_template_text(template_str, {"company_name": name})
def render_template_text(template_str, context):
    template = Template(template_str)
    return template.render(context)

def extract_text_from_docx(file_storage):
      result = mammoth.convert_to_html(file_storage)
      html = result.value

    # Remove inline styles related to color
      html = re.sub(r'style="[^"]*color:[^"]*"', '', html)

      return html
   
# NEW: For PDF → HTML (simplified plain-text fallback)
def extract_text_from_pdf(file_storage):
    pdf_data = file_storage.read()
    text = ""
    with fitz.open(stream=pdf_data, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    # Convert line breaks to basic HTML formatting
    html = "<br>".join(text.splitlines())
    return html

def send_email(to_email, subject, body):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    import base64
    import re

    msg = MIMEMultipart('related')
    msg['From'] = current_user.smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject

    image_parts = []
    image_matches = list(re.finditer(r'data:image/[^;]+;base64,([^"]+)', body))
    
    for idx, match in enumerate(image_matches):
        image_data = base64.b64decode(match.group(1))
        cid = f"image{idx}"
        # Replace base64 src with CID in HTML
        body = body.replace(match.group(0), f"cid:{cid}")
        # Prepare image part
        image_part = MIMEImage(image_data)
        image_part.add_header('Content-ID', f'<{cid}>')
        image_parts.append(image_part)

    # Attach HTML body
    msg.attach(MIMEText(body, 'html'))

    # Attach all images
    for part in image_parts:
        msg.attach(part)

    with smtplib.SMTP(current_user.smtp_server, current_user.smtp_port) as server:
        server.starttls()
        server.login(current_user.smtp_user, current_user.smtp_pass)
        server.send_message(msg)
