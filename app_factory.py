# app_factory.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv
import os

from models import db, User

load_dotenv()

login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    env = os.getenv("FLASK_ENV", "development")
    if env == "production":
        app.config.from_object("config.ProdConfig")
    else:
        app.config.from_object("config.DevConfig")
        
    from models import db  # adjust import if needed
    with app.app_context():
        db.create_all()

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"
    mail.init_app(app)

    from flask_app import setup_routes
    setup_routes(app, db, login_manager, mail)

    return app
