"""Prometheus metrics endpoint."""
from fastapi import APIRouter, Response
from prometheus_client import (
    Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST,
)

router = APIRouter(tags=["Metrics"])

# Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
)


@router.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
