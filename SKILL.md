---
name: logisim
description: "Author, design, and validate pixel-perfect digital logic circuit files (.circ) for Logisim 2.7.1 and Logisim-evolution. Covers exact component pin geometry, Manhattan wire routing, subcircuit modular hierarchy, multi-bit buses, arithmetic modules, flip-flops, and automated validation."
---

# Logisim Circuit Architect Skill

A complete engineering specification and workflow for generating 100% compliant, pixel-perfect `.circ` circuit files that open natively in **Logisim 2.7.1** and **Logisim-evolution** with zero graphical glitches, zero disconnects, and immediate simulation readiness.

---

## 1. Fundamental Rules of the Logisim Engine

Logisim stores digital circuits as XML files (`.circ`). Unlike hardware description languages (VHDL/Verilog) or netlist-based CAD tools (SPICE), Logisim determines electrical connectivity **purely through geometry**:

1. **Strict 10-Pixel Grid Alignment:**
   - Every component anchor `loc="(X,Y)"` and every wire endpoint `from="(X1,Y1)" to="(X2,Y2)"` **must be an integer multiple of 10**.
   - Placements that do not align to the 10px grid cause visual misalignment and fail to snap to pins.

2. **Strict Manhattan Orthogonal Routing:**
   - Logisim **only supports horizontal and vertical wire segments**:
     - Horizontal: $Y_1 = Y_2$
     - Vertical: $X_1 = X_2$
   - **Diagonal wires are strictly forbidden.** Connecting two points $(X_1, Y_1)$ and $(X_2, Y_2)$ with different $X$ and $Y$ requires at least two orthogonal segments through a corner point $(X_2, Y_1)$ or $(X_1, Y_2)$.

3. **Implicit Junction Creation:**
   - An electrical connection (junction) is formed **only** when a wire endpoint lands on:
     - An exact pin coordinate of a component.
     - An endpoint or collinear coordinate of another wire.
   - If a wire misses a pin coordinate by even 10 pixels, no connection occurs and the simulation will display blue/red error lines (`Unknown` or `Error`).

4. **Standard Library Indices:**
   A standard Logisim `.circ` file declares libraries at the root `<project>`:
   - `lib="0"`: `#Wiring` (Pin, Splitter, Probe, Tunnel, Clock, Constant, Power, Ground)
   - `lib="1"`: `#Gates` (AND, OR, NAND, NOR, XOR, XNOR, NOT, Buffer, Controlled Buffer)
   - `lib="2"`: `#Plexers` (Multiplexer, Demultiplexer, Decoder, Priority Encoder)
   - `lib="3"`: `#Arithmetic` (Adder, Subtractor, Multiplier, Divider, Comparator, Shifter)
   - `lib="4"`: `#Memory` (D/T/JK/SR Flip-Flops, Register, Counter, Shift Register, RAM, ROM)
   - `lib="5"`: `#I/O` (Button, LED, 7-Segment Display, Hex Display, Keyboard, TTY)
   - `lib="6"`: `#Base` (Text Tool, Poke Tool, Edit Tool)

---

## 2. Ground-Truth Component Pin Geometry

For a component placed at anchor `loc="(X,Y)"`, its pin positions are calculated as `(X + dx, Y + dy)`.

### 2.1 Wiring (`lib="0"`)
| Component | Default Attributes | Pin Name | dx | dy | Direction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pin (Input)** | `facing="east"`, `output="false"` | `pin` | `0` | `0` | Output to circuit |
| **Pin (Output)** | `facing="west"`, `output="true"` | `pin` | `0` | `0` | Input from circuit |
| **Clock** | `facing="east"` | `out` | `0` | `0` | Clock signal |
| **Constant** | `facing="east"`, `value="0x1"` | `out` | `0` | `0` | Output |
| **Power** | `facing="north"` | `out` | `0` | `0` | VCC |
| **Ground** | `facing="south"` | `out` | `0` | `0` | GND |
| **Tunnel** | `facing="west"` | `pin` | `0` | `0` | Shared net |
| **Splitter** | `facing="east"`, `fanout="2"` | `trunk`<br>`out0`<br>`out1` | `0`<br>`20`<br>`20` | `0`<br>`-20`<br>`-10` | Combined bus<br>Bit 0<br>Bit 1 |

---

### 2.2 Logic Gates (`lib="1"`)
Gates facing `east` have their output at `(0, 0)` relative to `loc`.

#### Standard Size (`size="50"`, medium):
| Gate | Inputs | Input 0 (`in0`) | Input 1 (`in1`) | Input 2 (`in2`) | Output (`out`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **AND Gate** | 2 | `(-50, -20)` | `(-50, 20)` | — | `(0, 0)` |
| **AND Gate** | 3 | `(-50, -20)` | `(-50, 0)` | `(-50, 20)` | `(0, 0)` |
| **OR Gate** | 2 | `(-50, -20)` | `(-50, 20)` | — | `(0, 0)` |
| **OR Gate** | 3 | `(-50, -20)` | `(-50, 0)` | `(-50, 20)` | `(0, 0)` |
| **NAND Gate** | 2 | `(-60, -20)` | `(-60, 20)` | — | `(0, 0)` |
| **NOR Gate** | 2 | `(-60, -20)` | `(-60, 20)` | — | `(0, 0)` |
| **XOR Gate** | 2 | `(-60, -20)` | `(-60, 20)` | — | `(0, 0)` |
| **XNOR Gate** | 2 | `(-70, -20)` | `(-70, 20)` | — | `(0, 0)` |

#### Narrow Size (`size="30"`):
| Gate | Inputs | Input 0 (`in0`) | Input 1 (`in1`) | Output (`out`) |
| :--- | :---: | :---: | :---: | :---: |
| **AND Gate (Narrow)** | 2 | `(-30, -10)` | `(-30, 10)` | `(0, 0)` |
| **OR Gate (Narrow)** | 2 | `(-30, -10)` | `(-30, 10)` | `(0, 0)` |
| **NOT Gate** | 1 | `(-30, 0)` | — | `(0, 0)` |
| **Buffer** | 1 | `(-20, 0)` | — | `(0, 0)` |
| **Controlled Buffer** | 1 | `in: (-20, 0)` | `ctrl: (-10, 10)` | `(0, 0)` |
| **Controlled Inverter**| 1 | `in: (-30, 0)` | `ctrl: (-20, 10)` | `(0, 0)` |

---

### 2.3 Plexers (`lib="2"`)
| Component | Select Bits | Pin Name | dx | dy | Function |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **Multiplexer** | 1 (2-to-1) | `in0`<br>`in1`<br>`sel`<br>`enable`<br>`out` | `-30`<br>`-30`<br>`-20`<br>`-10`<br>`0` | `-10`<br>`10`<br>`20`<br>`20`<br>`0` | Input 0<br>Input 1<br>Select line<br>Enable line<br>Output |
| **Demultiplexer** | 1 (1-to-2) | `in`<br>`out0`<br>`out1`<br>`sel`<br>`enable` | `0`<br>`30`<br>`30`<br>`20`<br>`10` | `0`<br>`-10`<br>`10`<br>`20`<br>`20` | Input<br>Output 0<br>Output 1<br>Select line<br>Enable line |
| **Decoder** | 1 (1-to-2) | `sel`<br>`enable`<br>`out0`<br>`out1` | `0`<br>`-10`<br>`10`<br>`10` | `0`<br>`0`<br>`-30`<br>`-10` | Select input<br>Enable input<br>Active low/high 0<br>Active low/high 1 |

---

### 2.4 Arithmetic (`lib="3"`)
All arithmetic blocks have standardized 40x40 bodies with outputs on the right and inputs on the left:
| Component | Pin Name | dx | dy | Description |
| :--- | :--- | :---: | :---: | :--- |
| **Adder** | `inA`<br>`inB`<br>`out`<br>`cin`<br>`cout` | `-40`<br>`-40`<br>`0`<br>`-20`<br>`-20` | `-10`<br>`10`<br>`0`<br>`-20`<br>`20` | Operand A<br>Operand B<br>Sum output<br>Carry In (top)<br>Carry Out (bottom) |
| **Subtractor** | `inA`<br>`inB`<br>`out`<br>`bin`<br>`bout` | `-40`<br>`-40`<br>`0`<br>`-20`<br>`-20` | `-10`<br>`10`<br>`0`<br>`-20`<br>`20` | Minuend<br>Subtrahend<br>Difference output<br>Borrow In (top)<br>Borrow Out (bottom) |
| **Comparator** | `inA`<br>`inB`<br>`gt`<br>`eq`<br>`lt` | `-40`<br>`-40`<br>`0`<br>`0`<br>`0` | `-10`<br>`10`<br>`-10`<br>`0`<br>`10` | Operand A<br>Operand B<br>A > B output<br>A = B output<br>A < B output |

---

### 2.5 Memory / Sequential Elements (`lib="4"`)
Flip-Flop bodies are 40x40. Outputs $Q$ and $\overline{Q}$ are on the right edge:
| Component | Pin Name | dx | dy | Description |
| :--- | :--- | :---: | :---: | :--- |
| **D Flip-Flop** | `d`<br>`clock`<br>`q`<br>`notq`<br>`reset`<br>`preset`<br>`enable` | `-40`<br>`-40`<br>`0`<br>`0`<br>`-10`<br>`-30`<br>`-20` | `0`<br>`20`<br>`0`<br>`20`<br>`30`<br>`30`<br>`30` | Data input<br>Clock input<br>Normal output $Q$<br>Inverted output $\overline{Q}$<br>Async Clear (bottom right)<br>Async Preset (bottom left)<br>Clock Enable (bottom center) |
| **T Flip-Flop** | `t`<br>`clock`<br>`q`<br>`notq` | `-40`<br>`-40`<br>`0`<br>`0` | `0`<br>`20`<br>`0`<br>`20` | Toggle input<br>Clock input<br>$Q$<br>$\overline{Q}$ |
| **J-K Flip-Flop** | `j`<br>`clock`<br>`k`<br>`q`<br>`notq` | `-40`<br>`-40`<br>`-40`<br>`0`<br>`0` | `0`<br>`10`<br>`20`<br>`0`<br>`20` | J input<br>Clock input<br>K input<br>$Q$<br>$\overline{Q}$ |
| **S-R Flip-Flop** | `s`<br>`clock`<br>`r`<br>`q`<br>`notq` | `-40`<br>`-40`<br>`-40`<br>`0`<br>`0` | `0`<br>`10`<br>`20`<br>`0`<br>`20` | Set input<br>Clock input<br>Reset input<br>$Q$<br>$\overline{Q}$ |
| **Register** | `in`<br>`out`<br>`clock`<br>`clear`<br>`enable` | `-30`<br>`0`<br>`-20`<br>`-10`<br>`-30` | `0`<br>`0`<br>`20`<br>`20`<br>`10` | Parallel Data In (8-bit)<br>Parallel Data Out (8-bit)<br>Clock<br>Clear<br>Enable |
| **Counter** | `out`<br>`in`<br>`clock`<br>`clear`<br>`load`<br>`count`<br>`carry` | `0`<br>`-30`<br>`-20`<br>`-10`<br>`-30`<br>`-30`<br>`0` | `0`<br>`0`<br>`20`<br>`20`<br>`-10`<br>`10`<br>`10` | Counter value out<br>Parallel load in<br>Clock<br>Clear<br>Load enable<br>Count enable<br>Carry output |

---

## 3. High-Level Python Engine API

The skill includes a dedicated Python API in `scripts/logisim_builder.py` allowing instant programmatic schematic construction:

```python
from logisim_builder import Project, Pin, AndGate, OrGate, NotGate

# 1. Initialize project
proj = Project(name="main")
c = proj.main

# 2. Add components with exact coordinates
pin_a = c.add(Pin(100, 100, label="A"))
pin_b = c.add(Pin(100, 140, label="B"))
and_gate = c.add(AndGate(240, 120, inputs=2, size=50))
out_pin = c.add(Pin(320, 120, label="Y", facing="west", output=True))

# 3. Connect via orthogonal Manhattan routing
c.connect(pin_a, "pin", and_gate, "in0", routing="hv")
c.connect(pin_b, "pin", and_gate, "in1", routing="hv")
c.connect(and_gate, "out", out_pin, "pin")

# 4. Save to validated .circ XML
proj.save("and_logic.circ")
```

---

## 4. Verification and Quality Checklist

Before finalizing any `.circ` file, verify:

1. **All coordinates are multiples of 10.**
2. **Every wire has either $X_1 = X_2$ or $Y_1 = Y_2$.**
3. **No loose wire ends near pins:** Check that input/output connections touch the exact pin offsets.
4. **Output pins face west (`facing="west"`, `output="true"`):** This places the wire contact on the left side facing inward.
5. **Bus widths match:** If a pin or gate is 4-bit, the connected wire and destination port must also support 4 bits.
6. **Execute automated validator:**
   ```bash
   python scripts/validate_circ.py <path_to_circuit.circ> [path_to_logisim.jar]
   ```
