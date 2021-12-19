from flask import Flask
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from config import Config

app = Flask(__name__)
db = MySQL(app)
bcrypt = Bcrypt(app)
app.config.from_object(Config)

from app import routes