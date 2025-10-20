import logging
import os
import random
import threading
import time
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

import requests


class ApiClientError(Exception):
    pass


class ApiClientHTTPError(ApiClientError):
    def __init__(self, message: str, status_code: int, response_text: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


def _parse_retry_after(header_value: str) -> Optional[float]:
    """Parse Retry-After header which can be seconds or HTTP-date.
    Returns seconds to sleep if parsable, otherwise None.
    """
    if not header_value:
        return None
    try:
        # Seconds format
        return float(header_value)
    except ValueError:
        # HTTP-date format, try best effort
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(header_value)
            if dt is not None:
                return max(0.0, (dt - dt.now(dt.tzinfo)).total_seconds())
        except Exception:
            return None
    return None


class ApiClient:
    """A unified API client with retry, backoff and structured logging."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[int, float]] = None,
        max_retries: Optional[int] = None,
        session: Optional[requests.Session] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        # Lazy import to avoid heavy import cycles during tests
        from config import BASE_URL as CFG_BASE_URL, HEADERS as CFG_HEADERS

        env_base_url = os.getenv("LINKLIKE_BASE_URL")
        self.base_url = (base_url or env_base_url or CFG_BASE_URL).rstrip("/") + "/"

        self.timeout = float(os.getenv("LINKLIKE_TIMEOUT", str(timeout if timeout is not None else 10)))
        self.max_retries = int(os.getenv("LINKLIKE_MAX_RETRIES", str(max_retries if max_retries is not None else 3)))

        self.session = session or requests.Session()
        # Merge provided headers over config headers to allow overrides
        base_headers = dict(CFG_HEADERS)
        if headers:
            base_headers.update(headers)
        self.session.headers.update(base_headers)

        self.logger = logger or logging.getLogger(__name__)

    def _build_url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        return urljoin(self.base_url, path_or_url.lstrip("/"))

    def request(
        self,
        method: str,
        path_or_url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[int, float]] = None,
    ) -> Any:
        url = self._build_url(path_or_url)
        attempts = 0
        last_error: Optional[str] = None

        while attempts < self.max_retries:
            attempts += 1
            start_ts = time.time()
            status_code = None
            try:
                resp = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=headers,
                    timeout=timeout or self.timeout,
                )
                status_code = resp.status_code

                # Success
                if 200 <= resp.status_code < 300:
                    elapsed_ms = int((time.time() - start_ts) * 1000)
                    self.logger.info(
                        "api_call: method=%s url=%s status=%s attempts=%s elapsed_ms=%s",
                        method,
                        url,
                        resp.status_code,
                        attempts,
                        elapsed_ms,
                    )
                    try:
                        return resp.json()
                    except ValueError:
                        return resp.text

                # Too Many Requests - handle Retry-After
                if resp.status_code == 429:
                    retry_after = _parse_retry_after(resp.headers.get("Retry-After", ""))
                    base_backoff = 2 ** (attempts - 1)
                    jitter = random.uniform(0, 0.5)
                    sleep_sec = retry_after if retry_after is not None else (base_backoff + jitter)

                    elapsed_ms = int((time.time() - start_ts) * 1000)
                    self.logger.warning(
                        "api_call_throttled: method=%s url=%s status=%s attempts=%s elapsed_ms=%s retry_after=%s",
                        method,
                        url,
                        resp.status_code,
                        attempts,
                        elapsed_ms,
                        sleep_sec,
                    )

                    if attempts >= self.max_retries:
                        raise ApiClientHTTPError(
                            f"HTTP 429 after {attempts} attempts", status_code=resp.status_code, response_text=resp.text
                        )
                    time.sleep(max(0.0, sleep_sec))
                    continue

                # Retry on 5xx and 408 (Request Timeout)
                if resp.status_code == 408 or 500 <= resp.status_code < 600:
                    base_backoff = 2 ** (attempts - 1)
                    jitter = random.uniform(0, 0.5)
                    elapsed_ms = int((time.time() - start_ts) * 1000)
                    self.logger.warning(
                        "api_call_retryable: method=%s url=%s status=%s attempts=%s elapsed_ms=%s wait=%s",
                        method,
                        url,
                        resp.status_code,
                        attempts,
                        elapsed_ms,
                        base_backoff + jitter,
                    )
                    if attempts >= self.max_retries:
                        raise ApiClientHTTPError(
                            f"HTTP {resp.status_code} after {attempts} attempts",
                            status_code=resp.status_code,
                            response_text=resp.text,
                        )
                    time.sleep(base_backoff + jitter)
                    continue

                # Do not retry other 4xx
                if 400 <= resp.status_code < 500:
                    elapsed_ms = int((time.time() - start_ts) * 1000)
                    self.logger.error(
                        "api_call_client_error: method=%s url=%s status=%s attempts=%s elapsed_ms=%s error=%s",
                        method,
                        url,
                        resp.status_code,
                        attempts,
                        elapsed_ms,
                        resp.text[:2000],
                    )
                    raise ApiClientHTTPError(
                        f"HTTP {resp.status_code}", status_code=resp.status_code, response_text=resp.text
                    )

                # Unexpected status - treat as error without retry
                elapsed_ms = int((time.time() - start_ts) * 1000)
                self.logger.error(
                    "api_call_unexpected: method=%s url=%s status=%s attempts=%s elapsed_ms=%s",
                    method,
                    url,
                    status_code,
                    attempts,
                    elapsed_ms,
                )
                raise ApiClientHTTPError(
                    f"Unexpected HTTP status {resp.status_code}", status_code=resp.status_code, response_text=resp.text
                )

            except (requests.Timeout, requests.ConnectionError, requests.RequestException) as e:
                last_error = str(e)
                base_backoff = 2 ** (attempts - 1)
                jitter = random.uniform(0, 0.5)
                elapsed_ms = int((time.time() - start_ts) * 1000)
                self.logger.warning(
                    "api_call_exception: method=%s url=%s attempts=%s elapsed_ms=%s error=%s wait=%s",
                    method,
                    url,
                    attempts,
                    elapsed_ms,
                    last_error,
                    base_backoff + jitter,
                )
                if attempts >= self.max_retries:
                    raise ApiClientError(f"Request failed after {attempts} attempts: {last_error}")
                time.sleep(base_backoff + jitter)
                continue

        # If we exit loop without returning/raising, raise generic error
        raise ApiClientError(f"Exhausted retries after {self.max_retries} attempts: {last_error}")

    def get(
        self,
        path_or_url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[int, float]] = None,
    ) -> Any:
        return self.request("GET", path_or_url, params=params, headers=headers, timeout=timeout)

    def post(
        self,
        path_or_url: str,
        *,
        json: Optional[Any] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[int, float]] = None,
    ) -> Any:
        return self.request("POST", path_or_url, json=json, data=data, headers=headers, timeout=timeout)


_thread_local = threading.local()


def get_thread_local_client(
    base_url: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[Union[int, float]] = None,
    max_retries: Optional[int] = None,
) -> ApiClient:
    """Returns a per-thread ApiClient instance. Updates headers if provided."""
    client: Optional[ApiClient] = getattr(_thread_local, "client", None)
    if client is None:
        client = ApiClient(base_url=base_url, headers=headers, timeout=timeout, max_retries=max_retries)
        _thread_local.client = client
        return client

    # Update headers dynamically for current thread client if provided
    if headers:
        client.session.headers.update(headers)
    # Update base_url/timeout/retries if provided
    if base_url:
        client.base_url = base_url.rstrip("/") + "/"
    if timeout is not None:
        client.timeout = float(timeout)
    if max_retries is not None:
        client.max_retries = int(max_retries)

    return client
