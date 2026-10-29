# LogisimSkill ⚡

[![Validation Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Logisim Engine](https://img.shields.io/badge/engine-Logisim%202.7.1%20%7C%20Evolution-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

**LogisimSkill** is an engineering framework and AI agent skill for programmatically generating, routing, and validating 100% compliant `.circ` digital logic schematics for **Logisim** and **Logisim-evolution**.

It solves the common problem of AI-generated circuits being misaligned, having diagonal wires, or missing pin coordinates by using the **exact mathematical port geometry** reverse-engineered directly from Logisim's core engine bytecode.

---

## ✨ Features

- **Automatic GUI Toolbar & Mappings:** Eliminates the missing toolbar bug in Logisim GUI mode by automatically generating `<toolbar>` (with Poke Tool, Edit Tool, Text Tool) and `<mappings>`.
- **Exact Component Geometry:** Pin-accurate coordinates for 48+ standard Logisim components across Wiring, Gates, Plexers, Arithmetic, Memory, and I/O.
- **Strict Manhattan Wire Routing:** Automatically breaks non-aligned connections into purely orthogonal ($X_1=X_2$ or $Y_1=Y_2$) segments with automatic junction creation.
- **Segmented Bus Routing:** `add_vbus` and `add_hbus` prevent overlapping collinear wires and ensure clean, reliable multi-tap junctions.
- **Canonical Logic Generators:** Ready-to-use factories for decoders (2-to-4), encoders (8-to-3, 10-to-4, N-to-M), multiplexers (4-to-1, 8-to-1), and demultiplexers (1-to-4, 1-to-8).
- **Collision-Free Ergonomic Layouts:** Built-in rules for pin spacing ($\ge 30\text{--}40$ px pitch) eliminating text and label overlaps.
- **10-Pixel Grid Snapping:** Enforces complete alignment with Logisim's internal grid.
- **Engine-Level Validation:** `validate_circ.py` checks XML validity, grid alignment, absence of diagonal lines, toolbar presence, and tests loading headlessly directly inside Logisim's Java bytecode.
- **Modular & Clean:** Standard Python API with zero external dependencies (uses standard library `xml.etree`).

---

## 🚀 Quickstart

### 1. Programmatic Circuit Generation

```python
from scripts.logisim_builder import (
    Project, Pin, AndGate, OrGate, NotGate,
    build_decoder_2to4, build_encoder_8to3,
    build_multiplexer_4to1, build_demultiplexer_1to4
)

# Create a project (automatically injects GUI toolbar & mouse mappings)
proj = Project(name="main")

# Generate standard canonical blocks with zero manual routing:
build_decoder_2to4(proj, name="main", with_enable=True)
build_encoder_8to3(proj, name="Классический_8_в_3")
build_multiplexer_4to1(proj, name="Мультиплексор_4_в_1", with_enable=True)

# Or build custom circuits using segmented bus routing:
sheet = proj.get_or_create_circuit("CustomCircuit")
pin_a = sheet.add(Pin(100, 100, label="A"))
pin_b = sheet.add(Pin(100, 140, label="B"))
and_gate = sheet.add(AndGate(240, 120, inputs=2, size=50))
out_pin = sheet.add(Pin(320, 120, label="Y", facing="west", output=True))

sheet.connect(pin_a, "pin", and_gate, "in0", routing="hv")
sheet.connect(pin_b, "pin", and_gate, "in1", routing="hv")
sheet.connect(and_gate, "out", out_pin, "pin")

# Save as .circ XML
proj.save("my_circuit.circ")
```

### 2. Validating Circuits

Run the built-in validator against any `.circ` file:

```bash
python scripts/validate_circ.py examples/half_adder.circ
```

To run engine-level headless verification using your local Logisim executable:

```bash
python scripts/validate_circ.py examples/half_adder.circ /path/to/logisim.jar
```

---

## 📂 Repository Structure

```
LogisimSkill/
├── SKILL.md                 # Antigravity Agent Skill Specification
├── README.md                # Project documentation & usage
├── .gitignore               # Clean repository filter
├── scripts/
│   ├── logisim_builder.py   # Core logic engine and component factories
│   └── validate_circ.py     # Static and engine-level circuit validator
├── examples/
│   ├── half_adder.circ      # Combinational XOR + AND half adder
│   ├── decoder_2to4.circ    # Full 2-to-4 binary decoder with NOT and AND gates
│   └── d_flip_flop_divider.circ # Sequential DFF with inverted feedback
└── tests/
    └── test_builder.py      # Unit tests & example verification suite
```

---

## 🛠️ Testing

Run the test suite:

```bash
python tests/test_builder.py
```

All 4 unit tests generate circuits, validate their geometry, and verify them against the Logisim engine parser.

---

## 📄 License

MIT License. Designed for students, digital logic designers, and AI coding assistants.
