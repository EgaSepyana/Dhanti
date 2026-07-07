from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.artifacts import router as artifacts_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.datasets import router as datasets_router
from app.api.documents import router as documents_router
from app.api.files import router as files_router
from app.api.health import router as health_router
from app.api.widgets import router as widgets_router
from app.api.workspaces import router as workspaces_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.debug)

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(workspaces_router)
app.include_router(files_router)
app.include_router(datasets_router)
app.include_router(documents_router)
app.include_router(conversations_router)
app.include_router(chat_router)
app.include_router(artifacts_router)
app.include_router(widgets_router)
