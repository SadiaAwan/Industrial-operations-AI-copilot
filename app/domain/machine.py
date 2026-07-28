"""Machine domain contract."""

from app.domain.common import DomainModel, MachineId, MachineStatus


class Machine(DomainModel):
    machine_id: MachineId
    name: str
    machine_type: str
    status: MachineStatus = MachineStatus.ACTIVE
    location: str | None = None
