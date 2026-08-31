from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional


def compute_half_life_days(attempts: int) -> float:
    """Compute retention half-life based on number of spaced repetition attempts."""
    safe_attempts = max(1, attempts)
    return float(7.0 * min(safe_attempts, 3))


def compute_effective_mastery(
    mastery: float,
    last_assessed_at: Optional[datetime],
    half_life_days: float = 7.0,
    current_time: Optional[datetime] = None
) -> float:
    """Compute decayed effective mastery score based on elapsed time."""
    if last_assessed_at is None:
        return float(mastery)
    
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    if last_assessed_at.tzinfo is None:
        last_assessed_at = last_assessed_at.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    
    days_elapsed = max(0.0, (current_time - last_assessed_at).total_seconds() / 86400.0)
    effective = float(mastery) * (0.5 ** (days_elapsed / max(1.0, half_life_days)))
    return round(max(0.0, min(1.0, effective)), 4)


def compute_updated_mastery(old_mastery: float, new_score: float, attempts: int = 1) -> float:
    """Compute updated mastery with 40% prior weight and 60% new score weight."""
    updated = round(0.4 * float(old_mastery) + 0.6 * float(new_score), 4)
    return max(0.0, min(1.0, updated))


def update_mastery_on_assessment(
    old_mastery: float,
    new_score: float,
    attempts: int,
    assessed_at: Optional[datetime] = None
) -> Dict[str, Any]:
    """Calculate updated mastery, attempts, half-life, and next review date."""
    if assessed_at is None:
        assessed_at = datetime.now(timezone.utc)
    if assessed_at.tzinfo is None:
        assessed_at = assessed_at.replace(tzinfo=timezone.utc)

    updated_mastery = compute_updated_mastery(old_mastery, new_score, attempts)
    updated_attempts = attempts + 1
    updated_half_life = compute_half_life_days(updated_attempts)
    next_review_at = assessed_at + timedelta(days=updated_half_life)
    
    return {
        "mastery": updated_mastery,
        "attempts": updated_attempts,
        "halfLifeDays": updated_half_life,
        "lastAssessedAt": assessed_at,
        "nextReviewAt": next_review_at,
    }


def needs_review(
    effective_mastery: float,
    next_review_at: Optional[datetime],
    current_time: Optional[datetime] = None
) -> bool:
    """Check if concept warrants a targeted review drill."""
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    if effective_mastery < 0.50:
        return True
    
    if next_review_at is not None:
        if next_review_at.tzinfo is None:
            next_review_at = next_review_at.replace(tzinfo=timezone.utc)
        if next_review_at <= current_time:
            return True
            
    return False
