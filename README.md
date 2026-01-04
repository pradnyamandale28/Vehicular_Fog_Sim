# Vehicular Fog Computing Simulation

A SUMO-based simulation for vehicular fog computing with TraCI bridge integration.

## Project Structure

```
vehicular_fog_sim/
├── sim/
│   └── traci_bridge.py    # TraCI bridge for SUMO integration
├── sumo/
│   ├── config/            # SUMO configuration files
│   ├── net/               # Network definition files
│   ├── routes/            # Route and trip files
│   └── additional/        # Vehicle type definitions
└── logs/                  # Simulation logs
```

## Features

- TraCI integration with SUMO
- Fog node management (4 static fog nodes)
- Vehicle handoff detection
- Request management with urgency computation
- Deadline, criticality, handoff risk, and fog load weighting

## Requirements

- Python 3.x
- SUMO (Simulation of Urban MObility)
- TraCI Python library

## Usage

```bash
python sim/traci_bridge.py
```

## Configuration

Edit `sim/traci_bridge.py` to modify:
- Fog node positions (`FOG_NODES`)
- Fog radius (`FOG_RADIUS`)
- Request probability (`REQUEST_PROB`)
- Urgency weights (`W_D`, `W_C`, `W_H`, `W_L`)

