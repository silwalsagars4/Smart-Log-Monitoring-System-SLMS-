"""Apache combined log parser (same format as Nginx combined)."""

from parsers.nginx_parser import NginxParser


class ApacheParser(NginxParser):
    """Apache uses the same combined log format as Nginx."""

    def parse(self, raw):
        result = super().parse(raw)
        if result:
            result["source"] = "apache"
        return result
