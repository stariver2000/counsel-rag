# 패키지가 설치·임포트 가능한지 확인하는 최소 스모크.
# 왜: uv sync + hatch 패키징 설정이 깨지면 이후 모든 태스크가 막히므로 가장 먼저 잡는다.
import counsel_rag


def test_package_imports():
    assert counsel_rag is not None
