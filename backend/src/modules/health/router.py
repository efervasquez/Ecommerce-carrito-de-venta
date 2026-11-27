from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.modules.health.repository import HealthRepository
from src.modules.health.schemas import HealthResponse
from src.modules.health.service import HealthService

router = APIRouter(prefix="/health", tags=["Health"])


def get_health_service() -> HealthService:
    return HealthService(HealthRepository())


@router.get(
    "",
    response_model=HealthResponse,
    responses={
        200: {"model": HealthResponse, "description": "Todos los servicios operativos"},
        503: {"model": HealthResponse, "description": "Uno o mas servicios no disponibles"},
    },
)
@router.get(
    "/",
    response_model=HealthResponse,
    include_in_schema=False,
)
async def check_health(
    service: HealthService = Depends(get_health_service),
) -> JSONResponse:
    status_code, health_data = await service.get_health_status()
    return JSONResponse(status_code=status_code, content=health_data.model_dump())
