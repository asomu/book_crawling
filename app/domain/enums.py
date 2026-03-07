from __future__ import annotations

from enum import Enum


class Site(str, Enum):
    YES24 = "yes24"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PARTIAL_SUCCESS = "partial_success"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobItemStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class AssetKind(str, Enum):
    COVER = "cover"
    Y1000 = "y1000"
    COUPANG = "coupang"
    NAVER = "naver"
    DETAIL = "detail"


class EventLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
