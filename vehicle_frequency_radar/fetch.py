from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

from .config import USER_AGENT
from .robots import RobotsGuard


@dataclass
class FetchResult:
    url: str
    status_code: Optional[int]
    text: str
    error: str = ""


class Fetcher:
    def __init__(
        self,
        user_agent: str = USER_AGENT,
        strict_robots: bool = True,
        timeout: int = 25,
    ) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fr,en;q=0.8,ar;q=0.7",
            }
        )
        self.timeout = timeout
        self.robots = RobotsGuard(user_agent, self.session, strict=strict_robots)

    def get(self, url: str, min_delay_seconds: float) -> FetchResult:
        decision = self.robots.check(url)
        if not decision.allowed:
            return FetchResult(url=url, status_code=None, text="", error=decision.reason)

        delay = max(min_delay_seconds, decision.crawl_delay_seconds or 0)
        self.robots.wait_for_host(url, delay)

        try:
            response = self.session.get(url, timeout=self.timeout)
            return FetchResult(
                url=response.url,
                status_code=response.status_code,
                text=response.text if response.ok else "",
                error="" if response.ok else f"HTTP {response.status_code}",
            )
        except requests.RequestException as exc:
            return FetchResult(url=url, status_code=None, text="", error=str(exc))

    def render(self, url: str, min_delay_seconds: float) -> FetchResult:
        decision = self.robots.check(url)
        if not decision.allowed:
            return FetchResult(url=url, status_code=None, text="", error=decision.reason)

        delay = max(min_delay_seconds, decision.crawl_delay_seconds or 0)
        self.robots.wait_for_host(url, delay)

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return FetchResult(
                url=url,
                status_code=None,
                text="",
                error="Playwright is not installed. Run: pip install '.[playwright]'",
            )

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(user_agent=self.session.headers["User-Agent"])
                response = page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)
                html = page.content()
                final_url = page.url
                status_code = response.status if response else None
                browser.close()
            return FetchResult(url=final_url, status_code=status_code, text=html)
        except Exception as exc:
            return FetchResult(url=url, status_code=None, text="", error=f"Playwright render failed: {exc}")
