#!/usr/bin/env python3
"""
Logisim Circuit Inspector and Verification Tool
===============================================
Performs deep structural, electrical, and ergonomic audits of Logisim .circ files:
1. Toolbar & Mappings Check: Ensures UI toolbar (Poke Tool, Select Tool) does not disappear in Logisim.
2. Label Audit: Enforces strict naming rules - only inputs and outputs should have labels;
   internal logic gates (AND, OR, NOT, etc.) and flip-flops must remain unlabeled.
3. Wire Connectivity & Dangling Wire Detection:
   - Detects floating stubs (endpoints connecting to nothing).
   - Detects non-orthogonal and unaligned wires.
   - Detects overlapping or zero-length wires.
4. Circuit Topology & Truth Table Matrix:
   - Traces signal paths from inputs to outputs.
   - Displays canonical connection matrix (e.g., encoder bit taps, decoder minterms, MUX/DEMUX routes).
"""

from __future__ import annotations
import sys
import os
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Tuple, Set, Optional, Any


# Standard Gate Dimensions in Logisim 2.7.1
def get_gate_input_offsets(inputs: int, size: int) -> List[int]:
    """Calculates exact dy offsets for inputs of a gate facing East in Logisim."""
    if inputs <= 3:
        if size < 40:  # Narrow (30)
            delta, step, skip = -5, 10, 10
        elif size >= 60 or inputs <= 2:
            delta, step, skip = -10, 20, 20
        else:  # size 50, inputs 3
            delta, step, skip = -10, 20, 20
    elif inputs == 4 and size >= 60:
        delta, step, skip = -5, 20, 0
    else:
        delta, step, skip = -5, 10, 10

    offsets = []
    for i in range(inputs):
        if inputs % 2 == 1:
            dy = delta * (inputs - 1) + step * i
        else:
            dy = delta * inputs + step * i
            if i >= inputs // 2:
                dy += skip
        offsets.append(dy)
    return offsets


def get_component_port_info(comp_name: str, loc: Tuple[int, int], attrs: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """
    Calculates all port coordinates and expected outward normal unit vectors for a component.
    The normal vector (nx, ny) defines the direction a connected wire MUST travel AWAY from the port.
    Any wire segment connected to the port that is not collinear with (nx, ny) is a tangential defect.
    """
    x, y = loc
    facing = attrs.get("facing", "east")
    size = int(attrs.get("size", "50")) if "size" in attrs else 50
    inputs = int(attrs.get("inputs", "5")) if "inputs" in attrs else 5

    facing_normals = {
        "east": (1, 0),
        "west": (-1, 0),
        "south": (0, 1),
        "north": (0, -1)
    }

    ports = {}

    if comp_name == "Pin":
        ports["pin"] = {"pt": (x, y), "normal": facing_normals.get(facing, (1, 0))}
    elif comp_name in ("Constant", "Clock"):
        ports["out"] = {"pt": (x, y), "normal": facing_normals.get(facing, (1, 0))}
    elif comp_name == "Power":
        ports["out"] = {"pt": (x, y), "normal": (0, -1)}
    elif comp_name == "Ground":
        ports["out"] = {"pt": (x, y), "normal": (0, 1)}
    elif comp_name == "Tunnel":
        ports["pin"] = {"pt": (x, y), "normal": facing_normals.get(facing, (-1, 0))}
    elif comp_name == "NOT Gate":
        gate_size = int(attrs.get("size", "30")) if "size" in attrs else 30
        if facing == "east":
            ports["out"] = {"pt": (x, y), "normal": (1, 0)}
            ports["in"] = {"pt": (x - gate_size, y), "normal": (-1, 0)}
        elif facing == "west":
            ports["out"] = {"pt": (x, y), "normal": (-1, 0)}
            ports["in"] = {"pt": (x + gate_size, y), "normal": (1, 0)}
        elif facing == "south":
            ports["out"] = {"pt": (x, y), "normal": (0, 1)}
            ports["in"] = {"pt": (x, y - gate_size), "normal": (0, -1)}
        elif facing == "north":
            ports["out"] = {"pt": (x, y), "normal": (0, -1)}
            ports["in"] = {"pt": (x, y + gate_size), "normal": (0, 1)}
    elif comp_name in ("AND Gate", "OR Gate", "NAND Gate", "NOR Gate", "XOR Gate", "XNOR Gate"):
        eff_size = size + (10 if comp_name in ("NAND Gate", "NOR Gate", "XOR Gate", "XNOR Gate") else 0)
        offsets = get_gate_input_offsets(inputs, size)
        if facing == "east":
            ports["out"] = {"pt": (x, y), "normal": (1, 0)}
            for i, dy in enumerate(offsets):
                ports[f"in{i}"] = {"pt": (x - eff_size, y + dy), "normal": (-1, 0)}
        elif facing == "west":
            ports["out"] = {"pt": (x, y), "normal": (-1, 0)}
            for i, dy in enumerate(offsets):
                ports[f"in{i}"] = {"pt": (x + eff_size, y + dy), "normal": (1, 0)}
        elif facing == "south":
            ports["out"] = {"pt": (x, y), "normal": (0, 1)}
            for i, dy in enumerate(offsets):
                ports[f"in{i}"] = {"pt": (x - dy, y - eff_size), "normal": (0, -1)}
        elif facing == "north":
            ports["out"] = {"pt": (x, y), "normal": (0, -1)}
            for i, dy in enumerate(offsets):
                ports[f"in{i}"] = {"pt": (x - dy, y + eff_size), "normal": (0, 1)}
    elif comp_name == "D Flip-Flop":
        ports["d"] = {"pt": (x - 40, y), "normal": (-1, 0)}
        ports["clock"] = {"pt": (x - 40, y + 20), "normal": (-1, 0)}
        ports["q"] = {"pt": (x, y), "normal": (1, 0)}
        ports["notq"] = {"pt": (x, y + 20), "normal": (1, 0)}
        ports["reset"] = {"pt": (x - 10, y + 30), "normal": (0, 1)}
        ports["preset"] = {"pt": (x - 30, y + 30), "normal": (0, 1)}
        ports["enable"] = {"pt": (x - 20, y + 30), "normal": (0, 1)}
    elif comp_name == "T Flip-Flop":
        ports["t"] = {"pt": (x - 40, y), "normal": (-1, 0)}
        ports["clock"] = {"pt": (x - 40, y + 20), "normal": (-1, 0)}
        ports["q"] = {"pt": (x, y), "normal": (1, 0)}
        ports["notq"] = {"pt": (x, y + 20), "normal": (1, 0)}
        ports["reset"] = {"pt": (x - 10, y + 30), "normal": (0, 1)}
        ports["preset"] = {"pt": (x - 30, y + 30), "normal": (0, 1)}
        ports["enable"] = {"pt": (x - 20, y + 30), "normal": (0, 1)}
    elif comp_name == "J-K Flip-Flop":
        ports["j"] = {"pt": (x - 40, y), "normal": (-1, 0)}
        ports["clock"] = {"pt": (x - 40, y + 10), "normal": (-1, 0)}
        ports["k"] = {"pt": (x - 40, y + 20), "normal": (-1, 0)}
        ports["q"] = {"pt": (x, y), "normal": (1, 0)}
        ports["notq"] = {"pt": (x, y + 20), "normal": (1, 0)}
        ports["reset"] = {"pt": (x - 10, y + 30), "normal": (0, 1)}
        ports["preset"] = {"pt": (x - 30, y + 30), "normal": (0, 1)}
        ports["enable"] = {"pt": (x - 20, y + 30), "normal": (0, 1)}
    elif comp_name == "S-R Flip-Flop":
        ports["s"] = {"pt": (x - 40, y), "normal": (-1, 0)}
        ports["clock"] = {"pt": (x - 40, y + 10), "normal": (-1, 0)}
        ports["r"] = {"pt": (x - 40, y + 20), "normal": (-1, 0)}
        ports["q"] = {"pt": (x, y), "normal": (1, 0)}
        ports["notq"] = {"pt": (x, y + 20), "normal": (1, 0)}
        ports["reset"] = {"pt": (x - 10, y + 30), "normal": (0, 1)}
        ports["preset"] = {"pt": (x - 30, y + 30), "normal": (0, 1)}
        ports["enable"] = {"pt": (x - 20, y + 30), "normal": (0, 1)}
    elif comp_name == "Multiplexer":
        sel_cnt = int(attrs.get("select", "1"))
        in_cnt = 1 << sel_cnt
        for i in range(in_cnt):
            ports[f"in{i}"] = {"pt": (x - 30, y - 10 * (in_cnt - 1) + 20 * i), "normal": (-1, 0)}
        ports["out"] = {"pt": (x, y), "normal": (1, 0)}
        ports["sel"] = {"pt": (x - 20, y + 20), "normal": (0, 1)}
        ports["enable"] = {"pt": (x - 10, y + 20), "normal": (0, 1)}
    elif comp_name == "Demultiplexer":
        sel_cnt = int(attrs.get("select", "1"))
        out_cnt = 1 << sel_cnt
        ports["in"] = {"pt": (x, y), "normal": (-1, 0)}
        for i in range(out_cnt):
            ports[f"out{i}"] = {"pt": (x + 30, y - 10 * (out_cnt - 1) + 20 * i), "normal": (1, 0)}
        ports["sel"] = {"pt": (x + 20, y + 20), "normal": (0, 1)}
        ports["enable"] = {"pt": (x + 10, y + 20), "normal": (0, 1)}
    elif comp_name == "Decoder":
        sel_cnt = int(attrs.get("select", "1"))
        out_cnt = 1 << sel_cnt
        ports["sel"] = {"pt": (x, y), "normal": (-1, 0)}
        ports["enable"] = {"pt": (x - 10, y), "normal": (-1, 0)}
        for i in range(out_cnt):
            ports[f"out{i}"] = {"pt": (x + 10, y - 10 - 20 * (out_cnt - 1 - i)), "normal": (1, 0)}
    elif comp_name in ("Adder", "Subtractor", "Multiplier", "Divider"):
        ports["inA"] = {"pt": (x - 40, y - 10), "normal": (-1, 0)}
        ports["inB"] = {"pt": (x - 40, y + 10), "normal": (-1, 0)}
        ports["out"] = {"pt": (x, y), "normal": (1, 0)}
        ports["cin"] = {"pt": (x - 20, y - 20), "normal": (0, -1)}
        ports["cout"] = {"pt": (x - 20, y + 20), "normal": (0, 1)}
    elif comp_name == "Comparator":
        ports["inA"] = {"pt": (x - 40, y - 10), "normal": (-1, 0)}
        ports["inB"] = {"pt": (x - 40, y + 10), "normal": (-1, 0)}
        ports["gt"] = {"pt": (x, y - 10), "normal": (1, 0)}
        ports["eq"] = {"pt": (x, y), "normal": (1, 0)}
        ports["lt"] = {"pt": (x, y + 10), "normal": (1, 0)}
    elif comp_name in ("Register", "Counter"):
        ports["in"] = {"pt": (x - 30, y), "normal": (-1, 0)}
        ports["out"] = {"pt": (x, y), "normal": (1, 0)}
        ports["clock"] = {"pt": (x - 20, y + 20), "normal": (0, 1)}
        ports["clear"] = {"pt": (x - 10, y + 20), "normal": (0, 1)}
        if comp_name == "Register":
            ports["enable"] = {"pt": (x - 30, y + 10), "normal": (-1, 0)}
        else:
            ports["load"] = {"pt": (x - 30, y - 10), "normal": (-1, 0)}
            ports["count"] = {"pt": (x - 30, y + 10), "normal": (-1, 0)}
            ports["carry"] = {"pt": (x, y + 10), "normal": (1, 0)}
    elif comp_name in ("RAM", "ROM"):
        ports["addr"] = {"pt": (x, y), "normal": (-1, 0)}
        ports["data"] = {"pt": (x + 140, y), "normal": (1, 0)}
    elif comp_name == "Button":
        facing_map = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}
        ports["out"] = {"pt": (x, y), "normal": facing_map.get(facing, (1, 0))}
    elif comp_name == "Joystick":
        ports["x"] = {"pt": (x, y - 10), "normal": (-1, 0)}
        ports["y"] = {"pt": (x, y + 10), "normal": (-1, 0)}
    elif comp_name == "Keyboard":
        ports["clock"] = {"pt": (x, y), "normal": (-1, 0)}
        ports["re"] = {"pt": (x + 20, y + 20), "normal": (0, 1)}
        ports["clr"] = {"pt": (x + 40, y + 20), "normal": (0, 1)}
        ports["avail"] = {"pt": (x + 60, y + 20), "normal": (0, 1)}
        ports["data"] = {"pt": (x + 80, y + 20), "normal": (0, 1)}
    elif comp_name == "LED":
        led_facing = attrs.get("facing", "west")
        ports["in"] = {"pt": (x, y), "normal": facing_normals.get(led_facing, (-1, 0))}
    elif comp_name == "7-Segment Display":
        ports["a"] = {"pt": (x + 10, y), "normal": (0, -1)}
        ports["b"] = {"pt": (x + 20, y), "normal": (0, -1)}
        ports["f"] = {"pt": (x, y), "normal": (0, -1)}
        ports["g"] = {"pt": (x + 30, y), "normal": (0, -1)}
        ports["e"] = {"pt": (x, y + 60), "normal": (0, 1)}
        ports["d"] = {"pt": (x + 10, y + 60), "normal": (0, 1)}
        ports["c"] = {"pt": (x + 20, y + 60), "normal": (0, 1)}
        ports["dp"] = {"pt": (x + 30, y + 60), "normal": (0, 1)}
    elif comp_name == "Hex Digit Display":
        ports["data"] = {"pt": (x, y), "normal": (0, 1)}
        ports["dp"] = {"pt": (x + 10, y), "normal": (0, 1)}
    elif comp_name == "DotMatrix":
        ports["cols"] = {"pt": (x, y), "normal": (-1, 0)}
        ports["rows"] = {"pt": (x, y + 20), "normal": (-1, 0)}
    elif comp_name == "TTY":
        ports["data"] = {"pt": (x, y), "normal": (-1, 0)}
        ports["clock"] = {"pt": (x, y + 20), "normal": (-1, 0)}
        ports["we"] = {"pt": (x + 20, y + 40), "normal": (0, 1)}
        ports["clr"] = {"pt": (x + 40, y + 40), "normal": (0, 1)}
    else:
        # Generic component fallback
        ports["anchor"] = {"pt": (x, y), "normal": None}

    return ports


def get_component_ports(comp_name: str, loc: Tuple[int, int], attrs: Dict[str, str]) -> Dict[str, Tuple[int, int]]:
    """Calculates all port coordinates for a component based on type, loc, and attrs."""
    info = get_component_port_info(comp_name, loc, attrs)
    return {k: v["pt"] for k, v in info.items()}


def get_component_bbox(name: str, loc: Tuple[int, int], attrs: Dict[str, str]) -> Tuple[int, int, int, int]:
    """
    Calculates the exact 2D visual Axis-Aligned Bounding Box (AABB) of every Logisim component.
    Guarantees that no two components on the canvas ever physically overlap.
    Returns: (xmin, ymin, xmax, ymax) in absolute canvas coordinates.
    """
    x, y = loc
    facing = attrs.get("facing", "east")
    size = int(attrs.get("size", "50")) if "size" in attrs else 50
    inputs = int(attrs.get("inputs", "5")) if "inputs" in attrs else 5

    # 1. Wiring Library (lib 0)
    if name == "Pin":
        if facing == "west":
            return (x - 20, y - 10, x, y + 10)
        elif facing == "east":
            return (x, y - 10, x + 20, y + 10)
        elif facing == "south":
            return (x - 10, y, x + 10, y + 20)
        elif facing == "north":
            return (x - 10, y - 20, x + 10, y)
        return (x - 10, y - 10, x + 10, y + 10)

    elif name in ("Probe", "Clock", "Constant"):
        return (x, y - 10, x + 20, y + 10)
    elif name == "Ground":
        return (x - 10, y, x + 10, y + 15)
    elif name == "Power":
        return (x - 10, y - 15, x + 10, y)
    elif name == "Pull Resistor":
        return (x - 10, y - 10, x + 10, y + 10)
    elif name in ("Transistor", "Transmission Gate"):
        return (x - 20, y - 20, x + 20, y + 20)
    elif name == "Bit Extender":
        return (x - 40, y - 20, x, y + 20)
    elif name == "Tunnel":
        lbl = attrs.get("label", "")
        w = max(20, len(lbl) * 7 + 10)
        if facing == "west":
            return (x - w, y - 10, x, y + 10)
        elif facing == "east":
            return (x, y - 10, x + w, y + 10)
        elif facing == "south":
            return (x - 10, y, x + 10, y + w)
        else:
            return (x - 10, y - w, x + 10, y)
    elif name == "Splitter":
        fanout = int(attrs.get("fanout", "2"))
        h = max(20, fanout * 10)
        if facing == "east":
            return (x, y - h, x + 20, y + 10)
        elif facing == "west":
            return (x - 20, y - h, x, y + 10)
        elif facing == "south":
            return (x - 10, y, x + h, y + 20)
        else:
            return (x - 10, y - 20, x + h, y)

    # 2. Logic Gates (lib 1)
    elif name in ("AND Gate", "OR Gate", "NAND Gate", "NOR Gate", "XOR Gate", "XNOR Gate"):
        eff_size = size + (10 if name in ("NAND Gate", "NOR Gate", "XOR Gate") else (20 if name == "XNOR Gate" else 0))
        h = max(10 * inputs, size)
        h2 = h // 2
        if facing == "east":
            return (x - eff_size, y - h2, x, y + h2)
        elif facing == "west":
            return (x, y - h2, x + eff_size, y + h2)
        elif facing == "south":
            return (x - h2, y - eff_size, x + h2, y)
        elif facing == "north":
            return (x - h2, y, x + h2, y + eff_size)

    elif name == "NOT Gate":
        sz = int(attrs.get("size", "30")) if "size" in attrs else 30
        if facing == "east":
            return (x - sz, y - 10, x, y + 10)
        elif facing == "west":
            return (x, y - 10, x + sz, y + 10)
        elif facing == "south":
            return (x - 10, y - sz, x + 10, y)
        elif facing == "north":
            return (x - 10, y, x + 10, y + sz)

    elif name in ("Buffer", "Controlled Buffer", "Controlled Inverter"):
        return (x - 20, y - 10, x + 10, y + 10)

    # 3. Plexers (lib 2)
    elif name in ("Multiplexer", "Demultiplexer"):
        sel_cnt = int(attrs.get("select", "1"))
        lines = 1 << sel_cnt
        span = 10 * lines + 10
        if name == "Multiplexer":
            return (x - 30, y - span, x, y + span)
        else:
            return (x, y - span, x + 30, y + span)

    elif name == "Decoder":
        sel_cnt = int(attrs.get("select", "1"))
        out_cnt = 1 << sel_cnt
        return (x - 20, y - 20 * out_cnt - 10, x + 20, y + 10)

    elif name == "Priority Encoder":
        sel_cnt = int(attrs.get("select", "3"))
        in_cnt = 1 << sel_cnt
        return (x - 40, y - 10 * in_cnt, x, y + 10 * in_cnt)

    elif name == "Bit Selector":
        return (x - 30, y - 20, x, y + 20)

    # 4. Arithmetic (lib 3)
    elif name in ("Adder", "Subtractor", "Multiplier", "Divider", "Negator", "Comparator", "Shifter", "Bit Adder", "Bit Finder"):
        return (x - 40, y - 20, x, y + 20)

    # 5. Memory / Sequential (lib 4)
    elif "Flip-Flop" in name:
        return (x - 40, y - 10, x, y + 30)
    elif name in ("Register", "Counter"):
        return (x - 30, y - 15, x + 10, y + 25)
    elif name == "Shift Register":
        length = int(attrs.get("length", "8"))
        w = max(60, length * 10 + 20)
        return (x - 40, y - 20, x + w - 40, y + 20)
    elif name in ("RAM", "ROM"):
        return (x, y - 40, x + 140, y + 40)
    elif name == "Random":
        return (x - 40, y - 20, x, y + 20)

    # 6. I/O (lib 5)
    elif name == "Button":
        return (x - 30, y - 10, x, y + 10) if facing == "east" else (x - 10, y - 10, x + 10, y + 10)
    elif name == "Joystick":
        return (x, y - 30, x + 60, y + 30)
    elif name == "Keyboard":
        return (x, y - 10, x + 140, y + 30)
    elif name == "LED":
        return (x - 10, y - 10, x + 10, y + 10)
    elif name == "7-Segment Display":
        return (x - 5, y, x + 35, y + 65)
    elif name == "Hex Digit Display":
        return (x - 5, y - 65, x + 35, y)
    elif name == "DotMatrix":
        cols = int(attrs.get("matrixcols", "5"))
        rows = int(attrs.get("matrixrows", "7"))
        return (x, y - 10, x + cols * 10 + 10, y + rows * 10 + 10)
    elif name == "TTY":
        cols = int(attrs.get("columns", "32")) if "columns" in attrs else int(attrs.get("cols", "32"))
        rows = int(attrs.get("rows", "8"))
        w = max(160, cols * 8 + 20)
        h = max(80, rows * 14 + 20)
        return (x, y, x + w, y + h)

    # 7. Text & Base (lib 6)
    elif name == "Text":
        txt = attrs.get("text", "")
        w = max(30, len(txt) * 7 + 10)
        return (x - w // 2, y - 10, x + w // 2, y + 10)

    # 8. Subcircuit fallback
    return (x, y, x + 50, y + 50)


class CircuitInspectionReport:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.circuit_name: str = ""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.inputs: List[Dict[str, Any]] = []
        self.outputs: List[Dict[str, Any]] = []
        self.gates: List[Dict[str, Any]] = []
        self.wire_count: int = 0
        self.dangling_endpoints: List[Tuple[int, int]] = []
        self.tangential_violations: List[str] = []
        self.matrix_connections: Dict[str, List[str]] = defaultdict(list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def parse_coord(s: str) -> Tuple[int, int]:
    m = re.match(r"^\(?\s*(-?\d+)\s*,\s*(-?\d+)\s*\)?$", s.strip())
    if not m:
        raise ValueError(f"Invalid coordinate string: {s}")
    return (int(m.group(1)), int(m.group(2)))


def inspect_circuit(filepath: str, strict: bool = True) -> CircuitInspectionReport:
    report = CircuitInspectionReport(filepath)

    if not os.path.exists(filepath):
        report.errors.append(f"File not found: {filepath}")
        return report

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except Exception as e:
        report.errors.append(f"XML parse error: {e}")
        return report

    # 1. Toolbar and Mappings Check
    toolbar = root.find("toolbar")
    if toolbar is None:
        report.warnings.append("Missing <toolbar> element. Logisim toolbar will be empty.")
    else:
        tools = [t.get("name") for t in toolbar.findall("tool")]
        if "Poke Tool" not in tools:
            report.warnings.append("<toolbar> missing 'Poke Tool' (hand tool won't be easily accessible).")
        if "Edit Tool" not in tools:
            report.warnings.append("<toolbar> missing 'Edit Tool' (select tool won't be easily accessible).")

    mappings = root.find("mappings")
    if mappings is None:
        report.warnings.append("Missing <mappings> element. Mouse bindings may not function.")

    # 2. Inspect Circuits
    circuits = root.findall("circuit")
    if not circuits:
        report.errors.append("No <circuit> elements found in project.")
        return report

    # Default to the designated main circuit or the first non-empty circuit
    main_elem = root.find("main")
    main_name = main_elem.get("name") if main_elem is not None else None

    circ = None
    if main_name:
        for c in circuits:
            if c.get("name") == main_name:
                circ = c
                break
    if circ is None:
        circ = circuits[0]

    report.circuit_name = circ.get("name", "main")

    # Collect Components & Ports
    comps = circ.findall("comp")
    comp_ports: Dict[Tuple[int, int], List[Tuple[str, str]]] = defaultdict(list)
    comp_ports_normals: Dict[Tuple[int, int], List[Tuple[str, str, Optional[Tuple[int, int]]]]] = defaultdict(list)
    gate_types = {
        "AND Gate", "OR Gate", "NOT Gate", "NAND Gate", "NOR Gate", "XOR Gate", "XNOR Gate",
        "D Flip-Flop", "T Flip-Flop", "J-K Flip-Flop", "S-R Flip-Flop", "Counter", "Register"
    }

    for c in comps:
        name = c.get("name")
        loc_str = c.get("loc")
        if not loc_str:
            report.errors.append(f"Component '{name}' missing 'loc' attribute.")
            continue
        loc = parse_coord(loc_str)

        # Collect attributes
        attrs = {a.get("name"): a.get("val", "") for a in c.findall("a")}
        label = attrs.get("label", "").strip()

        # Rule Check: Internal gates and flip-flops must NOT be labeled
        if name in gate_types:
            report.gates.append({"name": name, "loc": loc, "label": label, "attrs": attrs})
            if label:
                msg = f"Forbidden label '{label}' on internal component '{name}' at {loc}. Only Inputs/Outputs should have labels!"
                if strict:
                    report.errors.append(msg)
                else:
                    report.warnings.append(msg)

        if name == "Pin":
            is_output = attrs.get("output", "false").lower() == "true"
            facing = attrs.get("facing", "east")
            pin_info = {"loc": loc, "label": label, "output": is_output, "facing": facing}
            if is_output:
                report.outputs.append(pin_info)
            else:
                report.inputs.append(pin_info)

        # Calculate all connection ports for this component
        ports_info = get_component_port_info(name, loc, attrs)
        for port_name, pmeta in ports_info.items():
            port_pt = pmeta["pt"]
            comp_ports[port_pt].append((name, port_name))
            comp_ports_normals[port_pt].append((name, port_name, pmeta["normal"]))

    # 3. Collect Wires & Graph
    wires = circ.findall("wire")
    report.wire_count = len(wires)

    wire_degree: Dict[Tuple[int, int], int] = defaultdict(int)
    adj: Dict[Tuple[int, int], Set[Tuple[int, int]]] = defaultdict(set)

    for w in wires:
        f_str = w.get("from")
        t_str = w.get("to")
        if not f_str or not t_str:
            report.errors.append("Wire missing 'from' or 'to' attribute.")
            continue
        p1 = parse_coord(f_str)
        p2 = parse_coord(t_str)

        if p1 == p2:
            report.errors.append(f"Zero-length wire at {p1}.")
            continue

        if p1[0] != p2[0] and p1[1] != p2[1]:
            report.errors.append(f"Non-orthogonal wire from {p1} to {p2}.")
            continue

        if p1[0] % 10 != 0 or p1[1] % 10 != 0 or p2[0] % 10 != 0 or p2[1] % 10 != 0:
            report.errors.append(f"Grid snapping violation: wire {p1} -> {p2} is not aligned to 10px grid.")
            continue

        wire_degree[p1] += 1
        wire_degree[p2] += 1
        adj[p1].add(p2)
        adj[p2].add(p1)

    # 4. Dangling Wire Endpoint Detection
    # An endpoint in wire network is degree 1. If no component port is at this location, it is dangling into empty space!
    for pt, deg in wire_degree.items():
        if deg == 1 and pt not in comp_ports:
            report.dangling_endpoints.append(pt)
            report.errors.append(f"Dangling wire endpoint at {pt}! Wire segment terminates in empty space.")

    # 4.5 Port Perpendicularity Check (Zero Tangential / Grazing Port Connections)
    # Every wire connecting to a component port MUST be strictly perpendicular (normal)
    # to the component boundary, with at least 1-2 grid cells (10-20px) offset before turning.
    for pt, p_list in comp_ports_normals.items():
        if pt not in adj:
            continue
        for c_name, p_name, norm in p_list:
            if norm is None:
                continue
            for neighbor in adj[pt]:
                dx = neighbor[0] - pt[0]
                dy = neighbor[1] - pt[1]
                u = (1 if dx > 0 else (-1 if dx < 0 else 0), 1 if dy > 0 else (-1 if dy < 0 else 0))
                if u != norm:
                    msg = (
                        f"Tangential/grazing wire at {c_name} port '{p_name}' at {pt}! "
                        f"Wire segment to {neighbor} moves in direction {u}, but port requires perpendicular normal {norm}. "
                        f"Wire must turn at least 1-2 grid cells (10-20px) away from component."
                    )
                    report.tangential_violations.append(msg)
                    report.errors.append(msg)

    # 4.6 Electrical Net Output Contention / Short-Circuit Audit
    # Multiple logic gate outputs driving the same net without tristate buffers is a fatal short-circuit.
    visited_net_nodes: Set[Tuple[int, int]] = set()
    for pt in list(adj.keys()):
        if pt in visited_net_nodes:
            continue
        net_nodes = []
        queue = [pt]
        visited_net_nodes.add(pt)
        while queue:
            curr = queue.pop(0)
            net_nodes.append(curr)
            for neighbor in adj[curr]:
                if neighbor not in visited_net_nodes:
                    visited_net_nodes.add(neighbor)
                    queue.append(neighbor)

        gate_outs = []
        for n_pt in net_nodes:
            if n_pt in comp_ports:
                for c_name, p_name in comp_ports[n_pt]:
                    if c_name in gate_types and p_name == "out":
                        gate_outs.append(f"{c_name}@{n_pt}")

        if len(gate_outs) > 1:
            report.errors.append(
                f"Electrical Short Circuit: {len(gate_outs)} logic gate outputs are shorted together on the same net: {', '.join(gate_outs)}! Each gate output must drive its own dedicated receiver."
            )

    # 4.7 Component Visual Collision & Overlap Detection (AABB Intersect)
    # Audits every component against all other components to ensure no overlapping bodies
    comp_bboxes = []
    for c in comps:
        nm = c.get("name")
        if nm == "Text":
            continue
        loc_str = c.get("loc")
        if not loc_str:
            continue
        loc = parse_coord(loc_str)
        attrs = {a.get("name"): a.get("val", "") for a in c.findall("a")}
        label = attrs.get("label", "").strip()
        bbox = get_component_bbox(nm, loc, attrs)
        ports = get_component_port_info(nm, loc, attrs)
        comp_bboxes.append({"name": nm, "loc": loc, "label": label, "bbox": bbox, "ports": ports})

    for i in range(len(comp_bboxes)):
        for j in range(i + 1, len(comp_bboxes)):
            c1 = comp_bboxes[i]
            c2 = comp_bboxes[j]
            b1 = c1["bbox"]
            b2 = c2["bbox"]

            ix = min(b1[2], b2[2]) - max(b1[0], b2[0])
            iy = min(b1[3], b2[3]) - max(b1[1], b2[1])

            # Strictly positive overlap in both X and Y means bodies collide
            if ix > 0 and iy > 0:
                l1_desc = f"'{c1['label']}'" if c1["label"] else f"at {c1['loc']}"
                l2_desc = f"'{c2['label']}'" if c2["label"] else f"at {c2['loc']}"
                report.errors.append(
                    f"Component Visual Collision: {c1['name']} ({l1_desc}) and {c2['name']} ({l2_desc}) "
                    f"spatially overlap by {ix}x{iy} px! Components must have adequate spacing and must never collide."
                )

    # 4.8 Labeled Pin Pitch & Clearance Audit
    # Pins placed too close cause label text and circle/square bodies to collide
    pins = [p for p in comp_bboxes if p["name"] == "Pin"]
    for i in range(len(pins)):
        for j in range(i + 1, len(pins)):
            p1 = pins[i]
            p2 = pins[j]
            loc1 = p1["loc"]
            loc2 = p2["loc"]
            dx = abs(loc1[0] - loc2[0])
            dy = abs(loc1[1] - loc2[1])

            if dx == 0 and dy > 0:
                if dy < 20:
                    report.errors.append(
                        f"Pin Body Collision: Pins '{p1['label']}' at {loc1} and '{p2['label']}' at {loc2} "
                        f"have vertical pitch of only {dy}px (minimum is 20px, recommended >= 30-40px)! Circle bodies collide."
                    )
                elif dy < 30 and (p1["label"] and p2["label"]):
                    report.warnings.append(
                        f"Pin Label Proximity: Pins '{p1['label']}' at {loc1} and '{p2['label']}' at {loc2} "
                        f"have vertical pitch of only {dy}px. Labels may visually touch or collide. Recommend pitch >= 30-40px."
                    )
            elif dy == 0 and dx > 0:
                if dx < 20:
                    report.errors.append(
                        f"Pin Body Collision: Pins '{p1['label']}' at {loc1} and '{p2['label']}' at {loc2} "
                        f"have horizontal pitch of only {dx}px (minimum is 20px, recommended >= 40px)! Bodies collide."
                    )
                elif dx < 40 and (p1["label"] and p2["label"]):
                    report.warnings.append(
                        f"Pin Label Proximity: Pins '{p1['label']}' at {loc1} and '{p2['label']}' at {loc2} "
                        f"have horizontal pitch of only {dx}px. Horizontal labels will collide. Recommend pitch >= 40px."
                    )

    # 4.9 Wire Penetrating Component Interior (Wire-Through-Body Audit)
    for c in comp_bboxes:
        if c["name"] in ("Pin", "Tunnel", "Splitter", "Clock", "Constant", "Power", "Ground"):
            continue
        bx1, by1, bx2, by2 = c["bbox"]
        port_pts = {v["pt"] for v in c["ports"].values()}

        for w in wires:
            p1 = parse_coord(w.get("from"))
            p2 = parse_coord(w.get("to"))

            # Horizontal wire segment
            if p1[1] == p2[1]:
                wy = p1[1]
                if by1 < wy < by2:
                    wx1, wx2 = min(p1[0], p2[0]), max(p1[0], p2[0])
                    inter_x1 = max(wx1, bx1)
                    inter_x2 = min(wx2, bx2)
                    if inter_x1 < inter_x2:
                        if p1 not in port_pts and p2 not in port_pts:
                            report.errors.append(
                                f"Wire-Through-Body Violation: Wire from {p1} to {p2} penetrates through interior of "
                                f"{c['name']} at {c['loc']}! Wires must route around components, not through them."
                            )
                        elif wx1 < bx1 and wx2 > bx2:
                            report.errors.append(
                                f"Wire-Through-Body Violation: Wire from {p1} to {p2} cuts completely through {c['name']} at {c['loc']}!"
                            )
            # Vertical wire segment
            elif p1[0] == p2[0]:
                wx = p1[0]
                if bx1 < wx < bx2:
                    wy1, wy2 = min(p1[1], p2[1]), max(p1[1], p2[1])
                    inter_y1 = max(wy1, by1)
                    inter_y2 = min(wy2, by2)
                    if inter_y1 < inter_y2:
                        if p1 not in port_pts and p2 not in port_pts:
                            report.errors.append(
                                f"Wire-Through-Body Violation: Wire from {p1} to {p2} penetrates through interior of "
                                f"{c['name']} at {c['loc']}! Wires must route around components, not through them."
                            )
                        elif wy1 < by1 and wy2 > by2:
                            report.errors.append(
                                f"Wire-Through-Body Violation: Wire from {p1} to {p2} cuts completely through {c['name']} at {c['loc']}!"
                            )

    # 5. Connectivity Trace & Matrix
    # Map gates to the output pins they drive
    gate_output_to_pin: Dict[Tuple[int, int], str] = {}
    for outp in report.outputs:
        out_pt = outp["loc"]
        visited = set()
        queue = [out_pt]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            if curr in comp_ports:
                for c_name, p_name in comp_ports[curr]:
                    if c_name in gate_types and p_name == "out":
                        gate_output_to_pin[curr] = outp["label"] or f"Out@{out_pt}"
            for neighbor in adj[curr]:
                if neighbor not in visited:
                    queue.append(neighbor)

    # Map input port coordinates to gate output coordinate
    input_port_to_gate_out: Dict[Tuple[int, int], Tuple[int, int]] = {}
    for g in report.gates:
        g_loc = g["loc"]
        ports = get_component_ports(g["name"], g_loc, g["attrs"])
        out_coord = ports.get("out")
        if out_coord:
            for p_name, p_coord in ports.items():
                if p_name != "out":
                    input_port_to_gate_out[p_coord] = out_coord

    # Trace connectivity from each input pin to gates and driven output pins
    report.input_to_outputs: Dict[str, List[str]] = defaultdict(list)

    for inp in report.inputs:
        in_pt = inp["loc"]
        visited = set()
        queue = [in_pt]
        connected_gates = []
        driven_outputs = set()

        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)

            # Check if this node touches any component port
            if curr in comp_ports:
                for c_name, p_name in comp_ports[curr]:
                    if c_name != "Pin":
                        connected_gates.append(f"{c_name}({p_name})@{curr}")
                # Check if this port belongs to a gate that drives an output pin
                if curr in input_port_to_gate_out:
                    g_out = input_port_to_gate_out[curr]
                    if g_out in gate_output_to_pin:
                        driven_outputs.add(gate_output_to_pin[g_out])

            # Traverse adjacent wire points
            for neighbor in adj[curr]:
                if neighbor not in visited:
                    queue.append(neighbor)

        lbl = inp["label"] or f"In@{in_pt}"
        report.matrix_connections[lbl] = connected_gates
        report.input_to_outputs[lbl] = sorted(list(driven_outputs))

    return report


def print_report(report: CircuitInspectionReport):
    print("=" * 70)
    print(f"CIRCUIT INSPECTION REPORT: {os.path.basename(report.filepath)}")
    print(f"Circuit Name : {report.circuit_name}")
    print(f"Inputs       : {len(report.inputs)} pins {[i.get('label') for i in report.inputs]}")
    print(f"Outputs      : {len(report.outputs)} pins {[o.get('label') for o in report.outputs]}")
    print(f"Gates        : {len(report.gates)} logic elements")
    print(f"Wires        : {report.wire_count} segments")
    print("=" * 70)

    if report.errors:
        print(f"\n[!] ERRORS FOUND ({len(report.errors)}):")
        for err in report.errors:
            print(f"  - {err}")

    if report.warnings:
        print(f"\n[*] WARNINGS ({len(report.warnings)}):")
        for warn in report.warnings:
            print(f"  - {warn}")

    if not report.errors and not report.warnings:
        print("\n[OK] Zero defects found! Wire snapping, orthogonality, labels, and netlist valid.")

    print("\n--- INPUT CONNECTIVITY SUMMARY ---")
    for in_lbl, conns in report.matrix_connections.items():
        if conns:
            print(f"  {in_lbl:12s} -> {len(conns)} connection(s): {', '.join(conns[:4])}{'...' if len(conns) > 4 else ''}")
        else:
            print(f"  {in_lbl:12s} -> [UNCONNECTED]")

    if hasattr(report, "input_to_outputs") and any(report.input_to_outputs.values()):
        print("\n--- INPUT -> DRIVEN OUTPUTS MATRIX (LOGICAL TRUTH TABLE) ---")
        for in_lbl, driven in report.input_to_outputs.items():
            driven_str = ", ".join(driven) if driven else "(none)"
            print(f"  {in_lbl:16s} ==> {driven_str}")

    print("=" * 70)
    status_str = "PASSED" if report.passed else "FAILED"
    print(f"FINAL AUDIT STATUS: {status_str}\n")


def fix_circuit_labels(filepath: str) -> bool:
    """Removes labels from all internal logic gates in a .circ file."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        gate_types = {
            "AND Gate", "OR Gate", "NOT Gate", "NAND Gate", "NOR Gate", "XOR Gate", "XNOR Gate",
            "D Flip-Flop", "T Flip-Flop", "J-K Flip-Flop", "S-R Flip-Flop", "Counter", "Register"
        }
        modified = False
        for circ in root.findall("circuit"):
            for comp in circ.findall("comp"):
                if comp.get("name") in gate_types:
                    for a in list(comp.findall("a")):
                        if a.get("name") == "label":
                            comp.remove(a)
                            modified = True

        if modified:
            tree.write(filepath, encoding="utf-8", xml_declaration=True)
            print(f"Successfully cleaned internal gate labels in {filepath}")
            return True
    except Exception as e:
        print(f"Failed to fix labels in {filepath}: {e}")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_circ.py <path_to_circuit.circ> [--fix-labels] [--non-strict]")
        sys.exit(1)

    target_path = sys.argv[1]
    do_fix = "--fix-labels" in sys.argv
    strict_mode = "--non-strict" not in sys.argv

    if do_fix:
        fix_circuit_labels(target_path)

    rep = inspect_circuit(target_path, strict=strict_mode)
    print_report(rep)
    sys.exit(0 if rep.passed else 1)
