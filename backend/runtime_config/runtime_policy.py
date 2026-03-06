"""Runtime policy decisions for forced API mode."""

from __future__ import annotations

import os


def decide_force_api_generations(system: str, cuda_available: bool, vram_gb: int | None) -> bool:
    """Return whether API-only generation must be forced for this runtime."""
    # Environment override for power users:
    #   LTX_FORCE_API_GENERATIONS=1 → always force API
    #   LTX_FORCE_API_GENERATIONS=0 → always use local models
    override = os.environ.get("LTX_FORCE_API_GENERATIONS")
    if override is not None:
        return override == "1"

    if system == "Darwin":
        return True

    if system == "Windows":
        if not cuda_available:
            return True
        if vram_gb is None:
            return True
        return vram_gb < 31

    # Fail closed for non-target platforms unless explicitly relaxed.
    return True
