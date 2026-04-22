import redis
from collectors.base_collector import BaseCollector
from parsers.apache_parser import ApacheParser


class ApacheCollector(BaseCollector):
    def __init__(self, redis_client: redis.Redis, log_path: str = "/host/var/log/apache2/access.log"):
        super().__init__(log_path, redis_client, ApacheParser())

    def get_source(self) -> str:
        return "apache"
