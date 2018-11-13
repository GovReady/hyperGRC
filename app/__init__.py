from flask import Flask
from config import Config

import rtyaml

app = Flask(__name__)
app.config.from_object(Config)

from app import routes

GOVREADY_FILE = app.config['GOVREADY_FILE']
print("   .govready file: {}".format(GOVREADY_FILE))