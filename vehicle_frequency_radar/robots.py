from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests


@dataclass
class RobotsDecision:
    allowed: bool
    crawl_delay_seconds: Optional[float] = None
    reason: str = ""


class RobotsGuard:
    def __init__(
        self,
        user_agent: str,
        session: requests.Session,
        strict: bool = True,
        timeout: int = 15,
    ) -> None:
        self.user_agent = user_agent
        self.session = session
        self.strict = strict
        self.timeout = timeout
        self._parsers: dict[str, Optional[RobotFileParser]] = {}
        self._last_fetch_by_host: dict[str, float] = {}

    def check(self, url: str) -> RobotsDecision:
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._get_parser(host)
        if parser is None:
            if self.strict:
                return RobotsDecision(False, reason="robots.txt unavailable in strict mode")
            return RobotsDecision(True, reason="robots.txt unavailable; non-strict mode")

        allowed = parser.can_fetch(self.user_agent, url)
        delay = parser.crawl_delay(self.user_agent)
        return RobotsDecision(
            allowed=allowed,
            crawl_delay_seconds=float(delay) if delay else None,
            reason="allowed by robots.txt" if allowed else "blocked by robots.txt",
        )

    def wait_for_host(self, url: str, min_delay_seconds: float) -> None:
        host = urlparse(url).netloc
        elapsed = time.monotonic() - self._last_fetch_by_host.get(host, 0)
        wait = max(0.0, min_delay_seconds - elapsed)
        if wait:
            time.sleep(wait)
        self._last_fetch_by_host[host] = time.monotonic()

    def _get_parser(self, host: str) -> Optional[RobotFileParser]:
        if host in self._parsers:
            return self._parsers[host]

        robots_url = urljoin(host, "/robots.txt")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            response = self.session.get(robots_url, timeout=self.timeout)
            if response.status_code >= 400:
                self._parsers[host] = None
                return None
            parser.parse(response.text.splitlines())
        except requests.RequestException:
            self._parsers[host] = None
            return None

        self._parsers[host] = parser
        return parser
