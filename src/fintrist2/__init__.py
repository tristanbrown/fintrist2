"""
Start Fintrist, connect to the DB, and expose public methods.
"""
from .connect import connect_db, test_db, drop_test
from .settings import Config

__all__ = ('connect_db', 'mongoclient', 'test_db')

mongoclient, db = connect_db()
