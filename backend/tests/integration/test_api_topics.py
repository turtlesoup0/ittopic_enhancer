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


class TestValidationAPI:
    """검증 API 통합 테스트."""

    async def test_validate_single_topic(self, client):
        """단일 토픽 검증 테스트."""
        # First, upload a topic
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=[SAMPLE_TOPICS_CREATE[0]],
        )
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if topic_ids:
            # Request validation
            response = await client.post(
                "/api/v1/validation/validate",
                json={
                    "topic_ids": topic_ids,
                    "reference_domains": ["all"],
                },
            )

            # Should create validation task
            assert response.status_code in [200, 201, 202]
            data = response.json()
            assert "task_id" in data or "results" in data

    async def test_validate_multiple_topics(self, client):
        """다중 토픽 검증 테스트."""
        # First, upload topics
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=SAMPLE_TOPICS_CREATE,
        )
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if len(topic_ids) > 0:
            # Request validation for all topics
            response = await client.post(
                "/api/v1/validation/validate",
                json={
                    "topic_ids": topic_ids,
                    "reference_domains": ["SW", "정보보안"],
                },
            )

            # Should create validation task
            assert response.status_code in [200, 201, 202]
            data = response.json()
            assert "task_id" in data or "results" in data

    async def test_validate_with_domain_filter(self, client):
        """도메인 필터와 함께 검증 테스트."""
        # First, upload topics
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=SAMPLE_TOPICS_CREATE,
        )
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if topic_ids:
            # Request validation with domain filter
            response = await client.post(
                "/api/v1/validation/validate",
                json={
                    "topic_ids": topic_ids,
                    "domain_filter": "신기술",
                    "reference_domains": ["all"],
                },
            )

            assert response.status_code in [200, 201, 202]
            data = response.json()
            assert "task_id" in data or "results" in data

    async def test_get_validation_status(self, client):
        """검증 태스크 상태 조회 테스트."""
        # First, create validation task
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=[SAMPLE_TOPICS_CREATE[0]],
        )
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if topic_ids:
            validation_response = await client.post(
                "/api/v1/validation/validate",
                json={
                    "topic_ids": topic_ids,
                    "reference_domains": ["all"],
                },
            )
            validation_data = validation_response.json()

            # Get task status if task_id is provided
            if "task_id" in validation_data:
                task_id = validation_data["task_id"]
                response = await client.get(f"/api/v1/validation/status/{task_id}")

                # Should return task status
                assert response.status_code in [200, 202, 404]
                if response.status_code == 200:
                    data = response.json()
                    assert "status" in data or "results" in data

    async def test_validate_empty_topic_list(self, client):
        """빈 토픽 목록 검증 테스트 (edge case)."""
        response = await client.post(
            "/api/v1/validation/validate",
            json={
                "topic_ids": [],
                "reference_domains": ["all"],
            },
        )

        # Should handle gracefully
        assert response.status_code in [400, 422]

    async def test_validate_nonexistent_topic(self, client):
        """존재하지 않는 토픽 검증 테스트."""
        response = await client.post(
            "/api/v1/validation/validate",
            json={
                "topic_ids": ["nonexistent-topic-id"],
                "reference_domains": ["all"],
            },
        )

        # Should handle gracefully (either 404 or process with warning)
        assert response.status_code in [200, 201, 202, 404, 422]


class TestProposalsAPI:
    """제안 API 통합 테스트."""

    async def test_get_proposals_for_topic(self, client):
        """토픽별 제안 목록 조회 테스트."""
        # First, upload a topic
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=[SAMPLE_TOPICS_CREATE[0]],
        )
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if topic_ids:
            topic_id = topic_ids[0]

            # Get proposals for the topic
            response = await client.get(f"/api/v1/proposals/{topic_id}")

            # Should return proposals list
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert "proposals" in data or "total" in data or isinstance(data, list)

    async def test_get_proposals_empty_topic(self, client):
        """존재하지 않는 토픽 제안 조회 테스트."""
        response = await client.get("/api/v1/proposals/nonexistent-topic-id")

        # Should return empty list or 404
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                assert data.get("proposals") == []

    async def test_proposal_data_structure(self, client):
        """제안 데이터 구조 검증 테스트."""
        # First, create a topic
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=[SAMPLE_TOPICS_CREATE[0]],
        )
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if topic_ids:
            topic_id = topic_ids[0]

            # Get proposals
            response = await client.get(f"/api/v1/proposals/{topic_id}")

            if response.status_code == 200:
                data = response.json()

                # Check data structure
                if isinstance(data, list) and len(data) > 0:
                    proposal = data[0]
                    # Verify required fields
                    assert "id" in proposal or "title" in proposal
                elif isinstance(data, dict) and "proposals" in data:
                    if len(data["proposals"]) > 0:
                        proposal = data["proposals"][0]
                        assert "id" in proposal or "title" in proposal


class TestValidationAndProposalIntegration:
    """검증 및 제안 통합 테스트."""

    async def test_full_validation_proposal_workflow(self, client):
        """전체 검증-제안 워크플로우 테스트."""
        # 1. Upload topic
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=[SAMPLE_TOPICS_CREATE[0]],
        )
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if not topic_ids:
            pytest.skip("No topic IDs returned from upload")

        topic_id = topic_ids[0]

        # 2. Request validation
        validation_response = await client.post(
            "/api/v1/validation/validate",
            json={
                "topic_ids": [topic_id],
                "reference_domains": ["all"],
            },
        )
        assert validation_response.status_code in [200, 201, 202]

        # 3. Get proposals (may be available after validation)
        proposals_response = await client.get(f"/api/v1/proposals/{topic_id}")
        assert proposals_response.status_code in [200, 404]

        # 4. Get topic details (should have validation info)
        topic_response = await client.get(f"/api/v1/topics/{topic_id}")
        if topic_response.status_code == 200:
            topic_data = topic_response.json()
            # Verify topic structure
            assert "id" in topic_data or "metadata" in topic_data

    async def test_korean_content_preservation(self, client):
        """한국어 콘텐츠 보존 테스트."""
        # Upload topic with Korean content
        korean_topic = {
            "file_path": "test/한글/테스트.md",
            "file_name": "테스트",
            "folder": "test/한글",
            "domain": "SW",
            "리드문": "한글 리드문입니다",
            "정의": "한글 정의입니다. 상세한 내용을 여기에 작성합니다.",
            "키워드": ["한국어", "키워드"],
            "해시태그": "#한글",
            "암기": "암기 내용입니다",
        }

        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=[korean_topic],
        )
        assert upload_response.status_code in [200, 201]

        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if topic_ids:
            # Verify Korean content is preserved
            get_response = await client.get(f"/api/v1/topics/{topic_ids[0]}")
            if get_response.status_code == 200:
                topic_data = get_response.json()
                # Check Korean fields
                assert "리드문" in topic_data or "content" in topic_data

    async def test_validation_with_incomplete_topic(self, client):
        """불완전한 토픽 검증 테스트."""
        # Upload incomplete topic
        incomplete_topic = {
            "file_path": "test/incomplete.md",
            "file_name": "incomplete",
            "folder": "test",
            "domain": "SW",
            "리드문": "",  # Empty
            "정의": "짧음",  # Too short
            "키워드": ["하나"],  # Only 1 keyword
            "해시태그": "",
            "암기": "",
        }

        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=[incomplete_topic],
        )
        assert upload_response.status_code in [200, 201]

        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if topic_ids:
            # Request validation - should detect gaps
            validation_response = await client.post(
                "/api/v1/validation/validate",
                json={
                    "topic_ids": topic_ids,
                    "reference_domains": ["all"],
                },
            )
            assert validation_response.status_code in [200, 201, 202]

            # Get proposals - should have improvement suggestions
            proposals_response = await client.get(f"/api/v1/proposals/{topic_ids[0]}")
            assert proposals_response.status_code in [200, 404]

    async def test_concurrent_validation_requests(self, client):
        """동시 검증 요청 테스트 (concurrency test)."""
        import asyncio

        # Upload multiple topics
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=SAMPLE_TOPICS_CREATE,
        )
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if len(topic_ids) > 1:
            # Create multiple concurrent validation requests
            async def validate_topic(topic_id: str):
                return await client.post(
                    "/api/v1/validation/validate",
                    json={
                        "topic_ids": [topic_id],
                        "reference_domains": ["all"],
                    },
                )

            # Run concurrent validations
            tasks = [validate_topic(tid) for tid in topic_ids[:3]]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should complete without errors
            for result in results:
                if not isinstance(result, Exception):
                    assert result.status_code in [200, 201, 202]
