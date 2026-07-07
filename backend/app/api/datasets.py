import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.dataset import Dataset, DatasetDetail, DatasetRead
from app.services import file_service

router = APIRouter(prefix="/api/workspaces/{workspace_id}/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetRead])
async def list_datasets(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).where(Dataset.workspace_id == workspace_id))
    return result.scalars().all()


@router.get("/{dataset_id}", response_model=DatasetDetail)
async def get_dataset(workspace_id: uuid.UUID, dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None or dataset.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    sample_rows = await file_service.read_dataset_sample(dataset.data_path) if dataset.data_path else []

    return DatasetDetail(**DatasetRead.model_validate(dataset).model_dump(), sample_rows=sample_rows)
