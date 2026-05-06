"""
Generic collector — dynamically instantiated for log paths added via the
Dynamic Log Config API. Selects the right parser based on collector_type.
"""

import redis
from collectors.base_collector import BaseCollector
from parsers.ssh_parser import SSHParser
from parsers.nginx_parser import NginxParser
from parsers.apache_parser import ApacheParser
from parsers.mysql_parser import MySQLParser
from parsers.docker_parser import DockerParser
from parsers.generic_parser import GenericParser

PARSER_MAP = {
    "ssh":     SSHParser,
    "auth":    SSHParser,
    "nginx":   NginxParser,
    "apache":  ApacheParser,
    "mysql":   MySQLParser,
    "docker":  DockerParser,
    "generic": GenericParser,
}


class GenericCollector(BaseCollector):
    """
    A flexible collector for dynamically-configured log paths.

    Args:
        log_path:       Full path to the log file to tail.
        collector_type: One of ssh|auth|nginx|apache|mysql|docker|generic.
        redis_client:   Shared Redis connection.
        config_id:      ID from the log_configs table (for tracking).
        label:          Human-readable label for logging.
    """

    def __init__(
        self,
        log_path: str,
        collector_type: str,
        redis_client: redis.Redis,
        config_id: int = 0,
        label: str = "",
    ):
        parser_cls = PARSER_MAP.get(collector_type.lower(), GenericParser)
        super().__init__(log_path, redis_client, parser_cls())
        self._collector_type = collector_type.lower()
        self.config_id = config_id
        self.label = label or log_path

    def get_source(self) -> str:
        return self._collector_type
