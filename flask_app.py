from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from markupsafe import Markup
from email_utils import render_template_text, send_email,extract_docx_with_images
from datetime import datetime
import pandas as pd
import os, csv, re
from dotenv import load_dotenv
from models import db, User
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Session
from flask import send_file
from flask_mail import Mail, Message
from flask import url_for
import uuid
from email_utils import render_template_text, send_email, extract_text_from_docx, extract_text_from_pdf, html_to_plain_text


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")

app = Flask(__name__)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy()

if os.environ.get("FLASK_ENV") == "production":
    app.config.from_object("production_config")
else:
    # local dev
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"

db.init_app(app)

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv('MAIL_USERNAME'),  # your email for sending verification
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),  # app password or real password
)

mail = Mail(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    with db.session() as session:
        return session.get(User, int(user_id))

# Progress tracking
progress_data = {"total": 0, "sent": 0}

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("Dashboard"))
    return render_template("index.html")  # your landing page

@app.route("/UploadDetails")
@login_required
def Dashboard():
    return render_template("upload_form.html")  # show upload form after login

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        smtp_user = request.form["smtp_user"]
        smtp_pass = request.form["smtp_pass"]

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("signup"))

        user = User(
            name=name,
            email=email,
            smtp_user=smtp_user,
            smtp_pass=smtp_pass,
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            emails_sent=0,
            campaigns_created=0,
            account_status="Active"
        )
        user.set_password(password)

        # Generate email verification token
        user.verification_token = str(uuid.uuid4())
        user.is_verified = False

        db.session.add(user)
        db.session.commit()

        # Send verification email
        verification_url = url_for('verify_email', token=user.verification_token, _external=True)
        msg = Message(
            subject="Please Verify Your Email",
            sender=app.config['MAIL_USERNAME'],
            recipients=[user.email],
            body=f"Hi {user.name},\n\nPlease verify your email by clicking the link below:\n{verification_url}\n\nThank you!"
        )
        mail.send(msg)

        flash("Signup successful! Please check your email to verify your account.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route('/verify/<token>')
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if user:
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        flash("Email verified! You can now log in.", "success")
        return redirect(url_for('login'))
    else:
        flash("Invalid or expired verification link.", "danger")
        return redirect(url_for('signup'))


@app.route("/app-password-guide")
def app_password_guide():
    return render_template("app_password_guide.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.is_verified:
                flash("Please verify your email before logging in.", "warning")
                return redirect(url_for("login"))
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logout successful!", "danger")
    return redirect(url_for("login"))

@app.route("/send_emails", methods=["POST"])
@login_required
def send_emails():
    global progress_data
    file = request.files["excel"]
    template_file = request.files["template"]
    # template_text = template_file.read().decode("utf-8")
    filename = template_file.filename
    ext = filename.split('.')[-1].lower()

    if ext in ["txt", "html"]:
        template_text = template_file.read().decode("utf-8")
    elif ext == "docx":
        template_text = extract_docx_with_images(template_file)
        # template_text = extract_text_from_docx(template_file)
    elif ext == "pdf":
        template_text = extract_text_from_pdf(template_file)
    else:
        flash("Unsupported file format. Use .txt, .html, .docx, or .pdf", "danger")
        return redirect(url_for("dashboard"))

    df = pd.read_excel(file)
    progress_data["total"] = len(df)
    progress_data["sent"] = 0

    subject = "Personalized Message"
    log_file_path = "email_log.csv"

    def normalize_key(key):
        return re.sub(r'\W+', '_', str(key).strip().lower())

    emails_sent_count = 0  # ✅ Initialize safely at the top

    with open(log_file_path, mode="w", newline="", encoding="utf-8") as log_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(["Company Name", "Email", "Status", "Timestamp", "Error"])

        for _, row in df.iterrows():
            raw_data = row.to_dict()
            row_data = {normalize_key(k): str(v).strip() for k, v in raw_data.items()}

            email = row_data.get("email", "")
            company_name = row_data.get("company_name", "Unknown")

            try:
                # body = render_template_text(template_text, row_data)
                # send_email(email, subject, body)
                rendered_html = render_template_text(template_text, row_data)
                send_email(email, subject, rendered_html)
                log_writer.writerow([company_name, email, "Success", datetime.now(), ""])
                emails_sent_count += 1  # ✅ count only on success
            except Exception as e:
                log_writer.writerow([company_name, email, "Failed", datetime.now(), str(e)])
            progress_data["sent"] += 1

    # ✅ Safely update DB now
    user = User.query.get(current_user.id)
    user.emails_sent += emails_sent_count
    user.campaigns_created += 1
    db.session.commit()

    return jsonify({
        "message": "Emails processed. See 'email_log.csv' for results."
    })


@app.route("/preview_email", methods=["POST"])
@login_required
def preview_email():
    file = request.files["excel"]
    template_file = request.files["template"]
    # template_text = template_file.read().decode("utf-8")
    filename = template_file.filename
    ext = filename.split('.')[-1].lower()

    if ext in ["txt", "html"]:
        template_text = template_file.read().decode("utf-8")
    elif ext == "docx":
        template_text = extract_text_from_docx(template_file)
    elif ext == "pdf":
        template_text = extract_text_from_pdf(template_file)
    else:
        flash("Unsupported file format. Use .txt, .html, .docx, or .pdf", "danger")
        return redirect(url_for("dashboard"))
    
    show_all = request.form.get("show_all") == "on"

    def normalize_key(key):
        return re.sub(r'\W+', '_', str(key).strip().lower())

    df = pd.read_excel(file)
    if df.empty:
        return "Excel file is empty."

    previews = []
    for _, row in df.iterrows():
        raw_data = row.to_dict()
        row_data = {normalize_key(k): str(v).strip() for k, v in raw_data.items()}
        rendered_html = render_template_text(template_text, row_data)
        previews.append(rendered_html)

    limited_previews = previews if show_all else previews[:20]

    return render_template(
        "preview_result.html",
        email_previews=limited_previews,
        total=len(previews),
        showing_all=show_all
    )

@app.route("/progress")
@login_required
def get_progress():
    return jsonify(progress_data)

@app.route("/download_log")
@login_required
def download_log():
    log_file_path = "email_log.csv"
    if not os.path.exists(log_file_path):
        flash("Log file not found. Please send some emails first.", "warning")
        return redirect(url_for("index"))

    return send_file(
        log_file_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name="email_log.csv"
    )

@app.route("/how-to-use")
@login_required
def how_to_use():
    return render_template("how_to_use.html")

if __name__ == "__main__":
    app.run()
