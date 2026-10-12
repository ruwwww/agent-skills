---
name: ai-pcb-eda
description: Script and verify KiCad PCBs with Python and automated DRC.
---

# AI-Assisted PCB & Hardware EDA

Design electronic hardware and printed circuit boards through **programmatic Python scripting** and automated verification loops against KiCad.

## Core Tooling & Ecosystem
- **CAD Engine:** KiCad 8/9/10 (`kicad-cli`, `pcbnew` Python bindings).
- **Programmatic Schematics & Netlists:** `skidl` (schematics in pure Python) or direct `.kicad_sch` S-expression generation.
- **Placement & Layout Automation:** Python scripts interfacing with `pcbnew` to place footprints by functional block, calculate bypass cap routing proximities, and enforce keepout zones.
- **Panelization & Export:** `kikit` for panelization, automated Gerber, drill, BOM, and CPL/pick-and-place export.

## Automated Closed-Loop Workflow
1. **Schematic & Netlist Definition:** Define connectivity, pin mappings, power nets (`+5V`, `+3V3`, `GND`), and decoupling capacitor assignments.
2. **Algorithmic Placement (`plan_layout.py`):**
   - Establish physical board outline (`Edge.Cuts`) and mounting hole patterns.
   - Group components into functional clusters: Power/BEC, MCU/Logic, Sensors/IMU, Connectors.
   - Position high-heat and switching elements (buck inductors, TVS diodes) with required clearances.
3. **Automated DRC Execution:**
   - Run headless Design Rule Check:
     ```bash
     kicad-cli pcb drc --output-format json -o drc_report.json board.kicad_pcb
     ```
   - Parse violations (trace clearance, footprint overlaps, pad collisions on reverse layer).
4. **Iterative Refinement:** Script modifies component coordinates in response to DRC errors until zero fatal violations remain.
5. **Manufacturing Export:**
   ```bash
   kicad-cli pcb export gerbers -o gerbers/ board.kicad_pcb
   kicad-cli pcb export drill -o gerbers/ board.kicad_pcb
   ```
