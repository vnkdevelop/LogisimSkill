"""
Logisim Circuit Builder Engine
==============================
High-precision programmatic logic circuit designer and XML generator for
Logisim 2.7.1 and Logisim-evolution.

Guarantees 100% mathematical snapping to the 10px grid, strict Manhattan
routing (orthogonal wires only), and verified pin geometry for all standard
components.
"""

from __future__ import annotations
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List, Tuple, Optional, Union, Any


class Coordinate:
    def __init__(self, x: int, y: int):
        if x % 10 != 0 or y % 10 != 0:
            # Snap to nearest 10 for safety
            x = round(x / 10.0) * 10
            y = round(y / 10.0) * 10
        self.x = int(x)
        self.y = int(y)

    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def __str__(self) -> str:
        return f"({self.x},{self.y})"

    def __repr__(self) -> str:
        return f"Coordinate({self.x}, {self.y})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Coordinate):
            return self.x == other.x and self.y == other.y
        if isinstance(other, (tuple, list)) and len(other) == 2:
            return self.x == other[0] and self.y == other[1]
        return False

    def __hash__(self) -> int:
        return hash((self.x, self.y))


class Wire:
    """Represents an orthogonal wire segment between two points."""
    def __init__(self, p1: Union[Coordinate, Tuple[int, int]], p2: Union[Coordinate, Tuple[int, int]]):
        self.p1 = p1 if isinstance(p1, Coordinate) else Coordinate(p1[0], p1[1])
        self.p2 = p2 if isinstance(p2, Coordinate) else Coordinate(p2[0], p2[1])

        # Normalize endpoints: min coordinate first for deduplication
        if (self.p1.x, self.p1.y) > (self.p2.x, self.p2.y):
            self.p1, self.p2 = self.p2, self.p1

        if not self.is_orthogonal():
            raise ValueError(f"Diagonal wire not allowed in Logisim: {self.p1} -> {self.p2}")

    def is_orthogonal(self) -> bool:
        return self.p1.x == self.p2.x or self.p1.y == self.p2.y

    def is_zero_length(self) -> bool:
        return self.p1 == self.p2

    def to_xml(self) -> ET.Element:
        elem = ET.Element("wire")
        elem.set("from", str(self.p1))
        elem.set("to", str(self.p2))
        return elem

    def __repr__(self) -> str:
        return f"Wire({self.p1} -> {self.p2})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Wire):
            return self.p1 == other.p1 and self.p2 == other.p2
        return False

    def __hash__(self) -> int:
        return hash((self.p1.to_tuple(), self.p2.to_tuple()))


class Component:
    """Represents a component on the Logisim canvas."""
    def __init__(
        self,
        lib: int,
        name: str,
        loc: Union[Coordinate, Tuple[int, int]],
        attrs: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, Tuple[int, int]]] = None
    ):
        self.lib = lib
        self.name = name
        self.loc = loc if isinstance(loc, Coordinate) else Coordinate(loc[0], loc[1])
        self.attrs = attrs or {}
        self.ports = ports or {}

    def get_port(self, port_name: str) -> Coordinate:
        """Returns the absolute coordinate of a named port."""
        if port_name not in self.ports:
            raise KeyError(f"Port '{port_name}' not defined for component '{self.name}'. Available: {list(self.ports.keys())}")
        dx, dy = self.ports[port_name]
        return Coordinate(self.loc.x + dx, self.loc.y + dy)

    def to_xml(self) -> ET.Element:
        elem = ET.Element("comp")
        elem.set("lib", str(self.lib))
        elem.set("loc", str(self.loc))
        elem.set("name", self.name)
        for attr_name, attr_val in self.attrs.items():
            if attr_val is not None:
                a_elem = ET.SubElement(elem, "a")
                a_elem.set("name", attr_name)
                a_elem.set("val", str(attr_val))
        return elem


# ==============================================================================
# Verified Component Factories (exact Logisim 2.7.1 & Evolution geometry)
# ==============================================================================

def Pin(
    x: int,
    y: int,
    label: str = "",
    facing: str = "east",
    output: bool = False,
    width: int = 1,
    tristate: bool = False,
    labelloc: str = "west"
) -> Component:
    attrs = {
        "facing": facing,
        "tristate": "true" if tristate else "false",
        "label": label,
        "labelloc": labelloc
    }
    if output:
        attrs["output"] = "true"
        if facing == "west":
            attrs["labelloc"] = "east"
    if width > 1:
        attrs["width"] = str(width)

    # Pin anchor is its connection tip at (0, 0)
    ports = {"pin": (0, 0)}
    return Component(lib=0, name="Pin", loc=(x, y), attrs=attrs, ports=ports)


def Clock(x: int, y: int, label: str = "CLK", high_duration: int = 1, low_duration: int = 1) -> Component:
    attrs = {"label": label, "labelloc": "west"}
    if high_duration != 1:
        attrs["highDuration"] = str(high_duration)
    if low_duration != 1:
        attrs["lowDuration"] = str(low_duration)
    return Component(lib=0, name="Clock", loc=(x, y), attrs=attrs, ports={"out": (0, 0)})


def Constant(x: int, y: int, value: int = 1, width: int = 1) -> Component:
    attrs = {"value": hex(value)}
    if width > 1:
        attrs["width"] = str(width)
    return Component(lib=0, name="Constant", loc=(x, y), attrs=attrs, ports={"out": (0, 0)})


def Ground(x: int, y: int, width: int = 1) -> Component:
    attrs = {}
    if width > 1:
        attrs["width"] = str(width)
    return Component(lib=0, name="Ground", loc=(x, y), attrs=attrs, ports={"out": (0, 0)})


def Power(x: int, y: int, width: int = 1) -> Component:
    attrs = {}
    if width > 1:
        attrs["width"] = str(width)
    return Component(lib=0, name="Power", loc=(x, y), attrs=attrs, ports={"out": (0, 0)})


def Tunnel(x: int, y: int, label: str, width: int = 1, facing: str = "west") -> Component:
    attrs = {"label": label, "facing": facing}
    if width > 1:
        attrs["width"] = str(width)
    return Component(lib=0, name="Tunnel", loc=(x, y), attrs=attrs, ports={"pin": (0, 0)})


def Splitter(
    x: int,
    y: int,
    incoming: int = 2,
    fanout: int = 2,
    facing: str = "east",
    appear: str = "left"
) -> Component:
    attrs = {
        "facing": facing,
        "incoming": str(incoming),
        "fanout": str(fanout),
        "appear": appear
    }
    # Main trunk port at (0, 0)
    ports = {"trunk": (0, 0)}
    # Splitter branch offsets depend on fanout and facing
    # For default facing="east", appear="left":
    # Branch 0: (20, -10 * fanout)
    for i in range(fanout):
        if facing == "east":
            ports[f"out{i}"] = (20, -10 * (fanout - i))
        elif facing == "west":
            ports[f"out{i}"] = (-20, -10 * (fanout - i))
    return Component(lib=0, name="Splitter", loc=(x, y), attrs=attrs, ports=ports)


# Logic Gates (exact pin offsets from Logisim engine)

def _calc_gate_inputs(size: int, inputs: int, bonus_width: int = 0) -> List[Tuple[int, int]]:
    """Calculates input pin (dx, dy) offsets for an East-facing gate."""
    total_width = size + bonus_width
    dx = -total_width
    offsets = []

    if inputs <= 3:
        if size < 40: # Narrow (30)
            delta, step, skip = -5, 10, 10
        elif size >= 60 or inputs <= 2:
            delta, step, skip = -10, 20, 20
        else: # size 50, inputs 3
            delta, step, skip = -10, 20, 20
    elif inputs == 4 and size >= 60:
        delta, step, skip = -5, 20, 0
    else:
        delta, step, skip = -5, 10, 10

    for i in range(inputs):
        if inputs % 2 == 1:
            dy = delta * (inputs - 1) + step * i
        else:
            dy = delta * inputs + step * i
            if i >= inputs // 2:
                dy += skip
        offsets.append((dx, dy))
    return offsets


def AndGate(x: int, y: int, inputs: int = 2, size: int = 50, label: str = "") -> Component:
    attrs = {"size": str(size), "inputs": str(inputs)}
    if label:
        attrs["label"] = label
    input_offsets = _calc_gate_inputs(size, inputs, bonus_width=0)
    ports = {"out": (0, 0)}
    for i, off in enumerate(input_offsets):
        ports[f"in{i}"] = off
    return Component(lib=1, name="AND Gate", loc=(x, y), attrs=attrs, ports=ports)


def OrGate(x: int, y: int, inputs: int = 2, size: int = 50, label: str = "") -> Component:
    attrs = {"size": str(size), "inputs": str(inputs)}
    if label:
        attrs["label"] = label
    input_offsets = _calc_gate_inputs(size, inputs, bonus_width=0)
    ports = {"out": (0, 0)}
    for i, off in enumerate(input_offsets):
        ports[f"in{i}"] = off
    return Component(lib=1, name="OR Gate", loc=(x, y), attrs=attrs, ports=ports)


def NandGate(x: int, y: int, inputs: int = 2, size: int = 50, label: str = "") -> Component:
    attrs = {"size": str(size), "inputs": str(inputs)}
    if label:
        attrs["label"] = label
    # Bubble adds 10px width
    input_offsets = _calc_gate_inputs(size, inputs, bonus_width=10)
    ports = {"out": (0, 0)}
    for i, off in enumerate(input_offsets):
        ports[f"in{i}"] = off
    return Component(lib=1, name="NAND Gate", loc=(x, y), attrs=attrs, ports=ports)


def NorGate(x: int, y: int, inputs: int = 2, size: int = 50, label: str = "") -> Component:
    attrs = {"size": str(size), "inputs": str(inputs)}
    if label:
        attrs["label"] = label
    input_offsets = _calc_gate_inputs(size, inputs, bonus_width=10)
    ports = {"out": (0, 0)}
    for i, off in enumerate(input_offsets):
        ports[f"in{i}"] = off
    return Component(lib=1, name="NOR Gate", loc=(x, y), attrs=attrs, ports=ports)


def XorGate(x: int, y: int, inputs: int = 2, size: int = 50, label: str = "") -> Component:
    attrs = {"size": str(size), "inputs": str(inputs)}
    if label:
        attrs["label"] = label
    input_offsets = _calc_gate_inputs(size, inputs, bonus_width=10)
    ports = {"out": (0, 0)}
    for i, off in enumerate(input_offsets):
        ports[f"in{i}"] = off
    return Component(lib=1, name="XOR Gate", loc=(x, y), attrs=attrs, ports=ports)


def XnorGate(x: int, y: int, inputs: int = 2, size: int = 50, label: str = "") -> Component:
    attrs = {"size": str(size), "inputs": str(inputs)}
    if label:
        attrs["label"] = label
    input_offsets = _calc_gate_inputs(size, inputs, bonus_width=20)
    ports = {"out": (0, 0)}
    for i, off in enumerate(input_offsets):
        ports[f"in{i}"] = off
    return Component(lib=1, name="XNOR Gate", loc=(x, y), attrs=attrs, ports=ports)


def NotGate(x: int, y: int, size: int = 30, label: str = "") -> Component:
    attrs = {"size": str(size)}
    if label:
        attrs["label"] = label
    ports = {"out": (0, 0), "in": (-size, 0)}
    return Component(lib=1, name="NOT Gate", loc=(x, y), attrs=attrs, ports=ports)


def Buffer(x: int, y: int, label: str = "") -> Component:
    attrs = {}
    if label:
        attrs["label"] = label
    ports = {"out": (0, 0), "in": (-20, 0)}
    return Component(lib=1, name="Buffer", loc=(x, y), attrs=attrs, ports=ports)


def ControlledBuffer(x: int, y: int, control: str = "right") -> Component:
    attrs = {"control": control}
    ports = {"out": (0, 0), "in": (-20, 0), "ctrl": (-10, 10 if control == "right" else -10)}
    return Component(lib=1, name="Controlled Buffer", loc=(x, y), attrs=attrs, ports=ports)


def ControlledInverter(x: int, y: int, size: int = 30, control: str = "right") -> Component:
    attrs = {"size": str(size), "control": control}
    ports = {"out": (0, 0), "in": (-size, 0), "ctrl": (-20, 10 if control == "right" else -10)}
    return Component(lib=1, name="Controlled Inverter", loc=(x, y), attrs=attrs, ports=ports)


# Plexers (Multiplexers & Decoders)

def Multiplexer(x: int, y: int, select: int = 1, width: int = 1) -> Component:
    attrs = {"select": str(select)}
    if width > 1:
        attrs["width"] = str(width)
    ports = {
        "out": (0, 0),
        "sel": (-20, 20),
        "enable": (-10, 20)
    }
    inputs_count = 1 << select
    for i in range(inputs_count):
        ports[f"in{i}"] = (-30, -10 * (inputs_count - 1) + 20 * i)
    return Component(lib=2, name="Multiplexer", loc=(x, y), attrs=attrs, ports=ports)


def Demultiplexer(x: int, y: int, select: int = 1, width: int = 1) -> Component:
    attrs = {"select": str(select)}
    if width > 1:
        attrs["width"] = str(width)
    ports = {
        "in": (0, 0),
        "sel": (20, 20),
        "enable": (10, 20)
    }
    outputs_count = 1 << select
    for i in range(outputs_count):
        ports[f"out{i}"] = (30, -10 * (outputs_count - 1) + 20 * i)
    return Component(lib=2, name="Demultiplexer", loc=(x, y), attrs=attrs, ports=ports)


def Decoder(x: int, y: int, select: int = 1) -> Component:
    attrs = {"select": str(select)}
    outputs_count = 1 << select
    ports = {
        "sel": (0, 0),
        "enable": (-10, 0)
    }
    for i in range(outputs_count):
        ports[f"out{i}"] = (10, -10 - 20 * (outputs_count - 1 - i))
    return Component(lib=2, name="Decoder", loc=(x, y), attrs=attrs, ports=ports)


# Arithmetic Modules

def Adder(x: int, y: int, width: int = 8) -> Component:
    attrs = {"width": str(width)}
    ports = {
        "inA": (-40, -10),
        "inB": (-40, 10),
        "out": (0, 0),
        "cin": (-20, -20),
        "cout": (-20, 20)
    }
    return Component(lib=3, name="Adder", loc=(x, y), attrs=attrs, ports=ports)


def Subtractor(x: int, y: int, width: int = 8) -> Component:
    attrs = {"width": str(width)}
    ports = {
        "inA": (-40, -10),
        "inB": (-40, 10),
        "out": (0, 0),
        "bin": (-20, -20),
        "bout": (-20, 20)
    }
    return Component(lib=3, name="Subtractor", loc=(x, y), attrs=attrs, ports=ports)


def Comparator(x: int, y: int, width: int = 8, mode: str = "twosComplement") -> Component:
    attrs = {"width": str(width), "mode": mode}
    ports = {
        "inA": (-40, -10),
        "inB": (-40, 10),
        "gt": (0, -10),
        "eq": (0, 0),
        "lt": (0, 10)
    }
    return Component(lib=3, name="Comparator", loc=(x, y), attrs=attrs, ports=ports)


# Memory / Sequential Elements

def DFlipFlop(x: int, y: int, trigger: str = "rising", label: str = "") -> Component:
    attrs = {"trigger": trigger}
    if label:
        attrs["label"] = label
    ports = {
        "d": (-40, 0),
        "clock": (-40, 20),
        "q": (0, 0),
        "notq": (0, 20),
        "reset": (-10, 30),
        "preset": (-30, 30),
        "enable": (-20, 30)
    }
    return Component(lib=4, name="D Flip-Flop", loc=(x, y), attrs=attrs, ports=ports)


def TFlipFlop(x: int, y: int, trigger: str = "rising", label: str = "") -> Component:
    attrs = {"trigger": trigger}
    if label:
        attrs["label"] = label
    ports = {
        "t": (-40, 0),
        "clock": (-40, 20),
        "q": (0, 0),
        "notq": (0, 20),
        "reset": (-10, 30),
        "preset": (-30, 30),
        "enable": (-20, 30)
    }
    return Component(lib=4, name="T Flip-Flop", loc=(x, y), attrs=attrs, ports=ports)


def JKFlipFlop(x: int, y: int, trigger: str = "rising", label: str = "") -> Component:
    attrs = {"trigger": trigger}
    if label:
        attrs["label"] = label
    ports = {
        "j": (-40, 0),
        "clock": (-40, 10),
        "k": (-40, 20),
        "q": (0, 0),
        "notq": (0, 20),
        "reset": (-10, 30),
        "preset": (-30, 30),
        "enable": (-20, 30)
    }
    return Component(lib=4, name="J-K Flip-Flop", loc=(x, y), attrs=attrs, ports=ports)


def SRFlipFlop(x: int, y: int, trigger: str = "rising", label: str = "") -> Component:
    attrs = {"trigger": trigger}
    if label:
        attrs["label"] = label
    ports = {
        "s": (-40, 0),
        "clock": (-40, 10),
        "r": (-40, 20),
        "q": (0, 0),
        "notq": (0, 20),
        "reset": (-10, 30),
        "preset": (-30, 30),
        "enable": (-20, 30)
    }
    return Component(lib=4, name="S-R Flip-Flop", loc=(x, y), attrs=attrs, ports=ports)


def Register(x: int, y: int, width: int = 8, trigger: str = "rising", label: str = "") -> Component:
    attrs = {"width": str(width), "trigger": trigger}
    if label:
        attrs["label"] = label
    ports = {
        "in": (-30, 0),
        "out": (0, 0),
        "clock": (-20, 20),
        "clear": (-10, 20),
        "enable": (-30, 10)
    }
    return Component(lib=4, name="Register", loc=(x, y), attrs=attrs, ports=ports)


def Counter(x: int, y: int, width: int = 8, max_val: int = 255, trigger: str = "rising", label: str = "") -> Component:
    attrs = {"width": str(width), "max": hex(max_val), "trigger": trigger}
    if label:
        attrs["label"] = label
    ports = {
        "out": (0, 0),
        "in": (-30, 0),
        "clock": (-20, 20),
        "clear": (-10, 20),
        "load": (-30, -10),
        "count": (-30, 10),
        "carry": (0, 10)
    }
    return Component(lib=4, name="Counter", loc=(x, y), attrs=attrs, ports=ports)


# I/O Elements

def Led(x: int, y: int, label: str = "", color: str = "r=240,g=0,b=0") -> Component:
    attrs = {"color": f"java.awt.Color[{color}]"}
    if label:
        attrs["label"] = label
    return Component(lib=5, name="LED", loc=(x, y), attrs=attrs, ports={"in": (0, 0)})


def SevenSegment(x: int, y: int) -> Component:
    ports = {
        "a": (10, 0),
        "b": (20, 0),
        "c": (20, 60),
        "d": (10, 60),
        "e": (0, 60),
        "f": (0, 0),
        "g": (30, 0),
        "dp": (30, 60)
    }
    return Component(lib=5, name="7-Segment Display", loc=(x, y), attrs={}, ports=ports)


def HexDigitDisplay(x: int, y: int) -> Component:
    ports = {
        "data": (0, 0),
        "dp": (10, 0)
    }
    return Component(lib=5, name="Hex Digit Display", loc=(x, y), attrs={}, ports=ports)


def Text(x: int, y: int, text: str, font: str = "SansSerif plain 12", halign: str = "center") -> Component:
    attrs = {"text": text, "font": font, "halign": halign}
    return Component(lib=6, name="Text", loc=(x, y), attrs=attrs, ports={})


# ==============================================================================
# Circuit and Project Container
# ==============================================================================

class Circuit:
    """Represents a single circuit sheet containing components and wires."""
    def __init__(self, name: str = "main"):
        self.name = name
        self.components: List[Component] = []
        self.wires: set[Wire] = set()

    def add(self, comp: Component) -> Component:
        self.components.append(comp)
        return comp

    def wire(
        self,
        p1: Union[Coordinate, Tuple[int, int]],
        p2: Union[Coordinate, Tuple[int, int]],
        routing: str = "hv"
    ) -> List[Wire]:
        """
        Adds orthogonal Manhattan wire segment(s) between p1 and p2.
        routing:
          'hv' -> horizontal segment first (p1.x, p1.y -> p2.x, p1.y), then vertical to (p2.x, p2.y)
          'vh' -> vertical segment first (p1.x, p1.y -> p1.x, p2.y), then horizontal to (p2.x, p2.y)
        """
        c1 = p1 if isinstance(p1, Coordinate) else Coordinate(p1[0], p1[1])
        c2 = p2 if isinstance(p2, Coordinate) else Coordinate(p2[0], p2[1])

        if c1 == c2:
            return []

        added = []
        if c1.x == c2.x or c1.y == c2.y:
            # Already orthogonal
            w = Wire(c1, c2)
            self.wires.add(w)
            added.append(w)
        else:
            # Need 2 orthogonal segments via corner point
            if routing == "hv":
                corner = Coordinate(c2.x, c1.y)
            else:
                corner = Coordinate(c1.x, c2.y)

            w1 = Wire(c1, corner)
            w2 = Wire(corner, c2)
            self.wires.add(w1)
            self.wires.add(w2)
            added.extend([w1, w2])
        return added

    def connect(
        self,
        comp1: Component,
        port1: str,
        comp2: Component,
        port2: str,
        routing: str = "hv"
    ) -> List[Wire]:
        """Connects port1 of comp1 to port2 of comp2 via orthogonal wires."""
        pt1 = comp1.get_port(port1)
        pt2 = comp2.get_port(port2)
        return self.wire(pt1, pt2, routing=routing)

    def to_xml(self) -> ET.Element:
        elem = ET.Element("circuit")
        elem.set("name", self.name)
        a_name = ET.SubElement(elem, "a")
        a_name.set("name", "circuit")
        a_name.set("val", self.name)
        a_clabel = ET.SubElement(elem, "a")
        a_clabel.set("name", "clabel")
        a_clabel.set("val", "")
        a_clabelup = ET.SubElement(elem, "a")
        a_clabelup.set("name", "clabelup")
        a_clabelup.set("val", "east")
        a_clabelfont = ET.SubElement(elem, "a")
        a_clabelfont.set("name", "clabelfont")
        a_clabelfont.set("val", "SansSerif plain 12")

        # Sorted wires for deterministic XML output
        for w in sorted(self.wires, key=lambda wire: (wire.p1.x, wire.p1.y, wire.p2.x, wire.p2.y)):
            elem.append(w.to_xml())

        for c in self.components:
            elem.append(c.to_xml())

        return elem


class Project:
    """Represents a full Logisim .circ file."""
    def __init__(self, name: str = "main", source: str = "2.7.1"):
        self.source = source
        self.circuits: Dict[str, Circuit] = {}
        self.main_circuit_name = name
        self.get_or_create_circuit(name)

    def get_or_create_circuit(self, name: str) -> Circuit:
        if name not in self.circuits:
            self.circuits[name] = Circuit(name)
        return self.circuits[name]

    @property
    def main(self) -> Circuit:
        return self.circuits[self.main_circuit_name]

    def to_xml_string(self) -> str:
        root = ET.Element("project")
        root.set("source", self.source)
        root.set("version", "1.0")

        # Standard Logisim libraries
        libs = [
            (0, "#Wiring"),
            (1, "#Gates"),
            (2, "#Plexers"),
            (3, "#Arithmetic"),
            (4, "#Memory"),
            (5, "#I/O"),
            (6, "#Base")
        ]
        for idx, desc in libs:
            lib_elem = ET.SubElement(root, "lib")
            lib_elem.set("desc", desc)
            lib_elem.set("name", str(idx))

        main_elem = ET.SubElement(root, "main")
        main_elem.set("name", self.main_circuit_name)

        options_elem = ET.SubElement(root, "options")
        a_gate = ET.SubElement(options_elem, "a")
        a_gate.set("name", "gateUndefined")
        a_gate.set("val", "ignore")
        a_simlimit = ET.SubElement(options_elem, "a")
        a_simlimit.set("name", "simlimit")
        a_simlimit.set("val", "1000")
        a_simrand = ET.SubElement(options_elem, "a")
        a_simrand.set("name", "simrand")
        a_simrand.set("val", "0")

        for c in self.circuits.values():
            root.append(c.to_xml())

        # Format XML cleanly
        xml_str = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(xml_str)
        pretty = parsed.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")

        # Logisim expects <?xml ... standalone="no"?> on line 1 followed by project
        lines = pretty.splitlines()
        clean_lines = [lines[0]]
        # Skip empty lines
        for l in lines[1:]:
            if l.strip():
                clean_lines.append(l)
        return "\n".join(clean_lines) + "\n"

    def save(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_xml_string())
