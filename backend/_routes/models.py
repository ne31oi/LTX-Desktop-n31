"""Route handlers for /api/models, /api/models/status, /api/models/download/*."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from api_types import (
    CustomModelsListResponse,
    DownloadProgressResponse,
    ModelDownloadRequest,
    ModelDownloadStartResponse,
    ModelInfo,
    ModelsStatusResponse,
    ModelSelectionRequest,
    StatusResponse,
    TextEncoderDownloadResponse,
)
from state.app_settings import UpdateSettingsRequest
from _routes._errors import HTTPError
from state import get_state_service
from app_handler import AppHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=list[ModelInfo])
def route_models_list(handler: AppHandler = Depends(get_state_service)) -> list[ModelInfo]:
    return handler.models.get_models_list()


@router.get("/models/status", response_model=ModelsStatusResponse)
def route_models_status(handler: AppHandler = Depends(get_state_service)) -> ModelsStatusResponse:
    return handler.models.get_models_status()


@router.get("/models/custom", response_model=CustomModelsListResponse)
def route_models_custom(handler: AppHandler = Depends(get_state_service)) -> CustomModelsListResponse:
    models = handler.models.list_custom_models()
    return CustomModelsListResponse(models=models, base_dir=str(handler.config.models_dir))


@router.get("/models/download/progress", response_model=DownloadProgressResponse)
def route_download_progress(handler: AppHandler = Depends(get_state_service)) -> DownloadProgressResponse:
    return handler.downloads.get_download_progress()


@router.post("/models/download", response_model=ModelDownloadStartResponse)
def route_model_download(
    req: ModelDownloadRequest,
    handler: AppHandler = Depends(get_state_service),
) -> ModelDownloadStartResponse:
    if handler.downloads.is_download_running():
        raise HTTPError(409, "Download already in progress")

    settings = handler.settings.get_settings_snapshot()
    skip_text_encoder = req.skipTextEncoder
    if settings.ltx_api_key and not settings.use_local_text_encoder:
        skip_text_encoder = True

    if handler.downloads.start_model_download(skip_text_encoder=skip_text_encoder):
        return ModelDownloadStartResponse(
            status="started",
            message="Model download started",
            skippingTextEncoder=skip_text_encoder,
        )

    raise HTTPError(400, "Failed to start download")


@router.post("/text-encoder/download", response_model=TextEncoderDownloadResponse)
def route_text_encoder_download(handler: AppHandler = Depends(get_state_service)) -> TextEncoderDownloadResponse:
    if handler.downloads.is_download_running():
        raise HTTPError(409, "Download already in progress")

    files = handler.models.refresh_available_files()
    if files["text_encoder"] is not None:
        return TextEncoderDownloadResponse(status="already_downloaded", message="Text encoder already downloaded")

    if handler.downloads.start_text_encoder_download():
        return TextEncoderDownloadResponse(status="started", message="Text encoder download started")

    raise HTTPError(400, "Failed to start download")


@router.post("/models/selection", response_model=StatusResponse)
def route_model_selection(
    req: ModelSelectionRequest,
    handler: AppHandler = Depends(get_state_service),
) -> StatusResponse:
    # Persist selection in app settings;
    # concrete use by pipelines can be added in a future change.
    patch = UpdateSettingsRequest(
        selected_base_model=req.baseModelId,
        selected_lora=req.loraId,
    )
    handler.settings.update_settings(patch)
    return StatusResponse(status="ok")


@router.post("/models/gguf/download", response_model=StatusResponse)
def route_gguf_download(handler: AppHandler = Depends(get_state_service)) -> StatusResponse:
    files = handler.models.refresh_available_files()
    if files.get("gguf_q4") is not None:
        return StatusResponse(status="already_downloaded")

    if handler.downloads.start_gguf_q4_download():
        return StatusResponse(status="started")

    raise HTTPError(400, "Failed to start GGUF download")
