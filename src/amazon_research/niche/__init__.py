"""
Niche detection and scoring. Step 79 – detector; Step 84 – niche scoring v2.
"""
from .detector import detect_niches
from .scoring import score_niches

__all__ = ["detect_niches", "score_niches"]
