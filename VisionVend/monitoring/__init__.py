"""
VisionVend Monitoring Package

This package provides comprehensive monitoring, metrics collection, health checks,
and alerting capabilities for the VisionVend system. It integrates with Prometheus,
Grafana, and other monitoring platforms to provide real-time visibility into system
performance and health.

Components:
- Prometheus metrics collectors
- Health check utilities
- Alerting integration
- Tracing and distributed system monitoring
- Dashboard templates

Usage:
    from VisionVend.monitoring import setup_monitoring, register_metrics
    
    # Initialize monitoring for a FastAPI app
    setup_monitoring(app)
    
    # Register custom metrics
    transaction_counter = register_metrics.counter(
        "visionvend_transactions_total",
        "Total number of transactions processed"
    )
    
    # Record metrics
    transaction_counter.inc()
"""

import logging
import os
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

try:
    import prometheus_client
    from prometheus_client import Counter, Gauge, Histogram, Summary
    from prometheus_client import multiprocess, CollectorRegistry
    from prometheus_client.exposition import generate_latest, CONTENT_TYPE_LATEST
except ImportError:
    prometheus_client = None

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from starlette.middleware.base import BaseHTTPMiddleware
except ImportError:
    FastAPI = None
    Request = None
    Response = None
    BaseHTTPMiddleware = None

try:
    import psutil
except ImportError:
    psutil = None


# Constants
DEFAULT_METRICS_PATH = "/metrics"
DEFAULT_HEALTH_PATH = "/health"
DEFAULT_BUCKETS = (0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)


class HealthStatus(str, Enum):
    """Health status enum for consistent reporting"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


# Registry setup
def create_registry(multiprocess_mode=False):
    """
    Create a Prometheus registry
    
    Args:
        multiprocess_mode: Whether to enable multiprocess mode for Prometheus
        
    Returns:
        A Prometheus registry
    """
    if prometheus_client is None:
        raise ImportError("prometheus_client is required for metrics collection")
        
    if multiprocess_mode:
        # Enable multiprocess mode for Prometheus
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = prometheus_client.REGISTRY
        
    return registry


# Core metrics
class MetricsRegistry:
    """Registry for VisionVend metrics"""
    
    def __init__(self, registry=None, prefix="visionvend"):
        """
        Initialize metrics registry
        
        Args:
            registry: Prometheus registry to use
            prefix: Prefix for all metrics
        """
        self.registry = registry or create_registry()
        self.prefix = prefix
        self.metrics = {}
        
        # Initialize default metrics
        self._setup_default_metrics()
        
    def _setup_default_metrics(self):
        """Set up default metrics for VisionVend"""
        # System metrics
        if psutil:
            self.gauge("system_cpu_usage", "CPU usage percentage")
            self.gauge("system_memory_usage", "Memory usage percentage")
            self.gauge("system_disk_usage", "Disk usage percentage")
            
        # Application metrics
        self.counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
        self.histogram("http_request_duration_seconds", "HTTP request duration in seconds",
                      ["method", "endpoint"], buckets=DEFAULT_BUCKETS)
        self.counter("errors_total", "Total errors", ["type", "component"])
        
        # Business metrics
        self.counter("transactions_total", "Total transactions")
        self.counter("transaction_items_total", "Total items sold")
        self.gauge("transaction_value", "Transaction value in dollars")
        self.counter("unlock_requests_total", "Total unlock requests")
        self.counter("payment_requests_total", "Total payment requests")
        
        # MQTT metrics
        self.counter("mqtt_messages_published_total", "Total MQTT messages published", ["topic"])
        self.counter("mqtt_messages_received_total", "Total MQTT messages received", ["topic"])
        self.counter("mqtt_errors_total", "Total MQTT errors", ["type"])
        self.gauge("mqtt_connected", "MQTT connection status (1=connected, 0=disconnected)")
        
        # Hardware metrics
        self.gauge("door_state", "Door state (1=open, 0=closed)")
        self.gauge("temperature", "Temperature in Celsius")
        self.gauge("humidity", "Humidity percentage")
        
    def counter(self, name, description, labels=None):
        """
        Create or get a counter metric
        
        Args:
            name: Metric name
            description: Metric description
            labels: List of label names
            
        Returns:
            Prometheus Counter
        """
        full_name = f"{self.prefix}_{name}"
        if full_name not in self.metrics:
            self.metrics[full_name] = Counter(full_name, description, labels or [], registry=self.registry)
        return self.metrics[full_name]
        
    def gauge(self, name, description, labels=None):
        """
        Create or get a gauge metric
        
        Args:
            name: Metric name
            description: Metric description
            labels: List of label names
            
        Returns:
            Prometheus Gauge
        """
        full_name = f"{self.prefix}_{name}"
        if full_name not in self.metrics:
            self.metrics[full_name] = Gauge(full_name, description, labels or [], registry=self.registry)
        return self.metrics[full_name]
        
    def histogram(self, name, description, labels=None, buckets=DEFAULT_BUCKETS):
        """
        Create or get a histogram metric
        
        Args:
            name: Metric name
            description: Metric description
            labels: List of label names
            buckets: Histogram buckets
            
        Returns:
            Prometheus Histogram
        """
        full_name = f"{self.prefix}_{name}"
        if full_name not in self.metrics:
            self.metrics[full_name] = Histogram(
                full_name, description, labels or [], buckets=buckets, registry=self.registry
            )
        return self.metrics[full_name]
        
    def summary(self, name, description, labels=None):
        """
        Create or get a summary metric
        
        Args:
            name: Metric name
            description: Metric description
            labels: List of label names
            
        Returns:
            Prometheus Summary
        """
        full_name = f"{self.prefix}_{name}"
        if full_name not in self.metrics:
            self.metrics[full_name] = Summary(full_name, description, labels or [], registry=self.registry)
        return self.metrics[full_name]
        
    def get_metric(self, name):
        """
        Get a metric by name
        
        Args:
            name: Metric name (with or without prefix)
            
        Returns:
            Prometheus metric
        """
        if name in self.metrics:
            return self.metrics[name]
            
        full_name = f"{self.prefix}_{name}"
        if full_name in self.metrics:
            return self.metrics[full_name]
            
        raise KeyError(f"Metric {name} not found")


# System metrics collection
class SystemMetricsCollector:
    """Collector for system metrics"""
    
    def __init__(self, registry, collection_interval=15):
        """
        Initialize system metrics collector
        
        Args:
            registry: MetricsRegistry instance
            collection_interval: Interval in seconds for collecting metrics
        """
        self.registry = registry
        self.collection_interval = collection_interval
        self.last_collection = 0
        
    def collect_metrics(self, force=False):
        """
        Collect system metrics
        
        Args:
            force: Whether to force collection regardless of interval
            
        Returns:
            Dict of collected metrics
        """
        now = time.time()
        if not force and now - self.last_collection < self.collection_interval:
            return
            
        self.last_collection = now
        
        if not psutil:
            return
            
        # Collect CPU metrics
        cpu_usage = psutil.cpu_percent(interval=0.1)
        self.registry.gauge("system_cpu_usage").set(cpu_usage)
        
        # Collect memory metrics
        memory = psutil.virtual_memory()
        self.registry.gauge("system_memory_usage").set(memory.percent)
        
        # Collect disk metrics
        disk = psutil.disk_usage('/')
        self.registry.gauge("system_disk_usage").set(disk.percent)
        
        # Collect network metrics
        net_io = psutil.net_io_counters()
        self.registry.gauge("system_network_bytes_sent").set(net_io.bytes_sent)
        self.registry.gauge("system_network_bytes_recv").set(net_io.bytes_recv)
        
        return {
            "cpu_usage": cpu_usage,
            "memory_usage": memory.percent,
            "disk_usage": disk.percent,
            "network_bytes_sent": net_io.bytes_sent,
            "network_bytes_recv": net_io.bytes_recv
        }


# Health checks
class HealthCheck:
    """Health check registry and runner"""
    
    def __init__(self):
        """Initialize health check registry"""
        self.checks = {}
        
    def register(self, name, check_func, timeout=5.0):
        """
        Register a health check
        
        Args:
            name: Check name
            check_func: Check function that returns (status, details)
            timeout: Timeout in seconds
            
        Returns:
            Self for chaining
        """
        self.checks[name] = {
            "func": check_func,
            "timeout": timeout
        }
        return self
        
    async def run_checks(self, include=None, exclude=None):
        """
        Run health checks
        
        Args:
            include: List of check names to include (None for all)
            exclude: List of check names to exclude
            
        Returns:
            Dict with health check results
        """
        results = {
            "status": HealthStatus.HEALTHY,
            "timestamp": time.time(),
            "checks": {}
        }
        
        checks_to_run = set(self.checks.keys())
        
        if include:
            checks_to_run = checks_to_run.intersection(include)
            
        if exclude:
            checks_to_run = checks_to_run.difference(exclude)
            
        for name in checks_to_run:
            check = self.checks[name]
            try:
                import asyncio
                from concurrent.futures import TimeoutError
                
                # Run the check with a timeout
                status, details = await asyncio.wait_for(
                    self._run_check(check["func"]),
                    timeout=check["timeout"]
                )
                
                results["checks"][name] = {
                    "status": status,
                    "details": details
                }
                
                # Update overall status
                if status == HealthStatus.UNHEALTHY and results["status"] != HealthStatus.UNHEALTHY:
                    results["status"] = HealthStatus.UNHEALTHY
                elif status == HealthStatus.DEGRADED and results["status"] == HealthStatus.HEALTHY:
                    results["status"] = HealthStatus.DEGRADED
                    
            except TimeoutError:
                results["checks"][name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "details": {"error": "Health check timed out"}
                }
                results["status"] = HealthStatus.UNHEALTHY
                
            except Exception as e:
                results["checks"][name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "details": {"error": str(e)}
                }
                results["status"] = HealthStatus.UNHEALTHY
                
        return results
        
    async def _run_check(self, check_func):
        """
        Run a health check function
        
        Args:
            check_func: Check function
            
        Returns:
            (status, details) tuple
        """
        import asyncio
        import inspect
        
        if inspect.iscoroutinefunction(check_func):
            return await check_func()
        else:
            return await asyncio.to_thread(check_func)


# FastAPI integration
class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting Prometheus metrics for FastAPI"""
    
    def __init__(self, app, registry):
        """
        Initialize Prometheus middleware
        
        Args:
            app: FastAPI app
            registry: MetricsRegistry instance
        """
        super().__init__(app)
        self.registry = registry
        
    async def dispatch(self, request, call_next):
        """
        Process a request and record metrics
        
        Args:
            request: FastAPI request
            call_next: Next middleware
            
        Returns:
            Response
        """
        start_time = time.time()
        method = request.method
        path = request.url.path
        
        # Skip metrics endpoint to avoid circular metrics
        if path == DEFAULT_METRICS_PATH:
            return await call_next(request)
            
        try:
            response = await call_next(request)
            status = response.status_code
            
            # Record request count
            self.registry.counter("http_requests_total").labels(
                method=method, endpoint=path, status=str(status)
            ).inc()
            
            # Record request duration
            self.registry.histogram("http_request_duration_seconds").labels(
                method=method, endpoint=path
            ).observe(time.time() - start_time)
            
            return response
            
        except Exception as e:
            # Record error
            self.registry.counter("errors_total").labels(
                type="http_request", component="middleware"
            ).inc()
            
            # Re-raise the exception
            raise


def setup_monitoring(app, registry=None, metrics_path=DEFAULT_METRICS_PATH, 
                    health_path=DEFAULT_HEALTH_PATH, health_check=None):
    """
    Set up monitoring for a FastAPI app
    
    Args:
        app: FastAPI app
        registry: Optional MetricsRegistry instance
        metrics_path: Path for metrics endpoint
        health_path: Path for health endpoint
        health_check: Optional HealthCheck instance
        
    Returns:
        Tuple of (registry, health_check)
    """
    if FastAPI is None:
        raise ImportError("fastapi is required for FastAPI integration")
        
    # Create registry if not provided
    if registry is None:
        registry = MetricsRegistry()
        
    # Create health check if not provided
    if health_check is None:
        health_check = HealthCheck()
        
    # Add Prometheus middleware
    app.add_middleware(PrometheusMiddleware, registry=registry)
    
    # Add metrics endpoint
    @app.get(metrics_path)
    async def metrics():
        if prometheus_client is None:
            return Response(
                content="prometheus_client not installed",
                status_code=500,
                media_type="text/plain"
            )
            
        # Collect system metrics
        system_collector = SystemMetricsCollector(registry)
        system_collector.collect_metrics()
        
        # Generate metrics
        return Response(
            content=generate_latest(registry.registry),
            media_type=CONTENT_TYPE_LATEST
        )
        
    # Add health endpoint
    @app.get(health_path)
    async def health():
        return await health_check.run_checks()
        
    return registry, health_check


# Default metrics registry
default_registry = MetricsRegistry() if prometheus_client else None

# Default health check
default_health_check = HealthCheck()

# Expose key components
__all__ = [
    "setup_monitoring",
    "MetricsRegistry",
    "HealthCheck",
    "HealthStatus",
    "SystemMetricsCollector",
    "default_registry",
    "default_health_check",
]
