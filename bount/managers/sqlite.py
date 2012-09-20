import logging
from bount.managers import DatabaseManager

__author__ = 'mturilin'

logger = logging.getLogger(__file__)


class SqliteManager(DatabaseManager):
    def __init__(self, dbfile):
        self.dbfile = dbfile
