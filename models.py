from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from sqlalchemy import Boolean
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    smtp_server = db.Column(db.String(100), default="smtp.gmail.com")
    smtp_port = db.Column(db.Integer, default=587)
    smtp_user = db.Column(db.String(100))  # Email used to send
    smtp_pass = db.Column(db.String(200))  # Encrypted password
    is_verified = db.Column(Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True, nullable=True)
    emails_sent = db.Column(db.Integer, default=0)
    campaigns_created = db.Column(db.Integer, default=0)
    account_status = db.Column(db.String(20), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def generate_verification_token(self):
        self.verification_token = str(uuid.uuid4())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


from cryptography.fernet import Fernet
import os

def encrypt_password(password):
    cipher = Fernet(os.getenv("FERNET_KEY").encode())
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password):
    cipher = Fernet(os.getenv("FERNET_KEY").encode())
    return cipher.decrypt(encrypted_password.encode()).decode()
