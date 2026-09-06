"""ETA accuracy, measured rather than asserted."""

from fastapi import APIRouter, Depends

from app.api.deps import get_history_service
from app.schemas.metrics import EtaAccuracyResponse
from app.services.history_service import HistoryService

router = APIRouter(tags=["metrics"])


@router.get("/metrics/eta", response_model=EtaAccuracyResponse)
def eta_accuracy(
    history: HistoryService = Depends(get_history_service),
) -> EtaAccuracyResponse:
    """How far the ETA engine has been off, against recorded arrivals.

    Measured against the simulation, which is stated in the response so the
    number can never be quoted as real-world accuracy.
    """
    return EtaAccuracyResponse.from_domain(history.accuracy())
