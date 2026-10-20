from fastapi import APIRouter

from app.dependencies import OverviewServiceDependency
from app.schemas import OverviewRead

router = APIRouter(prefix="/api/v1", tags=["overview"])


@router.get("/overview", response_model=OverviewRead)
def overview(service: OverviewServiceDependency) -> OverviewRead:
    return service.get_overview()
