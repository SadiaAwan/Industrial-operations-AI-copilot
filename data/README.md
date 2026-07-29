# Synthetic MVP Data

This directory contains synthetic data for the centrifugal-pump copilot. It does
not contain real company, equipment, technician, or operational data.

## Dataset contents

| Asset | Count | Location |
| --- | ---: | --- |
| Machines | 5 | `machines/machines.json` |
| Sensor readings | 420 | `synthetic_sensor_data/sensor_readings.csv` |
| Historical incidents | 30 | `incidents/incidents.json` |
| Maintenance records | 75 | `maintenance/maintenance_records.json` |
| Indexed document candidates | 8 | `documents_manifest.json` |

The initial evaluation datasets contain 25 questions across retrieval, tools,
safety, failures, and end-to-end behavior.

## Machine scenarios

| Machine | Scenario |
| --- | --- |
| P-101 | Normal operation |
| P-102 | Cavitation |
| P-103 | Shaft misalignment |
| P-104 | Bearing degradation |
| P-105 | Motor overload |

Each machine has 12 five-minute samples for all seven sensor types:

- vibration RMS
- bearing temperature
- motor current
- suction pressure
- discharge pressure
- flow rate
- rotational speed

Sensor data uses a normalized long format so every value retains its type, unit,
timestamp, reading ID, and machine ID.

## Documents

The document collection includes:

- two approved manuals
- three approved procedures
- two approved safety instructions
- one superseded maintenance-manual revision

`documents_manifest.json` contains the metadata needed by the later ingestion
pipeline. The superseded manual is an intentional negative fixture and must not
be used in normal grounded responses.

## Negative fixtures

`synthetic_sensor_data/invalid_readings.json` contains deliberately invalid
records for validation tests:

- wrong unit
- timestamp without UTC timezone
- unknown machine

These records are never operational sensor data.

## Regeneration

Run from the repository root:

```bash
uv run python -m scripts.generate_sensor_data
```

The default seed is `104` and the reference time is fixed. Regenerating with the
same code and seed produces byte-identical JSON and CSV files.

To generate into another directory:

```bash
uv run python -m scripts.generate_sensor_data --output-root /path/to/output
```

To use a different deterministic seed:

```bash
uv run python -m scripts.generate_sensor_data --seed 205
```

Changing the seed changes numerical noise and record timestamps. A seed change
that affects committed data must be reviewed together with the generated diff
and relevant evaluation expectations.
