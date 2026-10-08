"""SSRF guard for the `http` node executor: block requests to non-public addresses."""

from __future__ import annotations

import pytest

from app.engine.executors import _assert_public_url


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://127.0.0.1:8000/",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata endpoint
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://[::1]/",
        "ftp://example.com/",  # non-http(s) scheme
    ],
)
def test_blocks_non_public_urls(url):
    with pytest.raises(ValueError):
        _assert_public_url(url)


def test_allows_public_url(monkeypatch):
    # Hermetic: don't depend on real DNS (fails offline / in sandboxed CI).
    monkeypatch.setattr(
        "app.engine.executors.socket.getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    _assert_public_url("https://example.com/")


def test_blocks_unresolvable_host():
    with pytest.raises(ValueError):
        _assert_public_url("http://this-host-does-not-exist.invalid/")
