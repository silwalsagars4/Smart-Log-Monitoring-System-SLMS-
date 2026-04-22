import redis
from collectors.base_collector import BaseCollector
from parsers.mysql_parser import MySQLParser


class MySQLCollector(BaseCollector):
    def __init__(self, redis_client: redis.Redis, log_path: str = "/host/var/log/mysql/error.log"):
        super().__init__(log_path, redis_client, MySQLParser())

    def get_source(self) -> str:
        return "mysql"
