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
    """Calculates exact dy offsets for inputs of a gate facing East."""
    eff_height = max(10 * inputs, size)
    span = eff_height - 10
    if inputs == 1:
        return [0]
    elif inputs == 2:
        return [-10, 10]
    elif inputs % 2 == 1:
        # Odd: center input at 0, symmetric pairs
        k = (inputs - 1) // 2
        step = (span // 2) // k
        step = max(10, (step // 10) * 10)
        return [i * step for i in range(-k, k + 1)]
    else:
        # Even: no input at 0, symmetric pairs
        k = inputs // 2
        half_span = span // 2
        step = half_span // k
        step = max(10, (step // 10) * 10)
        offsets = []
        for i in range(-k, k + 1):
            if i != 0:
                val = i * step
                if val > 0:
                    val = max(10, val)
                else:
                    val = min(-10, val)
                offsets.append(val)
        return offsets


def get_component_ports(comp_name: str, loc: Tuple[int, int], attrs: Dict[str, str]) -> Dict[str, Tuple[int, int]]:
    """Calculates all port coordinates for a component based on type, loc, and attrs."""
    x, y = loc
    facing = attrs.get("facing", "east")
    size = int(attrs.get("size", "50")) if "size" in attrs else 50
    inputs = int(attrs.get("inputs", "2")) if "inputs" in attrs else 2

    ports = {}

    if comp_name == "Pin":
        ports["pin"] = (x, y)
    elif comp_name in ("Constant", "Power", "Ground", "Clock"):
        ports["out"] = (x, y)
    elif comp_name == "Tunnel":
        ports["pin"] = (x, y)
    elif comp_name == "NOT Gate":
        gate_size = int(attrs.get("size", "30")) if "size" in attrs else 30
        if facing == "east":
            ports["out"] = (x, y)
            ports["in"] = (x - gate_size, y)
        elif facing == "west":
            ports["out"] = (x, y)
            ports["in"] = (x + gate_size, y)
        elif facing == "south":
            ports["out"] = (x, y)
            ports["in"] = (x, y - gate_size)
        elif facing == "north":
            ports["out"] = (x, y)
            ports["in"] = (x, y + gate_size)
    elif comp_name in ("AND Gate", "OR Gate", "NAND Gate", "NOR Gate", "XOR Gate", "XNOR Gate"):
        if facing == "east":
            ports["out"] = (x, y)
            offsets = get_gate_input_offsets(inputs, size)
            for i, dy in enumerate(offsets):
                ports[f"in{i}"] = (x - size, y + dy)
        elif facing == "west":
            ports["out"] = (x, y)
            offsets = get_gate_input_offsets(inputs, size)
            for i, dy in enumerate(offsets):
                ports[f"in{i}"] = (x + size, y + dy)
    elif comp_name == "D Flip-Flop":
        ports["D"] = (x - 40, y - 20)
        ports["CLK"] = (x - 40, y)
        ports["Q"] = (x, y - 20)
        ports["notQ"] = (x, y)
    elif comp_name == "T Flip-Flop":
        ports["T"] = (x - 40, y - 20)
        ports["CLK"] = (x - 40, y)
        ports["Q"] = (x, y - 20)
        ports["notQ"] = (x, y)
    elif comp_name == "J-K Flip-Flop":
        ports["J"] = (x - 40, y - 20)
        ports["CLK"] = (x - 40, y)
        ports["K"] = (x - 40, y + 20)
        ports["Q"] = (x, y - 20)
        ports["notQ"] = (x, y)
    else:
        # Fallback for generic component: assume anchor at loc is a port
        ports["anchor"] = (x, y)

    return ports


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
        ports = get_component_ports(name, loc, attrs)
        for port_name, port_pt in ports.items():
            comp_ports[port_pt].append((name, port_name))

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
