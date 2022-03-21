"""
MongoDB connection
"""
import os
import mongoengine
from mongoengine.connection import _get_db
from fintrist2 import Config

def connect_db():
    mongoengine.disconnect()
    db_name = os.environ.get('ALT_DB') or Config.DATABASE_NAME
    mongoclient = mongoengine.connect(
        db_name,
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        username=Config.USERNAME,
        password=Config.PASSWORD,
        authentication_source='admin',
    )
    return mongoclient, mongoclient[db_name]

def test_db(test=True):
    """Toggle the test DB."""
    if test:
        os.environ['ALT_DB'] = Config.TESTNAME
    else:
        os.environ.pop('ALT_DB', None)
    mongoclient = connect_db()
    print(f"Test DB: {test}")
    return mongoclient

def drop_test():
    """Drop the test DB."""
    mongoclient = _get_db().client
    mongoclient.drop_database(Config.TESTNAME)
    print(f"{TESTNAME} dropped.")
