import redis
from collectors.base_collector import BaseCollector
from parsers.nginx_parser import NginxParser


class NginxCollector(BaseCollector):
    def __init__(self, redis_client: redis.Redis, log_path: str = "/host/var/log/nginx/access.log"):
        super().__init__(log_path, redis_client, NginxParser())

    def get_source(self) -> str:
        return "nginx"
