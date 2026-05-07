"""Configuration for the Hash Calculation service."""

import os
from dataclasses import dataclass


@dataclass
class HashCalcConfig:
    """Configuration for the Hash Calculation service."""

    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8078"))
