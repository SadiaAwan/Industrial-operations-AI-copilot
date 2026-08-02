"""Side-effect-free work-order draft proposal tool."""

import hashlib
import json

from app.domain.common import WorkOrderStatus
from app.domain.work_order import WorkOrderDraft
from app.schemas.tools import ToolResult, WorkOrderDraftRequest
from app.tools.runtime import ToolExecutor


class WorkOrderDraftTool:
    """Create a deterministic proposal; this tool never writes to a database."""

    name = "create_work_order_draft"

    def __init__(self, *, executor: ToolExecutor | None = None) -> None:
        self._executor = executor or ToolExecutor()

    async def __call__(
        self, request: WorkOrderDraftRequest
    ) -> ToolResult[WorkOrderDraft]:
        async def propose() -> WorkOrderDraft:
            canonical = json.dumps(
                request.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode()
            draft_id = f"DRAFT-{hashlib.sha256(canonical).hexdigest()[:16].upper()}"
            return WorkOrderDraft(
                draft_id=draft_id,
                machine_id=request.machine_id,
                title=request.title,
                description=request.description,
                priority=request.priority,
                proposed_checks=request.proposed_checks,
                status=WorkOrderStatus.PENDING_APPROVAL,
            )

        return await self._executor.execute(self.name, propose)
