import redis
from collectors.base_collector import BaseCollector
from parsers.ssh_parser import SSHParser


class SSHCollector(BaseCollector):
    def __init__(self, redis_client: redis.Redis, log_path: str = "/host/var/log/auth.log"):
        super().__init__(log_path, redis_client, SSHParser())

    def get_source(self) -> str:
        return "ssh"
