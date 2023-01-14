from pathlib import Path

from flask            import Flask
from flask_sqlalchemy import SQLAlchemy
import psycopg2

basedir = Path(__file__).parent

app = Flask(__name__)

from app.src import schedule_updates