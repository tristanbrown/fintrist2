"""
This is the config file for fintrist, containing various parameters the user may
wish to modify.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class ConfigObj():
    APP_HOST = os.getenv('COMPUTERNAME')
    DATABASE_NAME = 'Fintrist2_DB'
    TESTNAME = 'Fintrist2_Test'
    local = int(os.getenv('DB_LOCAL') or 0)
    if local:
        USERNAME = None
        PASSWORD = None
        DB_HOST = 'localhost'
    else:
        USERNAME = os.getenv('DB_USERNAME')
        PASSWORD = os.getenv('DB_PASSWORD')
        DB_HOST = os.getenv('DB_HOST')
    DB_PORT = int(os.getenv('DB_PORT') or 27017)
    APIKEY_AV = os.getenv('APIKEY_AV')
    APIKEY_TIINGO = os.getenv('APIKEY_TIINGO')
    TZ = os.getenv('TIMEZONE') or 'UTC'

Config = ConfigObj()
