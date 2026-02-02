"""
Repository 단위 테스트.

TopicRepository, ValidationRepository, ReferenceRepository, ProposalRepository의
CRUD 연산을 테스트합니다.
"""
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# TopicRepository 테스트
# =============================================================================
class TestTopicRepository:
    """TopicRepository CRUD 테스트."""

    @pytest.mark.asyncio
    async def test_create_topic(self, topic_repo, sample_topic_create):
        """토픽 생성 테스트."""
        topic = await topic_repo.create(sample_topic_create)

        assert topic is not None
        assert topic.metadata.file_path == sample_topic_create.file_path
        assert topic.metadata.domain == sample_topic_create.domain
        assert topic.content.리드문 == sample_topic_create.리드문
        assert topic.id is not None

    @pytest.mark.asyncio
    async def test_get_by_id(self, topic_repo, sample_topic_create):
        """ID로 토픽 조회 테스트."""
        created = await topic_repo.create(sample_topic_create)
        found = await topic_repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.metadata.file_path == created.metadata.file_path

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, topic_repo):
        """존재하지 않는 ID 조회 테스트."""
        result = await topic_repo.get_by_id("nonexistent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_file_path(self, topic_repo, sample_topic_create):
        """파일 경로로 토픽 조회 테스트."""
        await topic_repo.create(sample_topic_create)
        found = await topic_repo.get_by_file_path(sample_topic_create.file_path)

        assert found is not None
        assert found.metadata.file_path == sample_topic_create.file_path

    @pytest.mark.asyncio
    async def test_list_by_domain(self, topic_repo, sample_topic_create):
        """도메인별 토픽 목록 조회 테스트."""
        # 같은 도메인에 여러 토픽 생성
        await topic_repo.create(sample_topic_create)

        from app.models.topic import TopicCreate
        topic_create_2 = TopicCreate(
            file_path="/test/path/topic2.md",
            file_name="topic2.md",
            folder="test_folder",
            domain="SW",  # 같은 도메인
            리드문="리드문2",
            정의="정의2",
            키워드=["키워드3"],
            해시태그="#테스트2",
            암기="암기2",
        )
        await topic_repo.create(topic_create_2)

        # 도메인별 조회
        topics = await topic_repo.list_by_domain("SW")

        assert len(topics) == 2
        assert all(t.metadata.domain == "SW" for t in topics)

    @pytest.mark.asyncio
    async def test_update_topic(self, topic_repo, sample_topic_create):
        """토픽 수정 테스트."""
        created = await topic_repo.create(sample_topic_create)

        from app.models.topic import TopicUpdate
        update_data = TopicUpdate(
            리드문="수정된 리드문",
        )

        updated = await topic_repo.update(created.id, update_data)

        assert updated is not None
        assert updated.content.리드문 == "수정된 리드문"

    @pytest.mark.asyncio
    async def test_update_nonexistent_topic(self, topic_repo):
        """존재하지 않는 토픽 수정 테스트."""
        from app.models.topic import TopicUpdate
        update_data = TopicUpdate(리드문="새 리드문")

        result = await topic_repo.update("nonexistent_id", update_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_topic(self, topic_repo, sample_topic_create):
        """토픽 삭제 테스트."""
        created = await topic_repo.create(sample_topic_create)

        deleted = await topic_repo.delete(created.id)
        assert deleted is True

        # 삭제 후 조회되지 않아야 함
        found = await topic_repo.get_by_id(created.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_topic(self, topic_repo):
        """존재하지 않는 토픽 삭제 테스트."""
        result = await topic_repo.delete("nonexistent_id")
        assert result is False

    @pytest.mark.asyncio
    async def test_count_by_domain(self, topic_repo, sample_topic_create):
        """도메인별 토픽 수 카운트 테스트."""
        await topic_repo.create(sample_topic_create)

        count = await topic_repo.count_by_domain("SW")
        assert count == 1

        count_other = await topic_repo.count_by_domain("정보보안")
        assert count_other == 0


# =============================================================================
# ValidationRepository 테스트
# =============================================================================
class TestValidationRepository:
    """ValidationRepository CRUD 테스트."""

    @pytest.mark.asyncio
    async def test_create_validation(self, validation_repo, sample_validation_result):
        """검증 결과 생성 테스트."""
        validation = await validation_repo.create(sample_validation_result)

        assert validation is not None
        assert validation.id == sample_validation_result.id
        assert validation.topic_id == sample_validation_result.topic_id
        assert validation.overall_score == sample_validation_result.overall_score

    @pytest.mark.asyncio
    async def test_get_by_id(self, validation_repo, sample_validation_result):
        """ID로 검증 결과 조회 테스트."""
        created = await validation_repo.create(sample_validation_result)
        found = await validation_repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.topic_id == created.topic_id

    @pytest.mark.asyncio
    async def test_get_by_topic_id(self, validation_repo, sample_validation_result):
        """토픽별 검증 결과 조회 테스트."""
        await validation_repo.create(sample_validation_result)

        # 같은 토픽에 또 다른 검증 결과 생성
        from app.models.validation import ValidationResult, ContentGap, MatchedReference
        import uuid

        validation2 = ValidationResult(
            id=str(uuid.uuid4()),
            topic_id=sample_validation_result.topic_id,
            overall_score=0.75,
            field_completeness_score=0.8,
            content_accuracy_score=0.7,
            reference_coverage_score=0.75,
            gaps=[],
            matched_references=[],
            validation_timestamp=datetime.now(),
        )
        await validation_repo.create(validation2)

        # 토픽별 조회
        results = await validation_repo.get_by_topic_id(sample_validation_result.topic_id)

        assert len(results) == 2
        assert all(r.topic_id == sample_validation_result.topic_id for r in results)

    @pytest.mark.asyncio
    async def test_get_latest_by_topic(self, validation_repo, sample_validation_result):
        """최신 검증 결과 조회 테스트."""
        await validation_repo.create(sample_validation_result)

        latest = await validation_repo.get_latest_by_topic(sample_validation_result.topic_id)

        assert latest is not None
        assert latest.topic_id == sample_validation_result.topic_id

    @pytest.mark.asyncio
    async def test_get_latest_by_topic_not_found(self, validation_repo):
        """존재하지 않는 토픽의 최신 검증 결과 조회 테스트."""
        result = await validation_repo.get_latest_by_topic("nonexistent_topic")
        assert result is None


# =============================================================================
# ValidationTaskRepository 테스트
# =============================================================================
class TestValidationTaskRepository:
    """ValidationTaskRepository CRUD 테스트."""

    @pytest.mark.asyncio
    async def test_create_task(self, validation_task_repo):
        """검증 작업 생성 테스트."""
        task_id = "task_123"
        topic_ids = ["topic1", "topic2", "topic3"]

        task = await validation_task_repo.create(
            task_id=task_id,
            topic_ids=topic_ids,
            domain_filter="SW",
        )

        assert task is not None
        assert task.task_id == task_id
        assert task.status == "queued"
        assert task.total == 3
        assert task.current == 0

    @pytest.mark.asyncio
    async def test_get_by_id(self, validation_task_repo):
        """ID로 작업 조회 테스트."""
        task_id = "task_456"
        await validation_task_repo.create(task_id=task_id, topic_ids=["topic1"])

        found = await validation_task_repo.get_by_id(task_id)

        assert found is not None
        assert found.task_id == task_id

    @pytest.mark.asyncio
    async def test_update_status(self, validation_task_repo):
        """작업 상태 수정 테스트."""
        task_id = "task_789"
        await validation_task_repo.create(task_id=task_id, topic_ids=["topic1"])

        # 상태를 진행 중으로 변경
        updated = await validation_task_repo.update_status(
            task_id=task_id,
            status="running",
            progress=33,
            current=1,
        )

        assert updated is not None
        assert updated.status == "running"
        assert updated.progress == 33
        assert updated.current == 1

    @pytest.mark.asyncio
    async def test_update_status_completed(self, validation_task_repo):
        """작업 완료 상태 수정 테스트."""
        task_id = "task_101"
        await validation_task_repo.create(task_id=task_id, topic_ids=["topic1"])

        updated = await validation_task_repo.update_status(
            task_id=task_id,
            status="completed",
            progress=100,
            current=1,
        )

        assert updated is not None
        assert updated.status == "completed"

    @pytest.mark.asyncio
    async def test_update_status_with_error(self, validation_task_repo):
        """에러와 함께 상태 수정 테스트."""
        task_id = "task_102"
        await validation_task_repo.create(task_id=task_id, topic_ids=["topic1"])

        updated = await validation_task_repo.update_status(
            task_id=task_id,
            status="failed",
            error="Test error message",
        )

        assert updated is not None
        assert updated.status == "failed"
        assert updated.error == "Test error message"


# =============================================================================
# ReferenceRepository 테스트
# =============================================================================
class TestReferenceRepository:
    """ReferenceRepository CRUD 테스트."""

    @pytest.mark.asyncio
    async def test_create_reference(self, reference_repo, sample_reference_create):
        """참조 문서 생성 테스트."""
        reference = await reference_repo.create(sample_reference_create)

        assert reference is not None
        assert reference.id is not None
        assert reference.title == sample_reference_create.title
        assert reference.source_type == sample_reference_create.source_type
        assert reference.domain == sample_reference_create.domain

    @pytest.mark.asyncio
    async def test_get_by_id(self, reference_repo, sample_reference_create):
        """ID로 참조 문서 조회 테스트."""
        created = await reference_repo.create(sample_reference_create)
        found = await reference_repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.title == created.title

    @pytest.mark.asyncio
    async def test_get_by_file_path(self, reference_repo, sample_reference_create):
        """파일 경로로 참조 문서 조회 테스트."""
        created = await reference_repo.create(sample_reference_create)
        found = await reference_repo.get_by_file_path(created.file_path)

        assert found is not None
        assert found.file_path == created.file_path

    @pytest.mark.asyncio
    async def test_list_by_domain(self, reference_repo, sample_reference_create):
        """도메인별 참조 문서 목록 조회 테스트."""
        await reference_repo.create(sample_reference_create)

        from app.models.reference import ReferenceCreate, ReferenceSourceType
        ref_create_2 = ReferenceCreate(
            source_type=ReferenceSourceType.PDF_BOOK,
            title="참조 문서2",
            content="내용2",
            domain="SW",
            trust_score=1.0,
        )
        await reference_repo.create(ref_create_2)

        # 도메인별 조회
        references = await reference_repo.list_by_domain("SW")

        assert len(references) == 2
        assert all(r.domain == "SW" for r in references)

    @pytest.mark.asyncio
    async def test_list_by_domain_with_source_type(self, reference_repo, sample_reference_create):
        """도메인 및 소스 타입별 참조 문서 목록 조회 테스트."""
        await reference_repo.create(sample_reference_create)

        from app.models.reference import ReferenceCreate, ReferenceSourceType
        from app.models.topic import DomainEnum
        ref_create_2 = ReferenceCreate(
            source_type=ReferenceSourceType.MARKDOWN,  # 다른 타입
            title="마크다운 참조",
            content="마크다운 내용",
            domain=DomainEnum.SW.value,
            trust_score=0.6,
        )
        await reference_repo.create(ref_create_2)

        # PDF_BOOK만 필터링
        pdf_references = await reference_repo.list_by_domain("SW", ReferenceSourceType.PDF_BOOK.value)

        assert len(pdf_references) == 1
        assert pdf_references[0].source_type.value == ReferenceSourceType.PDF_BOOK.value

    @pytest.mark.asyncio
    async def test_create_with_embedding(self, reference_repo, sample_reference_create):
        """임베딩 포함 참조 문서 생성 테스트."""
        embedding = [0.1] * 768  # 768차원 임베딩

        reference = await reference_repo.create_with_embedding(
            reference_create=sample_reference_create,
            embedding=embedding,
        )

        assert reference is not None
        assert reference.embedding == embedding

    @pytest.mark.asyncio
    async def test_update_embedding(self, reference_repo, sample_reference_create):
        """임베딩 수정 테스트."""
        created = await reference_repo.create(sample_reference_create)
        new_embedding = [0.2] * 768

        updated = await reference_repo.update_embedding(created.id, new_embedding)

        assert updated is not None
        assert updated.embedding == new_embedding

    @pytest.mark.asyncio
    async def test_delete_reference(self, reference_repo, sample_reference_create):
        """참조 문서 삭제 테스트."""
        created = await reference_repo.create(sample_reference_create)

        deleted = await reference_repo.delete(created.id)
        assert deleted is True

        # 삭제 후 조회되지 않아야 함
        found = await reference_repo.get_by_id(created.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_count_by_domain(self, reference_repo, sample_reference_create):
        """도메인별 참조 문서 수 카운트 테스트."""
        await reference_repo.create(sample_reference_create)

        count = await reference_repo.count_by_domain("SW")
        assert count == 1

        count_other = await reference_repo.count_by_domain("정보보안")
        assert count_other == 0

    @pytest.mark.asyncio
    async def test_get_by_ids(self, reference_repo, sample_reference_create):
        """여러 ID로 참조 문서 조회 테스트."""
        ref1 = await reference_repo.create(sample_reference_create)

        from app.models.reference import ReferenceCreate, ReferenceSourceType
        ref_create_2 = ReferenceCreate(
            source_type=ReferenceSourceType.PDF_BOOK,
            title="참조2",
            content="내용2",
            domain="SW",
            trust_score=1.0,
        )
        ref2 = await reference_repo.create(ref_create_2)

        # 여러 ID로 조회
        references = await reference_repo.get_by_ids([ref1.id, ref2.id])

        assert len(references) == 2
        ids = {r.id for r in references}
        assert ref1.id in ids
        assert ref2.id in ids


# =============================================================================
# ProposalRepository 테스트
# =============================================================================
class TestProposalRepository:
    """ProposalRepository CRUD 테스트."""

    @pytest.mark.asyncio
    async def test_create_proposal(self, proposal_repo, sample_proposal):
        """제안 생성 테스트."""
        proposal = await proposal_repo.create(sample_proposal)

        assert proposal is not None
        assert proposal.id == sample_proposal.id
        assert proposal.topic_id == sample_proposal.topic_id
        assert proposal.priority == sample_proposal.priority

    @pytest.mark.asyncio
    async def test_get_by_id(self, proposal_repo, sample_proposal):
        """ID로 제안 조회 테스트."""
        created = await proposal_repo.create(sample_proposal)
        found = await proposal_repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.title == created.title

    @pytest.mark.asyncio
    async def test_get_by_topic_id(self, proposal_repo, sample_proposal):
        """토픽별 제안 목록 조회 테스트."""
        await proposal_repo.create(sample_proposal)

        # 같은 토픽에 또 다른 제안 생성
        from app.models.proposal import EnhancementProposal, ProposalPriority
        import uuid

        proposal2 = EnhancementProposal(
            id=str(uuid.uuid4()),
            topic_id=sample_proposal.topic_id,
            priority=ProposalPriority.MEDIUM,
            title="두 번째 제안",
            description="내용",
            current_content="현재",
            suggested_content="제안",
            reasoning="이유",
            reference_sources=[],
            estimated_effort=15,  # 분 단위 정수
            confidence=0.7,
            created_at=datetime.now(),
        )
        await proposal_repo.create(proposal2)

        # 토픽별 조회
        proposals = await proposal_repo.get_by_topic_id(sample_proposal.topic_id)

        assert len(proposals) == 2
        assert all(p.topic_id == sample_proposal.topic_id for p in proposals)

    @pytest.mark.asyncio
    async def test_get_by_topic_id_exclude_applied(self, proposal_repo, sample_proposal):
        """적용된 제안 제외 조회 테스트."""
        # 적용된 제안 생성
        from app.models.proposal import EnhancementProposal, ProposalPriority
        import uuid

        applied_proposal = EnhancementProposal(
            id=str(uuid.uuid4()),
            topic_id=sample_proposal.topic_id,
            priority=ProposalPriority.HIGH,
            title="적용된 제안",
            description="내용",
            current_content="현재",
            suggested_content="제안",
            reasoning="이유",
            reference_sources=[],
            estimated_effort=30,  # 분 단위 정수
            confidence=0.9,
            applied=True,  # 적용됨
            created_at=datetime.now(),
        )
        await proposal_repo.create(applied_proposal)
        await proposal_repo.create(sample_proposal)  # 적용되지 않음

        # 적용되지 않은 제안만 조회
        proposals = await proposal_repo.get_by_topic_id(
            sample_proposal.topic_id, include_applied=False
        )

        assert len(proposals) == 1
        assert proposals[0].applied is False

    @pytest.mark.asyncio
    async def test_mark_applied(self, proposal_repo, sample_proposal):
        """제안 적용 마크 테스트."""
        created = await proposal_repo.create(sample_proposal)

        updated = await proposal_repo.mark_applied(created.id)

        assert updated is not None
        assert updated.applied is True

    @pytest.mark.asyncio
    async def test_mark_rejected(self, proposal_repo, sample_proposal):
        """제안 거절 마크 테스트."""
        created = await proposal_repo.create(sample_proposal)

        updated = await proposal_repo.mark_rejected(created.id)

        assert updated is not None
        assert updated.rejected is True

    @pytest.mark.asyncio
    async def test_count_by_topic(self, proposal_repo, sample_proposal):
        """토픽별 제안 수 카운트 테스트."""
        await proposal_repo.create(sample_proposal)

        count = await proposal_repo.count_by_topic(sample_proposal.topic_id)
        assert count == 1

    @pytest.mark.asyncio
    async def test_create_many(self, proposal_repo):
        """여러 제안 일괄 생성 테스트."""
        from app.models.proposal import EnhancementProposal, ProposalPriority
        import uuid

        proposals = [
            EnhancementProposal(
                id=str(uuid.uuid4()),
                topic_id=f"topic_{i}",
                priority=ProposalPriority.HIGH,
                title=f"제안 {i}",
                description="내용",
                current_content="현재",
                suggested_content="제안",
                reasoning="이유",
                reference_sources=[],
                estimated_effort=30,  # 분 단위 정수
                confidence=0.9,
                created_at=datetime.now(),
            )
            for i in range(3)
        ]

        created = await proposal_repo.create_many(proposals)

        assert len(created) == 3
