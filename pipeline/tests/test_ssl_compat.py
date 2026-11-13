"""개발 PC의 SSL 주입 충돌 바로잡기(src/ssl_compat.py, 2026-11-12)."""
import ssl
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_noop_when_pip_truststore_not_injected(monkeypatch):
    """Actions처럼 pip_system_certs가 없는 곳에서는 ssl을 건드리지 않는다."""
    from ssl_compat import repair_truststore_injection

    class Plain(ssl.SSLContext):
        pass

    Plain.__module__ = "ssl"
    monkeypatch.setattr(ssl, "SSLContext", Plain)
    assert repair_truststore_injection() is False
    assert ssl.SSLContext is Plain


def test_repaired_context_sets_verify_mode_without_recursion():
    """이 PC처럼 pip 내장 truststore가 주입돼 있어도, 바로잡은 뒤에는 독립 truststore 컨텍스트가 정상 동작한다."""
    truststore = pytest.importorskip("truststore")
    from ssl_compat import repair_truststore_injection

    repair_truststore_injection()
    assert not ssl.SSLContext.__module__.startswith("pip._vendor.truststore")
    ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.verify_mode = ssl.CERT_REQUIRED  # 충돌 상태에서는 여기서 RecursionError가 났다
    assert ctx.verify_mode == ssl.CERT_REQUIRED
