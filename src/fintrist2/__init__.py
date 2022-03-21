"""
Start Fintrist, connect to the DB, and expose public methods.
"""
from .settings import Config
from .db.connect import connect_db, test_db, drop_test
from .stockmarket.prices import Stock

__all__ = ('Config', 'mongoclient', 'test_db', 'drop_test', 'Stock')

mongoclient, db = connect_db()
