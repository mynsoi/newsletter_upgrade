"""개발 PC의 SSL 주입 충돌 바로잡기 (2026-11-12).

개발 PC Python에는 사내망 인증서 때문에 pip_system_certs가 깔려 있다. 이 패키지는 Python이 켜질 때
pip 안에 들어 있는 truststore(pip._vendor.truststore)로 ssl.SSLContext를 바꿔 끼운다. 그런데
anthropic·openai SDK가 쓰는 httpx2는 따로 설치된 truststore를 쓰고, 이 truststore는 처음 불릴 때
ssl.SSLContext를 "원래 클래스"로 기억한다 — 이미 바뀐 클래스를 원본으로 잡아 HTTPS 연결 때마다
RecursionError(→ APIConnectionError)가 난다. curl·httpx 0.28·psycopg는 영향이 없다.

그래서 SDK를 부르기 직전에 pip 쪽 주입을 걷어 내고, 따로 설치된 truststore로 다시 주입한다.
시스템 인증서 저장소를 쓰는 동작은 그대로다. GitHub Actions처럼 pip_system_certs가 없는 곳에서는
아무것도 하지 않는다.
"""
from __future__ import annotations

import ssl

_PIP_TRUSTSTORE = "pip._vendor.truststore"


def repair_truststore_injection() -> bool:
    """pip 내장 truststore가 ssl에 주입돼 있으면 독립 truststore로 바꿔 끼운다. 바꿨으면 True."""
    if not ssl.SSLContext.__module__.startswith(_PIP_TRUSTSTORE):
        return False
    from pip._vendor import truststore as pip_truststore

    pip_truststore.extract_from_ssl()
    try:
        import truststore
    except ImportError:  # 독립 truststore가 없으면 SDK도 충돌하지 않는다 — 주입만 걷어 낸 채 둔다
        return True
    truststore.inject_into_ssl()
    return True
