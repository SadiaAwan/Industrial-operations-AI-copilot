"""Prometheus metrics endpoint; restrict this route at the deployment boundary."""

from fastapi import APIRouter, Request, Response

from app.observability.metrics import ObservabilityMetrics

router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> Response:
    collector: ObservabilityMetrics = request.app.state.metrics
    return Response(
        content=collector.registry.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
