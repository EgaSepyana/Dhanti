import io
import json
import uuid

import pandas as pd
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.models.dataset import Dataset
from app.models.document import Document
from app.models.file import File
from app.providers.manager import get_provider_manager
from app.services import dataset_service, document_service

settings = get_settings()


def validate_upload(filename: str, size_bytes: int) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in settings.allowed_file_types_list:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(settings.allowed_file_types_list)}",
        )
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {settings.max_file_size_mb}MB",
        )
    return ext


async def upload_bytes(path: str, content: bytes, content_type: str) -> None:
    await get_provider_manager().get_storage().upload(path, content, content_type)


async def download_bytes(path: str) -> bytes:
    return await get_provider_manager().get_storage().download(path)


CONTENT_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "pdf": "application/pdf",
}


async def process_file(file_id: uuid.UUID, content: bytes, ext: str) -> None:
    """Runs as a background task after upload: parses the file and creates the
    dataset/document row, updating file.status along the way."""
    async with async_session_factory() as db:
        file_row = await db.get(File, file_id)
        if file_row is None:
            return

        try:
            file_row.status = "parsing"
            await db.commit()

            if ext in ("csv", "xlsx", "xls"):
                await _process_dataset(db, file_row, content, ext)
            elif ext == "pdf":
                await _process_document(db, file_row, content)

            file_row.status = "parsed"
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            file_row.status = "error"
            file_row.metadata_ = {**file_row.metadata_, "error": str(exc)}
            await db.commit()


async def _process_dataset(db, file_row: File, content: bytes, ext: str) -> None:
    if ext == "csv":
        try:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(content), encoding="latin-1")
    else:
        df = pd.read_excel(io.BytesIO(content))

    columns = dataset_service.infer_schema(df)
    profile = dataset_service.profile_dataset(df, columns)

    data_path = f"{file_row.workspace_id}/{file_row.id}/data.parquet"
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    await upload_bytes(data_path, buffer.getvalue(), "application/octet-stream")

    dataset = Dataset(
        workspace_id=file_row.workspace_id,
        file_id=file_row.id,
        name=file_row.name,
        columns=columns,
        row_count=len(df),
        profile=profile,
        data_path=data_path,
    )
    db.add(dataset)


async def _process_document(db, file_row: File, content: bytes) -> None:
    page_count, structure, chunks = document_service.parse_pdf(content)

    document = Document(
        workspace_id=file_row.workspace_id,
        file_id=file_row.id,
        name=file_row.name,
        page_count=page_count,
        structure=structure,
        chunks=chunks,
    )
    db.add(document)


async def read_dataset_sample(data_path: str, limit: int = 100) -> list[dict]:
    content = await download_bytes(data_path)
    df = pd.read_parquet(io.BytesIO(content))
    # round-trip through pandas' JSON encoder so numpy/NaT/NaN become JSON-safe primitives
    return json.loads(df.head(limit).to_json(orient="records", date_format="iso"))
