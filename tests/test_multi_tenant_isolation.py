"""HTTP 多租户隔离：每个请求携带自己的蓝湖 Cookie，彼此不能串号。

这些用例直接验证三条防线：
  1. 凭证解析：请求头 > 环境变量 > 占位符
  2. 缓存目录：不同凭证落到不同命名空间，同一凭证可复用
  3. 设计服务：不同凭证拿到不同实例，缓存根目录不重叠
"""

from contextvars import ContextVar

import pytest

import lanhu_mcp_server as server


class FakeRequest:
    def __init__(self, cookie=None, dds_cookie=None, name=None, role=None):
        self.headers = {}
        if cookie is not None:
            self.headers["x-lanhu-cookie"] = cookie
        if dds_cookie is not None:
            self.headers["x-lanhu-dds-cookie"] = dds_cookie
        if name is not None:
            self.headers["x-lanhu-name"] = name
        if role is not None:
            self.headers["x-lanhu-role"] = role
        self.query_params = {}


@pytest.fixture
def request_scope(monkeypatch):
    """模拟 FastMCP 的请求上下文：ContextVar 天然按协程任务隔离。"""
    current = ContextVar("test_request", default=None)

    def fake_get_http_request():
        request = current.get()
        if request is None:
            raise RuntimeError("No active HTTP request found.")
        return request

    def fake_headers():
        request = current.get()
        return dict(request.headers) if request is not None else {}

    import fastmcp.server.dependencies as dependencies

    monkeypatch.setattr(dependencies, "get_http_request", fake_get_http_request)
    monkeypatch.setattr(server, "_request_headers", fake_headers)
    return current


def _make_request_cookie(cookie):
    """每次调用用一个新的 Request 对象，避免复用上一次的凭证缓存。"""
    return FakeRequest(cookie=cookie)


def test_request_header_wins_over_environment(monkeypatch, request_scope):
    monkeypatch.setattr(server, "COOKIE", "shared=env")
    monkeypatch.setattr(server, "DDS_COOKIE", "shared=dds-env")
    request_scope.set(_make_request_cookie("mine=header"))

    credentials = server.resolve_credentials()

    assert credentials.cookie == "mine=header"
    # 带了自定义身份时，DDS 不能回落到服务端环境变量里的共享账号，否则设计稿
    # 会以服务端账号的权限去拉，属于跨租户越权。没单独给 DDS Cookie 就复用同一个。
    assert credentials.dds_cookie == "mine=header"


def test_falls_back_to_environment_without_header(monkeypatch, request_scope):
    monkeypatch.setattr(server, "COOKIE", "shared=env")
    monkeypatch.setattr(server, "DDS_COOKIE", "dds=env")
    request_scope.set(FakeRequest())

    credentials = server.resolve_credentials()

    assert credentials.cookie == "shared=env"
    assert credentials.dds_cookie == "dds=env"


def test_dds_header_is_independent(monkeypatch, request_scope):
    monkeypatch.setattr(server, "COOKIE", "shared=env")
    monkeypatch.setattr(server, "DDS_COOKIE", "shared=env")
    request_scope.set(FakeRequest(cookie="main=1", dds_cookie="design=2"))

    credentials = server.resolve_credentials()

    assert credentials.cookie == "main=1"
    assert credentials.dds_cookie == "design=2"


def test_placeholder_cookie_is_detected(request_scope):
    request_scope.set(FakeRequest())
    assert server.Credentials("").is_placeholder
    assert server.Credentials(server.DEFAULT_COOKIE).is_placeholder
    assert not server.Credentials("real=value").is_placeholder


def test_quoted_header_is_normalized(request_scope):
    """客户端常把 .env 里带引号的值原样塞进请求头，必须剥掉引号。"""
    request_scope.set(_make_request_cookie('"a=1; b=2"'))
    assert server.resolve_credentials().cookie == "a=1; b=2"


def test_different_accounts_get_different_cache_roots(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "DATA_DIR", tmp_path)

    alice = server.Credentials("alice=token")
    bob = server.Credentials("bob=token")

    alice_dir = server._scoped_data_dir(alice)
    bob_dir = server._scoped_data_dir(bob)

    assert alice.namespace != bob.namespace
    assert alice_dir != bob_dir
    # 两个账号的缓存根目录不能互相包含，否则删除一方会波及另一方。
    assert not alice_dir.is_relative_to(bob_dir)
    assert not bob_dir.is_relative_to(alice_dir)
    # 同一账号重复解析应稳定映射到同一目录，保证缓存能命中。
    assert server._scoped_data_dir(server.Credentials("alice=token")) == alice_dir


def test_metadata_cache_keys_are_scoped():
    alice = server.Credentials("alice=token")
    bob = server.Credentials("bob=token")

    alice_key = server._get_metadata_cache_key("pid", "did", credentials=alice)
    bob_key = server._get_metadata_cache_key("pid", "did", credentials=bob)

    assert alice_key != bob_key
    assert alice.namespace in alice_key
    assert bob.namespace not in alice_key


@pytest.mark.asyncio
async def test_concurrent_callers_do_not_share_credentials(monkeypatch, request_scope):
    """并发是串号最容易发生的场景，这里压一下交错执行。"""
    import asyncio

    monkeypatch.setattr(server, "COOKIE", "shared=env")

    async def worker(token):
        request_scope.set(_make_request_cookie(token))
        await asyncio.sleep(0)
        credentials = server.resolve_credentials()
        extractor = server.LanhuExtractor()
        await asyncio.sleep(0)
        return extractor.cookie, credentials.namespace

    tokens = [f"user{index}=token" for index in range(12)]
    results = await asyncio.gather(*(worker(token) for token in tokens))

    assert [cookie for cookie, _ in results] == tokens
    assert len({namespace for _, namespace in results}) == len(tokens)


def test_design_service_is_created_per_credential(monkeypatch, request_scope, tmp_path):
    if server.DesignService is None:
        pytest.skip("design modules are not installed")
    monkeypatch.setattr(server, "DATA_DIR", tmp_path)
    monkeypatch.setattr(server, "_design_service", None)
    monkeypatch.setitem(server._design_services, "__reset__", None)
    server._design_services.clear()

    request_scope.set(_make_request_cookie("alice=token"))
    alice_service = server.get_design_service()
    alice_root = alice_service.root

    request_scope.set(_make_request_cookie("bob=token"))
    bob_service = server.get_design_service()
    bob_root = bob_service.root

    assert alice_service is not bob_service
    assert alice_root != bob_root
    assert not str(alice_root).startswith(str(bob_root))
    assert not str(bob_root).startswith(str(alice_root))

    # 同一账号再次请求应复用实例，避免重复建索引。
    request_scope.set(_make_request_cookie("alice=token"))
    assert server.get_design_service() is alice_service

    server._design_services.clear()


def test_identity_headers_override_url_query(monkeypatch, request_scope):
    monkeypatch.setenv("LANHU_USER_NAME", "env-name")
    monkeypatch.setenv("LANHU_USER_ROLE", "env-role")

    request_scope.set(FakeRequest(name="张三", role="Tester"))

    assert server.get_user_info(None) == ("张三", "Tester")
