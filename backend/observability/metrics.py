from __future__ import annotations

from config import settings

# ---------------------------------------------------------------------------
# Attempt to import prometheus_client.  If the package is absent or Prometheus
# is disabled in settings, every metric becomes a silent no-op so the rest of
# the codebase can call inc_* unconditionally without import-guarding.
# ---------------------------------------------------------------------------

_prometheus_available = False
_Counter = None
_Gauge   = None

if settings.prometheus_enabled:
    try:
        from prometheus_client import Counter as _Counter, Gauge as _Gauge  # type: ignore[assignment]
        _prometheus_available = True
    except ImportError:
        pass


class PrometheusMetrics:
    def __init__(self) -> None:
        if _prometheus_available and _Counter is not None:
            self._debates_started = _Counter(
                "yojaka_debates_started_total",
                "Total number of debates started",
            )
            self._messages_streamed = _Counter(
                "yojaka_messages_streamed_total",
                "Total number of messages streamed to clients",
            )
            self._budget_exhausted = _Counter(
                "yojaka_budget_exhausted_total",
                "Total number of sessions that hit token budget limits",
            )
            self._provider_errors = _Counter(
                "yojaka_provider_errors_total",
                "Total number of provider-level errors",
                ["provider"],
            )
        else:
            self._debates_started   = None
            self._messages_streamed = None
            self._budget_exhausted  = None
            self._provider_errors   = None

    def inc_debates_started(self) -> None:
        if self._debates_started is not None:
            self._debates_started.inc()

    def inc_messages_streamed(self) -> None:
        if self._messages_streamed is not None:
            self._messages_streamed.inc()

    def inc_budget_exhausted(self) -> None:
        if self._budget_exhausted is not None:
            self._budget_exhausted.inc()

    def inc_provider_errors(self, provider: str) -> None:
        if self._provider_errors is not None:
            self._provider_errors.labels(provider=provider).inc()
