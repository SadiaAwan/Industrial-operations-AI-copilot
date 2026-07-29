"""Idempotently seed PostgreSQL with the deterministic Phase 2 dataset."""

from sqlalchemy.orm import Session

from app.database.models import (
    IncidentModel,
    MachineModel,
    MaintenanceRecordModel,
    SensorReadingModel,
)
from app.database.session import (
    create_database_engine,
    create_session_factory,
    transactional_session,
)
from scripts.generate_sensor_data import (
    MACHINE_SCENARIOS,
    generate_incidents,
    generate_maintenance_records,
    generate_sensor_readings,
)


def seed_database(session: Session) -> dict[str, int]:
    machines = [machine for machine, _ in MACHINE_SCENARIOS]
    readings = generate_sensor_readings()
    incidents = generate_incidents()
    maintenance = generate_maintenance_records()

    for machine in machines:
        session.merge(MachineModel(**machine.model_dump(mode="json")))
    session.flush()
    for reading in readings:
        session.merge(SensorReadingModel(**reading.model_dump(mode="json")))
    for incident in incidents:
        session.merge(IncidentModel(**incident.model_dump(mode="json")))
    for record in maintenance:
        session.merge(MaintenanceRecordModel(**record.model_dump(mode="json")))

    return {
        "machines": len(machines),
        "sensor_readings": len(readings),
        "incidents": len(incidents),
        "maintenance_records": len(maintenance),
    }


def main() -> None:
    engine = create_database_engine()
    factory = create_session_factory(engine)
    with transactional_session(factory) as session:
        counts = seed_database(session)
    engine.dispose()
    print("Seed complete:", counts)


if __name__ == "__main__":
    main()
