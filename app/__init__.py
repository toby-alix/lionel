from flask            import Flask

app = Flask(__name__)

from app.src import schedule_updates