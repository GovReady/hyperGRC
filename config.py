import os

class Config(object):
  SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
  GOVREADY_FILE = os.environ.get('GOVREADY_FILE') or '../.govready'