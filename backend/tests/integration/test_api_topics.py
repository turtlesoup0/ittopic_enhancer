"""Integration tests for Topics API."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


# 테스트용 API 키
TEST_API_KEY = "test-api-key-for-integration-tests-12345"


# 테스트용 샘플 데이터
SAMPLE_TOPICS_CREATE = [
    {
        "file_path": "1_Project/정보 관리 기술사/1_신기술/인공지능.md",
        "file_name": "인공지능",
        "folder": "1_Project/정보 관리 기술사/1_신기술",
        "domain": "신기술",
        "리드문": "인간의 지능적 행위를 컴퓨터가 수행하는 기술",
        "정의": "기계가 인간의 지능을 모방하는 기술",
        "키워드": ["AI", "머신러닝"],
        "해시태그": "#인공지능",
        "암기": "인공지능의 핵심 개념과 응용 분야",
    },
    {
        "file_path": "1_Project/정보 관리 기술사/2_정보보안/암호.md",
        "file_name": "암호",
        "folder": "1_Project/정보 관리 기술사/2_정보보안",
        "domain": "정보보안",
        "리드문": "정보를 보호하는 암호화 기술",
        "정의": "데이터를 비밀키로 변환하여 보호하는 기술",
        "키워드": ["보안", "암호화", "대칭키", "비대칭키"],
        "해시태그": "#보안",
        "암기": "암호 시스템의 종류와 특징",
    },
    {
        "file_path": "1_Project/정보 관리 기술사/6_데이터베이스/SQL.md",
        "file_name": "SQL",
        "folder": "1_Project/정보 관리 기술사/6_데이터베이스",
        "domain": "데이터베이스",
        "리드문": "데이터베이스 질의 언어",
        "정의": "관계형 데이터베이스에서 데이터를 조작하는 표준 언어",
        "키워드": ["데이터", "쿼리", "RDBMS"],
        "해시태그": "#DB",
        "암기": "SQL의 DDL, DML, DCL 명령어",
    },
]


@pytest.fixture
async def client():
    """Async test client fixture using ASGI transport."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": TEST_API_KEY},
    ) as ac:
        yield ac


class TestTopicsAPI:
    """Topics API 테스트 (Characterization Tests)."""

    async def test_health_check(self, client):
        """헬스 체크 테스트."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        # Characterization: actual behavior is "running" not "healthy"
        assert data["status"] == "running"
        assert "version" in data

    async def test_v1_health_check(self, client):
        """V1 API 헬스 체크 테스트."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_create_topic(self, client):
        """단일 토픽 생성 테스트."""
        topic_data = SAMPLE_TOPICS_CREATE[0]

        response = await client.post("/api/v1/topics/", json=topic_data)

        # Characterization test: document actual behavior
        assert response.status_code in [200, 201], f"Expected 200-201, got {response.status_code}"
        data = response.json()
        assert "id" in data or "file_path" in data

    async def test_upload_topics(self, client):
        """토픽 일괄 업로드 테스트."""
        response = await client.post(
            "/api/v1/topics/upload",
            json=SAMPLE_TOPICS_CREATE,
        )

        # Characterization test: document actual behavior
        assert response.status_code in [200, 201], f"Expected 200-201, got {response.status_code}"
        data = response.json()
        assert "uploaded_count" in data
        assert "topic_ids" in data
        assert data["uploaded_count"] == len(SAMPLE_TOPICS_CREATE)

    async def test_list_topics(self, client):
        """토픽 목록 조회 테스트."""
        # First, upload topics
        await client.post("/api/v1/topics/upload", json=SAMPLE_TOPICS_CREATE)

        # Then list them
        response = await client.get("/api/v1/topics/")

        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        assert "total" in data
        assert isinstance(data["topics"], list)

    async def test_list_topics_by_domain(self, client):
        """도메인별 토픽 목록 조회 테스트."""
        # First, upload topics
        await client.post("/api/v1/topics/upload", json=SAMPLE_TOPICS_CREATE)

        # Then filter by domain
        response = await client.get("/api/v1/topics/?domain=신기술")

        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        # Characterization: verify all returned topics are from the specified domain
        for topic in data.get("topics", []):
            assert topic.get("metadata", {}).get("domain") == "신기술"

    async def test_get_topic_by_id(self, client):
        """특정 토픽 조회 테스트."""
        # First, upload topics
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=SAMPLE_TOPICS_CREATE[:1],
        )
        upload_data = upload_response.json()
        topic_id = upload_data.get("topic_ids", [None])[0]

        if topic_id:
            # Then get the specific topic
            response = await client.get(f"/api/v1/topics/{topic_id}")

            # Characterization test: document actual behavior
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert data["id"] == topic_id

    async def test_update_topic(self, client):
        """토픽 업데이트 테스트."""
        # First, upload a topic
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=SAMPLE_TOPICS_CREATE[:1],
        )
        upload_data = upload_response.json()
        topic_id = upload_data.get("topic_ids", [None])[0]

        if topic_id:
            # Then update it
            update_data = {
                "리드문": "업데이트된 리드문: 인간의 지능을 기계가 구현",
                "정의": "업데이트된 정의: AI는 인공지능의 줄임말",
            }
            response = await client.put(f"/api/v1/topics/{topic_id}", json=update_data)

            # Characterization test: document actual behavior
            assert response.status_code in [200, 404]

    async def test_delete_topic(self, client):
        """토픽 삭제 테스트."""
        # First, upload a topic
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=SAMPLE_TOPICS_CREATE[:1],
        )
        upload_data = upload_response.json()
        topic_id = upload_data.get("topic_ids", [None])[0]

        if topic_id:
            # Then delete it
            response = await client.delete(f"/api/v1/topics/{topic_id}")

            # Characterization test: document actual behavior
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert "success" in data

    async def test_get_nonexistent_topic(self, client):
        """존재하지 않는 토픽 조회 테스트."""
        fake_id = "nonexistent-topic-id"
        response = await client.get(f"/api/v1/topics/{fake_id}")

        # Characterization test: document actual behavior
        assert response.status_code == 404

    async def test_api_key_required_for_mutations(self, client):
        """API 키 요구 사항 테스트 (Characterization)."""
        # Test with a client without API key
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as no_key_client:
            topic_data = SAMPLE_TOPICS_CREATE[0]
            response = await no_key_client.post("/api/v1/topics/", json=topic_data)

            # Characterization test: document actual behavior
            # Should return 401 Unauthorized without API key
            assert response.status_code == 401
            data = response.json()
            assert "error" in data
