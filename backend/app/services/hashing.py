from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_hex(payload: Any) -> str:
    """
    Deterministic SHA-256 for audit/evidence hashing.

    - JSON encoded with sorted keys so hash is stable across runs.
    - Returned as lowercase hex.
    """
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()



