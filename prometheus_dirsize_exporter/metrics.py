"""
Define the metrics we export
"""
from prometheus_client import Gauge

NAMESPACE = "dirsize"

TOTAL_SIZE = Gauge(
    "total_size_bytes", "Total Size of the Directory (in bytes)", namespace=NAMESPACE,
    labelnames=("directory",)
)

LATEST_MTIME = Gauge(
    "latest_mtime",
    "Newest modified file in the directory (as unix timestamp)",
    namespace=NAMESPACE,
    labelnames=("directory",)
)

OLDEST_MTIME = Gauge(
    "oldest_mtime",
    "Oldest modified file in the directory (as unix timestamp)",
    namespace=NAMESPACE,
    labelnames=("directory",)
)

ENTRIES_COUNT = Gauge(
    "entries_count",
    "Total number of entries (files, directories & links) in the directory",
    namespace=NAMESPACE,
    labelnames=("directory",)
)

PROCESSING_TIME = Gauge(
    "processing_time",
    "Time it took to process the directory (in seconds)",
    namespace=NAMESPACE,
    labelnames=("directory",)
)

LAST_UPDATED = Gauge(
    "last_updated_ns",
    "Last time this directory was processed (as unix timestamp)",
    namespace=NAMESPACE,
    labelnames=("directory",)
)