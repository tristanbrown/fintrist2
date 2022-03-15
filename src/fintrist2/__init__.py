"""
Start Fintrist, connect to the DB, and expose public methods.
"""
from .connect import connect_db, test_db, drop_test
from .settings import Config
from .stockmarket import Stock

__all__ = ('connect_db', 'mongoclient', 'test_db', 'Stock')

mongoclient, db = connect_db()
