"""AquaWatch Pydantic Schemas Package."""

from app.schemas.health import HealthResponse
from app.schemas.zone import ZoneBase, ZoneCreate, ZoneResponse
from app.schemas.reading import (
    ReadingBase,
    ReadingCreate,
    ReadingResponse,
    DailyReadingResponse,
)
from app.schemas.alert import (
    AlertBase,
    AlertCreate,
    AlertResponse,
    AlertSeverity,
    AlertType,
)
from app.schemas.anomaly import (
    InjectedAnomalyBase,
    InjectedAnomalyCreate,
    InjectedAnomalyResponse,
    AnomalyType,
)
from app.schemas.summary import (
    TopZoneSummary,
    ZoneBudgetSummary,
    DashboardSummaryResponse,
)
from app.schemas.detection import DetectionRunResponse
from app.schemas.conservation import (
    BudgetStatus,
    RecommendationPriority,
    ZoneBudgetStatus,
    ConservationBudgetsResponse,
    ConservationRecommendation,
    ConservationTipsResponse,
    LeakSavingsEstimate,
    ConservationSavingsResponse,
)

from app.schemas.demo import (
    DemoInjectRequest,
    DemoTimelineStep,
    DemoTelemetryPoint,
    DemoSessionStatus,
    DemoInjectResponse,
    DemoResetResponse,
)

__all__ = [
    "HealthResponse",
    "ZoneBase",
    "ZoneCreate",
    "ZoneResponse",
    "ReadingBase",
    "ReadingCreate",
    "ReadingResponse",
    "DailyReadingResponse",
    "AlertBase",
    "AlertCreate",
    "AlertResponse",
    "AlertSeverity",
    "AlertType",
    "InjectedAnomalyBase",
    "InjectedAnomalyCreate",
    "InjectedAnomalyResponse",
    "AnomalyType",
    "TopZoneSummary",
    "ZoneBudgetSummary",
    "DashboardSummaryResponse",
    "DetectionRunResponse",
    "BudgetStatus",
    "RecommendationPriority",
    "ZoneBudgetStatus",
    "ConservationBudgetsResponse",
    "ConservationRecommendation",
    "ConservationTipsResponse",
    "LeakSavingsEstimate",
    "ConservationSavingsResponse",
    "DemoInjectRequest",
    "DemoTimelineStep",
    "DemoTelemetryPoint",
    "DemoSessionStatus",
    "DemoInjectResponse",
    "DemoResetResponse",
]
