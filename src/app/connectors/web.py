"""Web scraping connector with boilerplate removal.

Uses trafilatura for content extraction and HTML-to-Markdown conversion.
Handles rate limits, retries, and content sanitization.

Reference: docs/03_INGESTION_STRATEGY.md Section 3.4
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any, ClassVar
from urllib.parse import urlparse

import httpx
import trafilatura
from trafilatura.settings import use_config

from app.schemas import AgentFailure, ErrorCodes


class WebConnector:
    """Fetch and extract clean content from web pages.

    Features:
        - Boilerplate removal (navigation, ads, footers)
        - HTML → Markdown conversion
        - Rate limiting with exponential backoff
        - User-Agent rotation
        - Content sanitization
        - Configurable timeouts
    """

    DEFAULT_USER_AGENTS: ClassVar[list[str]] = [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like"
            " Gecko) Chrome/109.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
        ),
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    ]

    def __init__(
        self,
        *,
        timeout: int = 30,
        max_retries: int = 5,
        user_agents: list[str] | None = None,
        allowed_domains: list[str] | None = None,
    ) -> None:
        """Initialize web connector.

        Args:
            timeout: Request timeout in seconds (default: 30).
            max_retries: Maximum retry attempts for transient failures.
            user_agents: List of User-Agent strings to rotate.
            allowed_domains: Whitelist of allowed domains (None = allow all).
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agents = user_agents or self.DEFAULT_USER_AGENTS
        self.allowed_domains = allowed_domains
        self._current_agent_idx = 0

        # Configure trafilatura for aggressive boilerplate removal
        self.trafilatura_config = use_config()
        self.trafilatura_config.set("DEFAULT", "EXTENSIVE_CLEANING", "true")

    def _get_user_agent(self) -> str:
        """Get next User-Agent in rotation."""
        agent = self.user_agents[self._current_agent_idx]
        self._current_agent_idx = (self._current_agent_idx + 1) % len(self.user_agents)
        return agent

    def _is_allowed_domain(self, url: str) -> bool:
        """Check if URL domain is in whitelist."""
        if self.allowed_domains is None:
            return True

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        return any(
            domain == allowed or domain.endswith(f".{allowed}")
            for allowed in self.allowed_domains
        )

    async def fetch(
        self,
        url: str,
        *,
        extract_metadata: bool = True,
    ) -> tuple[str, dict[str, Any]] | AgentFailure:
        """Fetch and extract clean content from a URL.

        Args:
            url: The URL to fetch.
            extract_metadata: Whether to extract page metadata (title, author, date).

        Returns:
            Tuple of (markdown_content, metadata) or AgentFailure.

        Error Codes:
            - ERR_CONNECTOR_BLOCKED_DOMAIN: Domain not in whitelist
            - ERR_CONNECTOR_NOT_FOUND: HTTP 404
            - ERR_CONNECTOR_AUTH: HTTP 401/403
            - ERR_CONNECTOR_RATE_LIMIT: HTTP 429
            - ERR_CONNECTOR_NETWORK: Network error or timeout
            - ERR_CONNECTOR_INVALID_CONTENT: No extractable content
        """
        # Validate domain
        if not self._is_allowed_domain(url):
            return AgentFailure(
                agent_id="web_connector",
                error_code=ErrorCodes.CONNECTOR_BLOCKED_DOMAIN,
                message=f"Domain not allowed: {urlparse(url).netloc}",
                recoverable=False,
            )

        # Fetch HTML with retries
        html_content = await self._fetch_with_retry(url)
        if isinstance(html_content, AgentFailure):
            return html_content

        # Extract clean content
        try:
            markdown = trafilatura.extract(
                html_content,
                output_format="markdown",
                config=self.trafilatura_config,
                include_comments=False,
                include_tables=True,
                include_links=True,
            )

            if not markdown or len(markdown.strip()) < 50:
                return AgentFailure(
                    agent_id="web_connector",
                    error_code=ErrorCodes.CONNECTOR_INVALID_CONTENT,
                    message=f"No extractable content from {url}",
                    recoverable=False,
                )

            # Extract metadata
            metadata: dict[str, Any] = {"url": url}
            if extract_metadata:
                meta = trafilatura.extract_metadata(html_content)
                if meta:
                    metadata.update(
                        {
                            "title": meta.title,
                            "author": meta.author,
                            "date": meta.date,
                            "description": meta.description,
                            "sitename": meta.sitename,
                        }
                    )

            # Add content hash for deduplication
            content_hash = hashlib.sha256(markdown.encode()).hexdigest()[:16]
            metadata["content_hash"] = content_hash

            return (markdown, metadata)

        except Exception as e:
            return AgentFailure(
                agent_id="web_connector",
                error_code=ErrorCodes.CONNECTOR_INVALID_CONTENT,
                message=f"Content extraction failed: {e!s}",
                recoverable=False,
            )

    async def _fetch_with_retry(self, url: str) -> str | AgentFailure:
        """Fetch URL with exponential backoff on transient errors.

        Retry on:
            - HTTP 429 (rate limit)
            - HTTP 503 (service unavailable)
            - Network timeouts
            - Connection errors

        Returns:
            HTML content or AgentFailure.
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                headers = {
                    "User-Agent": self._get_user_agent(),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                }

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        url, headers=headers, follow_redirects=True
                    )

                    # Handle HTTP errors
                    if response.status_code == 404:
                        return AgentFailure(
                            agent_id="web_connector",
                            error_code=ErrorCodes.CONNECTOR_NOT_FOUND,
                            message=f"Page not found: {url}",
                            recoverable=False,
                        )

                    if response.status_code in {401, 403}:
                        return AgentFailure(
                            agent_id="web_connector",
                            error_code=ErrorCodes.CONNECTOR_AUTH,
                            message=(
                                f"Access denied (HTTP {response.status_code}): {url}"
                            ),
                            recoverable=False,
                        )

                    # Retry on rate limit or service unavailable
                    if response.status_code in {429, 503}:
                        if attempt < self.max_retries - 1:
                            backoff = 2**attempt  # 1s, 2s, 4s, 8s, 16s
                            await asyncio.sleep(backoff)
                            continue

                        return AgentFailure(
                            agent_id="web_connector",
                            error_code=ErrorCodes.CONNECTOR_RATE_LIMIT,
                            message=(
                                "Rate limit exceeded after"
                                f" {attempt + 1} attempts: {url}"
                            ),
                            recoverable=True,
                        )

                    response.raise_for_status()
                    return response.text

            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.NetworkError,
            ) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    backoff = 2**attempt
                    await asyncio.sleep(backoff)
                    continue

        # All retries exhausted
        return AgentFailure(
            agent_id="web_connector",
            error_code=ErrorCodes.CONNECTOR_NETWORK,
            message=(
                f"Network error after {self.max_retries} attempts: {last_error!s}"
            ),
            recoverable=True,
        )
