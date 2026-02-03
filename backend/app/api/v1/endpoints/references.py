"""Reference management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import os

from app.api.deps import get_db, get_current_request_id
from app.core.api import ApiResponse
from app.core.errors import ErrorCode
from app.models.reference import (
    ReferenceCreate,
    ReferenceIndexRequest,
    ReferenceIndexResponse,
    ReferenceDocument,
    ReferenceSourceType,
)
from app.services.parser.pdf_parser import PDFParser
from app.services.matching.matcher import get_matching_service
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.repositories.reference import ReferenceRepository

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/index", response_model=ApiResponse)
async def index_references(
    request: ReferenceIndexRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """
    Index reference documents from files or URLs.

    This will parse documents, generate embeddings, and store in vector database.
    """
    try:
        import time
        start_time = time.time()

        matcher = get_matching_service()
        parser = PDFParser()

        indexed_count = 0
        failed_count = 0
        failed_paths = []

        for path in request.source_paths:
            try:
                # Parse document
                if request.source_type == ReferenceSourceType.PDF_BOOK:
                    parsed = parser.parse(path)
                else:
                    # For now, only PDF is supported
                    failed_count += 1
                    failed_paths.append(path)
                    continue

                # Create reference document
                ref = ReferenceDocument(
                    id=str(uuid.uuid4()),
                    source_type=request.source_type,
                    title=parsed["metadata"]["title"],
                    content=parsed["content"],
                    file_path=parsed["file_path"],
                    domain=request.domain or "general",
                    trust_score=1.0,
                )

                # Generate embedding
                from app.services.matching.embedding import get_embedding_service
                embedding_service = get_embedding_service()
                ref.embedding = embedding_service.encode(ref.content).tolist()

                # Index in vector database
                await matcher.index_references([ref])

                # Store in database
                ref_repo = ReferenceRepository(db)
                await ref_repo.create_with_embedding(
                    ReferenceCreate(
                        source_type=ref.source_type,
                        title=ref.title,
                        content=ref.content,
                        url=ref.url,
                        file_path=ref.file_path,
                        domain=ref.domain,
                        trust_score=ref.trust_score,
                    ),
                    ref.embedding,
                )
                indexed_count += 1

            except Exception as e:
                logger.error("reference_index_failed", path=path, error=str(e))
                failed_count += 1
                failed_paths.append(path)

        duration = time.time() - start_time

        logger.info(
            "references_indexed",
            indexed=indexed_count,
            failed=failed_count,
            duration=duration,
        )

        response_data = ReferenceIndexResponse(
            indexed_count=indexed_count,
            failed_count=failed_count,
            failed_paths=failed_paths,
            duration_seconds=duration,
        )

        return ApiResponse.success_response(
            data=response_data,
            request_id=request_id,
        )
    except Exception as e:
        logger.error("index_references_failed", error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="참고 문헌 인덱싱 실패",
            request_id=request_id,
        )


@router.post("/upload", response_model=ApiResponse)
async def upload_reference(
    file: UploadFile = File(...),
    domain: str = "general",
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """
    Upload a reference document (PDF file).

    The file will be parsed, embedded, and indexed automatically.
    """
    try:
        if not file.filename.endswith(".pdf"):
            return ApiResponse.error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message="PDF 파일만 지원됩니다",
                details={"filename": file.filename},
                request_id=request_id,
            )

        # Save uploaded file
        upload_dir = "./data/uploads"
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, file.filename)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Parse and index
        matcher = get_matching_service()
        parser = PDFParser()

        parsed = parser.parse(file_path)

        ref = ReferenceDocument(
            id=str(uuid.uuid4()),
            source_type=ReferenceSourceType.PDF_BOOK,
            title=parsed["metadata"]["title"],
            content=parsed["content"],
            file_path=file_path,
            domain=domain,
            trust_score=1.0,
        )

        from app.services.matching.embedding import get_embedding_service
        embedding_service = get_embedding_service()
        ref.embedding = embedding_service.encode(ref.content).tolist()

        await matcher.index_references([ref])

        # Store in database
        ref_repo = ReferenceRepository(db)
        await ref_repo.create_with_embedding(
            ReferenceCreate(
                source_type=ref.source_type,
                title=ref.title,
                content=ref.content,
                url=ref.url,
                file_path=ref.file_path,
                domain=ref.domain,
                trust_score=ref.trust_score,
            ),
            ref.embedding,
        )

        logger.info("reference_uploaded", file_name=file.filename, ref_id=ref.id)

        return ApiResponse.success_response(
            data={
                "success": True,
                "reference_id": ref.id,
                "message": "Reference uploaded and indexed"
            },
            request_id=request_id,
        )

    except Exception as e:
        logger.error("reference_upload_failed", file_name=file.filename, error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"파일 처리 실패: {str(e)}",
            details={"filename": file.filename},
            request_id=request_id,
        )


@router.get("/", response_model=ApiResponse)
async def list_references(
    domain: str | None = None,
    source_type: ReferenceSourceType | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """List indexed reference documents."""
    try:
        ref_repo = ReferenceRepository(db)

        if domain:
            references = await ref_repo.list_by_domain(domain, source_type, skip, limit)
        else:
            references = await ref_repo.list_all(source_type, skip, limit)

        return ApiResponse.success_response(
            data={
                "references": references,
                "total": len(references),
                "domain": domain,
                "source_type": source_type.value if source_type else None,
            },
            request_id=request_id,
        )
    except Exception as e:
        logger.error("list_references_failed", error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="참고 문헌 목록 조회 실패",
            request_id=request_id,
        )


@router.post("/reset", response_model=ApiResponse)
async def reset_references(
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """
    Reset all reference documents.

    This will clear the vector database. Use with caution!
    """
    try:
        matcher = get_matching_service()
        await matcher.reset_collection()

        logger.info("references_reset")

        return ApiResponse.success_response(
            data={"success": True, "message": "All references have been reset"},
            request_id=request_id,
        )
    except Exception as e:
        logger.error("reset_references_failed", error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="참고 문헌 초기화 실패",
            request_id=request_id,
        )
