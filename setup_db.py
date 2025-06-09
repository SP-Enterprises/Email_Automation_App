# setup_db.py

from flask import Flask
from models import db
import os

# Create your Flask app instance
app = Flask(__name__)

# Load environment variables (if using .env for DB config)
from dotenv import load_dotenv
load_dotenv()

# Set up the database URI (update this if you're using a different DB)
# app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQLALCHEMY_DATABASE_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize app with SQLAlchemy
db.init_app(app)

# Create all tables
with app.app_context():
    db.create_all()
    print("✅ Database tables created successfully.")
