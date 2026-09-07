"""Persistence.

Append-only history of what the ETA engine predicted and what actually
happened. Nothing the live map draws depends on it.
"""

from app.db.models import Arrival, Base, Meta, Prediction
from app.db.session import Database

__all__ = ["Arrival", "Base", "Database", "Meta", "Prediction"]
