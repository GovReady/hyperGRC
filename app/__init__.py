from flask import Flask
from config import Config

import rtyaml

app = Flask(__name__)
app.config.from_object(Config)

# Banish flask's 50 page jinja cache template limit to speed performance
# app.jinja_env.cache = {}

from app import routes

