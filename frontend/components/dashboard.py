"""Machine overview, live status, and sensor trend components."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd
import streamlit as st

from app.schemas.api import MachineStatusResponse


def sensor_rows(status: MachineStatusResponse) -> list[dict[str, Any]]:
    return [
        {
            "timestamp": reading.recorded_at,
            "sensor": reading.sensor_type,
            "value": reading.value,
            "unit": reading.unit,
        }
        for reading in status.latest_readings
    ]


def latest_sensor_values(status: MachineStatusResponse) -> dict[str, tuple[float, str]]:
    values: dict[str, tuple[float, str]] = {}
    for reading in sorted(status.latest_readings, key=lambda item: item.recorded_at):
        values[reading.sensor_type] = (reading.value, reading.unit)
    return values


def render_machine_dashboard(status: MachineStatusResponse) -> None:
    machine = status.machine
    st.subheader(machine.name)
    st.caption(
        f"{machine.machine_id} · {machine.machine_type.replace('_', ' ').title()}"
        + (f" · {machine.location}" if machine.location else "")
    )

    status_column, reading_column, coverage_column = st.columns(3)
    status_column.metric(
        "Machine status", machine.status.value.replace("_", " ").title()
    )
    reading_column.metric("Latest readings", len(status.latest_readings))
    coverage_column.metric(
        "Sensor types", len({item.sensor_type for item in status.latest_readings})
    )

    if not status.latest_readings:
        st.info("No recent sensor readings are available for this machine.")
        return

    st.markdown("#### Current measurements")
    values = latest_sensor_values(status)
    metric_columns = st.columns(min(len(values), 4))
    for index, (sensor_name, (value, unit)) in enumerate(values.items()):
        metric_columns[index % len(metric_columns)].metric(
            sensor_name.replace("_", " ").title(), f"{value:g} {unit}"
        )

    st.markdown("#### Sensor trends")
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sensor_rows(status):
        grouped[str(row["sensor"])].append(row)
    sensor_tabs = st.tabs([name.replace("_", " ").title() for name in grouped])
    for tab, (_, rows) in zip(sensor_tabs, grouped.items(), strict=True):
        with tab:
            frame = pd.DataFrame(rows).set_index("timestamp")
            st.line_chart(frame[["value"]], use_container_width=True)
