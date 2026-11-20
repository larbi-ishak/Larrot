"""Quirk profiles: per-region behavioral dialects (see docs)7)."""

import enum


class Profile(enum.Enum):
    PUBLIC = "public"
    HCS = "hcs"

    @classmethod
    def parse(cls, s: str) -> "Profile":
        try:
            return cls(s.strip().lower())
        except ValueError:
            return cls.PUBLIC
