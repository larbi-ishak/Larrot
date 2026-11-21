"""Deterministic ID generation: seedable resource and job IDs.

POST /admin/seed?a=42 seeds the generator so every subsequent ID is
reproducible - recorded scenarios replay with identical IDs (the Moto
seed-API pattern). Unseeded, IDs are cryptographically random as usual.
"""

import random
import threading
import uuid

_lock = threading.Lock()
_rng: random.Random | None = None
_seed_value: int | None = None


def seed(value: int) -> None:
    """Seed the ID generator (any hashable int)."""
    global _rng, _seed_value
    with _lock:
        _seed_value = value
        _rng = random.Random(value)


def unseed() -> None:
    """Return to cryptographically random IDs (also what reset does)."""
    global _rng, _seed_value
    with _lock:
        _rng = None
        _seed_value = None


def current_seed() -> int | None:
    return _seed_value


def _hex(n_chars: int) -> str:
    """n_chars of hex: seeded-RNG when seeded, urandom otherwise."""
    if _rng is not None:
        with _lock:
            return f"{_rng.getrandbits(n_chars * 4):0{n_chars}x}"
    return uuid.uuid4().hex[:n_chars]


def seeded_id() -> str:
    """Hyphenated UUID-shaped ID (what jobs.new_id returns)."""
    h = _hex(32)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def seeded_job_id() -> str:
    """32-char hex job ID."""
    return _hex(32)
