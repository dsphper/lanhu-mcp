"""Request-scoped Lanhu credentials."""

from types import SimpleNamespace

import pytest

import lanhu_mcp_server as server


@pytest.mark.asyncio
async def test_request_cookie_overrides_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "COOKIE", "environment-cookie")
    monkeypatch.setattr(server, "DDS_COOKIE", "environment-dds-cookie")
    monkeypatch.setattr(
        server,
        "get_http_request",
        lambda: SimpleNamespace(headers={"x-lanhu-cookie": "request-cookie"}),
    )
    monkeypatch.setattr(server, "DATA_DIR", tmp_path)

    extractor = server.LanhuExtractor()
    service = server._get_request_design_service()

    assert extractor.client.headers["cookie"] == "request-cookie"
    assert extractor.dds_cookie == "request-cookie"
    assert service.cookie == "request-cookie"
    assert service.dds_cookie == "request-cookie"
    await extractor.close()


@pytest.mark.parametrize("headers", [{}, {"x-lanhu-cookie": ""}])
def test_request_cookie_falls_back_to_environment(monkeypatch, headers):
    monkeypatch.setattr(server, "COOKIE", "environment-cookie")
    monkeypatch.setattr(server, "DDS_COOKIE", "environment-dds-cookie")
    monkeypatch.setattr(
        server, "get_http_request", lambda: SimpleNamespace(headers=headers)
    )

    assert server._get_request_cookies() == (
        "environment-cookie",
        "environment-dds-cookie",
    )


def test_request_cookie_falls_back_without_http_request(monkeypatch):
    monkeypatch.setattr(server, "COOKIE", "environment-cookie")
    monkeypatch.setattr(server, "DDS_COOKIE", "environment-dds-cookie")

    def no_request():
        raise RuntimeError("No active HTTP request found.")

    monkeypatch.setattr(server, "get_http_request", no_request)

    assert server._get_request_cookies() == (
        "environment-cookie",
        "environment-dds-cookie",
    )
