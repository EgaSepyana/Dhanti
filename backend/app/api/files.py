import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.file import File, FileRead, FileUploadResponse
from app.services import file_service
from app.services.workspace_service import get_workspace

router = APIRouter(prefix="/api/workspaces/{workspace_id}/files", tags=["files"])


@router.post("", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    workspace_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    workspace = await get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    content = await file.read()
    ext = file_service.validate_upload(file.filename, len(content))

    file_id = uuid.uuid4()
    storage_path = f"{workspace_id}/{file_id}/{file.filename}"

    file_row = File(
        id=file_id,
        workspace_id=workspace_id,
        name=file.filename,
        type=ext,
        size_bytes=len(content),
        storage_path=storage_path,
        status="uploaded",
    )
    db.add(file_row)
    await db.commit()
    await db.refresh(file_row)

    await file_service.upload_bytes(
        storage_path, content, file_service.CONTENT_TYPES.get(ext, "application/octet-stream")
    )

    background_tasks.add_task(file_service.process_file, file_row.id, content, ext)

    return FileUploadResponse(file_id=file_row.id, status="parsing")


@router.get("", response_model=list[FileRead])
async def list_files(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(File).where(File.workspace_id == workspace_id))
    return result.scalars().all()
