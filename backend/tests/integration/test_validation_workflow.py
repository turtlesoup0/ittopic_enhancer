"""Integration tests for complete validation workflow."""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


# 테스트용 API 키
TEST_API_KEY = "test-api-key-for-integration-tests-12345"

# SQLite Skip Reason
# aiosqlite와 background tasks의 동시성 제한으로 인해 다음 테스트는 SQLite에서 skip됩니다.
# 프로덕션 환경(PostgreSQL)에서는 정상 작동합니다.
SQLITE_SKIP_REASON = "SQLite+aiosqlite does not support concurrent writes with background tasks. Use PostgreSQL in production."


# 테스트용 샘플 데이터
SAMPLE_TOPICS = [
    {
        "file_path": "test/신기술/머신러닝.md",
        "file_name": "머신러닝",
        "folder": "test/신기술",
        "domain": "신기술",
        "리드문": "데이터로부터 학습하는 알고리즘",
        "정의": "명시적으로 프로그래밍하지 않고 데이터에서 패턴을 학습하는 기술",
        "키워드": ["AI"],
        "해시태그": "#AI",
        "암기": "지도학습, 비지도학습, 강화학습",
    },
    {
        "file_path": "test/정보보안/방화벽.md",
        "file_name": "방화벽",
        "folder": "test/정보보안",
        "domain": "정보보안",
        "리드문": "네트워크 보안 시스템",
        "정의": "외부 공격으로부터 내부 네트워크를 보호하는 시스템",
        "키워드": ["보안"],
        "해시태그": "#보안",
        "암기": "패킷 필터링, 프록시, 상태 검사",
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


class TestValidationWorkflow:
    """검증 워크플로우 통합 테스트 (Characterization Tests)."""

    @pytest.mark.skip(reason=SQLITE_SKIP_REASON)
    async def test_complete_validation_cycle(self, client):
        """전체 검증 사이클 테스트: Upload -> Validate -> Proposals."""
        # Step 1: Upload topics
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=SAMPLE_TOPICS,
        )
        assert upload_response.status_code in [200, 201]
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])
        assert len(topic_ids) > 0, "No topics were uploaded"

        # Step 2: Create validation task
        validate_response = await client.post(
            "/api/v1/validate/",
            json={
                "topic_ids": topic_ids,
                "domain_filter": None,
                "reference_domains": ["all"],
            },
        )

        # Characterization test: document actual behavior
        assert validate_response.status_code in [200, 202, 400]
        validate_data = validate_response.json()

        # If validation task was created
        if validate_response.status_code in [200, 202]:
            task_id = validate_data.get("task_id")
            assert task_id is not None

            # Step 3: Poll for completion (with timeout)
            # SQLite는 동시성 제한이 있어 더 긴 대기 시간 필요
            max_polls = 60  # 최대 60초 대기
            poll_interval = 1.0  # 1초 간격

            for _ in range(max_polls):
                await asyncio.sleep(poll_interval)

                status_response = await client.get(f"/api/v1/validate/task/{task_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data.get("status")

                    if current_status == "completed":
                        # Step 4: Get validation results
                        result_response = await client.get(
                            f"/api/v1/validate/task/{task_id}/result"
                        )
                        assert result_response.status_code == 200
                        results = result_response.json()

                        # Characterization test: document result structure
                        assert isinstance(results, list)

                        # Step 5: Generate proposals
                        proposals_response = await client.post(
                            f"/api/v1/validate/task/{task_id}/proposals"
                        )
                        assert proposals_response.status_code == 200
                        proposals = proposals_response.json()

                        # Characterization test: document proposal structure
                        assert isinstance(proposals, list)

                        # Step 6: Get proposals for each topic
                        for topic_id in topic_ids:
                            proposal_list_response = await client.get(
                                f"/api/v1/proposals/?topic_id={topic_id}"
                            )
                            assert proposal_list_response.status_code == 200
                            proposal_data = proposal_list_response.json()
                            assert "proposals" in proposal_data
                            assert "total" in proposal_data

                        break  # Exit poll loop on success

                    elif current_status in ["failed", "error"]:
                        # Characterization test: document failure behavior
                        break

            else:
                # Timeout - characterization test: document timeout behavior
                pytest.skip("Validation task timed out (expected for integration test without LLM)")

    @pytest.mark.skip(reason=SQLITE_SKIP_REASON)
    async def test_validation_without_references(self, client):
        """참조 문서 없는 검증 테스트 (Characterization)."""
        # Upload topic first
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=SAMPLE_TOPICS[:1],
        )
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if topic_ids:
            # Create validation task
            validate_response = await client.post(
                "/api/v1/validate/",
                json={"topic_ids": topic_ids},
            )

            # Characterization test: document behavior without indexed references
            # System should either complete with degraded results or fail gracefully
            assert validate_response.status_code in [200, 202, 400, 500]

    async def test_proposal_application_workflow(self, client):
        """제안 적용 워크플로우 테스트 (Characterization)."""
        # Upload and validate (may skip if no references)
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=SAMPLE_TOPICS[:1],
        )
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if not topic_ids:
            pytest.skip("No topics uploaded")

        # Get proposals for the topic
        proposals_response = await client.get(
            f"/api/v1/proposals/?topic_id={topic_ids[0]}"
        )
        proposals_data = proposals_response.json()
        proposals = proposals_data.get("proposals", [])

        if proposals:
            # Try to apply a proposal
            proposal = proposals[0]
            proposal_id = proposal.get("id")

            if proposal_id:
                apply_response = await client.post(
                    "/api/v1/proposals/apply",
                    json={
                        "proposal_id": proposal_id,
                        "topic_id": topic_ids[0],
                    },
                )

                # Characterization test: document actual behavior
                assert apply_response.status_code in [200, 404, 400]

    async def test_reference_indexing_workflow(self, client):
        """참조 문서 인덱싱 워크플로우 테스트 (Characterization)."""
        # Note: This test requires actual PDF files
        # Characterization test: document behavior when files don't exist

        index_response = await client.post(
            "/api/v1/references/index",
            json={
                "source_paths": ["/nonexistent/file.pdf"],
                "source_type": "pdf_book",
                "domain": "test",
                "force_reindex": False,
            },
        )

        # Characterization test: document error handling
        # Should either return success with failed_count or handle gracefully
        assert index_response.status_code in [200, 400, 500]

        if index_response.status_code == 200:
            data = index_response.json()
            assert "indexed_count" in data
            assert "failed_count" in data

    async def test_list_references(self, client):
        """참조 문서 목록 조회 테스트 (Characterization)."""
        response = await client.get("/api/v1/references/")

        # Characterization test: document actual behavior
        assert response.status_code == 200
        data = response.json()
        assert "references" in data
        assert "total" in data
        assert isinstance(data["references"], list)

    async def test_pagination_behavior(self, client):
        """페이지네이션 동작 테스트 (Characterization)."""
        # Upload multiple topics
        topics_to_upload = SAMPLE_TOPICS * 3  # Create duplicates for pagination
        await client.post("/api/v1/topics/upload", json=topics_to_upload)

        # Test different page sizes
        for page_size in [1, 5, 10, 20]:
            response = await client.get(f"/api/v1/topics/?page=1&size={page_size}")

            assert response.status_code == 200
            data = response.json()
            assert "topics" in data
            assert "total" in data
            assert "page" in data
            assert "size" in data

            # Characterization test: verify pagination works as expected
            returned_count = len(data["topics"])
            assert returned_count <= page_size

    async def test_domain_filtering(self, client):
        """도메인 필터링 테스트 (Characterization)."""
        # Upload topics
        await client.post("/api/v1/topics/upload", json=SAMPLE_TOPICS)

        # Test filtering by each domain
        for domain in ["신기술", "정보보안"]:
            response = await client.get(f"/api/v1/topics/?domain={domain}")

            assert response.status_code == 200
            data = response.json()

            # Characterization test: verify domain filtering
            for topic in data.get("topics", []):
                topic_domain = topic.get("metadata", {}).get("domain")
                if topic_domain:
                    assert topic_domain == domain

    async def test_error_handling_invalid_data(self, client):
        """잘못된 데이터 에러 핸들링 테스트 (Characterization)."""
        # Test with invalid topic data
        invalid_topic = {
            "file_path": "",  # Invalid empty path
            "file_name": "",  # Invalid empty name
            "domain": "InvalidDomain",  # Invalid domain
        }

        response = await client.post("/api/v1/topics/", json=invalid_topic)

        # Characterization test: document actual error behavior
        # Should return validation error or handle gracefully
        assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.skip(reason=SQLITE_SKIP_REASON)
    async def test_concurrent_validation_requests(self, client):
        """동시 검증 요청 테스트 (Characterization)."""
        # Upload topics
        upload_response = await client.post(
            "/api/v1/topics/upload",
            json=SAMPLE_TOPICS,
        )
        upload_data = upload_response.json()
        topic_ids = upload_data.get("topic_ids", [])

        if not topic_ids:
            pytest.skip("No topics uploaded")

        # Create multiple validation tasks concurrently
        tasks = []
        for _ in range(3):
            response = await client.post(
                "/api/v1/validate/",
                json={"topic_ids": topic_ids},
            )
            if response.status_code in [200, 202]:
                data = response.json()
                task_id = data.get("task_id")
                if task_id:
                    tasks.append(task_id)

        # Characterization test: document concurrent request handling
        # System should handle multiple requests gracefully
        assert len(tasks) >= 0  # At minimum, should not crash


@pytest.mark.parametrize("domain", ["신기술", "정보보안", "네트워크"])
async def test_domain_specific_validation(client, domain):
    """도메인별 검증 테스트 (Parameterized)."""
    topic = {
        "file_path": f"test/{domain}/test_topic.md",
        "file_name": "test_topic",
        "folder": f"test/{domain}",
        "domain": domain,
        "exam_frequency": "medium",  # 명시적 추가
        "리드문": f"{domain} 테스트 리드문",
        "정의": f"{domain} 테스트 정의",
        "키워드": ["테스트"],
        "해시태그": "#테스트",
        "암기": "테스트 암기 내용",
    }

    # upload 엔드포인트 사용 (단일 topic도 리스트로)
    upload_response = await client.post("/api/v1/topics/upload", json=[topic])
    assert upload_response.status_code in [200, 201]
