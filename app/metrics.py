"""
Prometheus metrics collection for the Lyftr AI webhook API.
"""
from typing import Dict, List
from threading import Lock


class MetricsCollector:
    """Thread-safe metrics collection in Prometheus exposition format."""
    
    def __init__(self):
        self._lock = Lock()
        # HTTP requests by path and status
        self.http_requests: Dict[tuple, int] = {}
        # Webhook results
        self.webhook_requests: Dict[str, int] = {}
        # Request latency buckets (in milliseconds)
        self.latency_buckets = [10, 50, 100, 500, 1000, 5000]
        self.request_latencies: List[float] = []
    
    def record_http_request(self, path: str, status: int) -> None:
        """Record an HTTP request metric."""
        with self._lock:
            key = (path, status)
            self.http_requests[key] = self.http_requests.get(key, 0) + 1
    
    def record_webhook_result(self, result: str) -> None:
        """Record a webhook processing result."""
        with self._lock:
            self.webhook_requests[result] = self.webhook_requests.get(result, 0) + 1
    
    def record_latency(self, latency_ms: float) -> None:
        """Record request latency."""
        with self._lock:
            self.request_latencies.append(latency_ms)
    
    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus exposition format metrics."""
        with self._lock:
            lines = []
            
            # HTTP requests total
            lines.append("# HELP http_requests_total Total HTTP requests by path and status")
            lines.append("# TYPE http_requests_total counter")
            for (path, status), count in sorted(self.http_requests.items()):
                lines.append(f'http_requests_total{{path="{path}",status="{status}"}} {count}')
            
            lines.append("")
            
            # Webhook requests total
            lines.append("# HELP webhook_requests_total Total webhook requests by result")
            lines.append("# TYPE webhook_requests_total counter")
            for result, count in sorted(self.webhook_requests.items()):
                lines.append(f'webhook_requests_total{{result="{result}"}} {count}')
            
            lines.append("")
            
            # Request latency histograms
            lines.append("# HELP request_latency_ms Request latency in milliseconds")
            lines.append("# TYPE request_latency_ms histogram")
            
            total_latency = sum(self.request_latencies)
            count = len(self.request_latencies)
            
            for bucket in self.latency_buckets:
                bucket_count = sum(1 for l in self.request_latencies if l <= bucket)
                lines.append(f"request_latency_ms_bucket{{le=\"{bucket}\"}} {bucket_count}")
            
            lines.append(f'request_latency_ms_bucket{{le="+Inf"}} {count}')
            lines.append(f"request_latency_ms_sum {total_latency}")
            lines.append(f"request_latency_ms_count {count}")
            
            return "\n".join(lines) + "\n"


# Global metrics instance
metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    return metrics
