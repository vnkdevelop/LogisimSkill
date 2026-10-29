---
name: logisim
description: "Author, design, and validate pixel-perfect digital logic circuit files (.circ) for Logisim 2.7.1 and Logisim-evolution. Covers exact component pin geometry, Manhattan wire routing, subcircuit modular hierarchy, multi-bit buses, arithmetic modules, flip-flops, and automated validation."
---

# Logisim Circuit Architect Skill

A complete engineering specification and workflow for generating 100% compliant, pixel-perfect `.circ` circuit files that open natively in **Logisim 2.7.1** and **Logisim-evolution** with zero graphical glitches, full GUI toolbar interactivity, zero disconnects, and immediate simulation readiness.

---

## 1. Zero-Exploration Generation Protocol (No Scratch Scripts Needed)

When tasked with generating a Logisim schematic, **never create temporary discovery scripts or trial-and-error tests**. All component pin offsets, gate geometries, bus distribution methods, and canonical circuit topologies are exhaustively documented in this skill and implemented in `scripts/logisim_builder.py`.

You can immediately generate final `.circ` files using either:
1. **The Python Builder API** (`from scripts.logisim_builder import Project, Pin, AndGate, OrGate, ...`).
2. **Pre-built Canonical Generators** (`build_decoder_2to4`, `build_encoder_n_to_m`, `build_multiplexer_8to1`, `build_demultiplexer_1to8`).
3. **Direct XML synthesis** following the exact schemas and templates provided below.

---

## 2. Mandatory GUI Toolbar & Mouse Mappings

### 2.1 The Missing Toolbar Bug
When Logisim loads a `.circ` file that lacks `<toolbar>` and `<mappings>` elements inside the root `<project>`, it initializes in a **stripped/headless view mode**:
- The top toolbar is completely absent.
- The **Poke Tool** (Hand tool `lib="6" name="Poke Tool"`), **Edit Tool** (Selection arrow), and **Text Tool** disappear.
- The user is unable to click input pins, toggle signals, or interact with the simulation.

### 2.2 Mandatory XML Block
Every generated `.circ` file **must** include the following blocks directly after `<options>` in the `<project>` tag:

```xml
  <mappings>
    <tool lib="6" map="Button2" name="Menu Tool"/>
    <tool lib="6" map="Button3" name="Menu Tool"/>
    <tool lib="6" map="Ctrl Button1" name="Menu Tool"/>
  </mappings>
  <toolbar>
    <tool lib="6" name="Poke Tool"/>
    <tool lib="6" name="Edit Tool"/>
    <tool lib="6" name="Text Tool">
      <a name="text" val=""/>
      <a name="font" val="SansSerif plain 12"/>
      <a name="halign" val="center"/>
      <a name="valign" val="base"/>
    </tool>
    <sep/>
    <tool lib="0" name="Pin">
      <a name="tristate" val="false"/>
    </tool>
    <tool lib="0" name="Pin">
      <a name="facing" val="west"/>
      <a name="output" val="true"/>
      <a name="labelloc" val="east"/>
    </tool>
    <tool lib="1" name="NOT Gate"/>
    <tool lib="1" name="AND Gate"/>
    <tool lib="1" name="OR Gate"/>
  </toolbar>
```

> [!NOTE]
> `Project.to_xml_string()` and `Project.save()` in `logisim_builder.py` automatically inject this entire block by default.

---

## 3. Ergonomic Layout & Wiring Principles

### 3.1 Strict 10-Pixel Grid Alignment
- Every component anchor `loc="(X,Y)"` and every wire endpoint `from="(X1,Y1)" to="(X2,Y2)"` **must be an integer multiple of 10**.
- Odd coordinates (e.g. 15, 25, 175) corrupt pin alignment and cause floating unconnected wires.

### 3.2 Manhattan Orthogonal Routing Only
- Logisim **only supports horizontal and vertical wire segments**:
  - Horizontal: $Y_1 = Y_2$
  - Vertical: $X_1 = X_2$
- **Diagonal wires are strictly forbidden.** Connecting two points $(X_1, Y_1)$ and $(X_2, Y_2)$ requires two orthogonal segments connected through a corner point $(X_2, Y_1)$ or $(X_1, Y_2)$.

### 3.3 Pin Pitch & Label Clearance Rules
- **Vertical Pin Arrays:** Place pins vertically on the left with a pitch of **$\ge 30\text{--}40$ px** (e.g., $Y = 100, 130, 160, 190 \dots$).
- **Label Orientation:**
  - Left-hand inputs: `facing="east"`, `labelloc="west"`.
  - Right-hand outputs: `facing="west"`, `output="true"`, `labelloc="east"`.
- **Horizontal Pin Warning:** Placing pins horizontally side-by-side with $\le 20$ px pitch causes severe label collisions (e.g. "X18" and "X19" overlapping). Always maintain $\ge 40$ px if horizontal placement is unavoidable, but prefer vertical arrays for multi-bit inputs.

### 3.4 Segmented Bus Routing (`add_vbus` and `add_hbus`)
- When tapping a bus line at multiple points, **never draw a single continuous wire across all taps**. In Logisim, overlapping collinear wire segments can cause phantom shorts or failing T-junctions.
- Always use segmented lines between consecutive tap coordinates:
  - For vertical bus at $X$ with taps at $Y_0, Y_1, Y_2$: create wire $(X, Y_0) \to (X, Y_1)$ and wire $(X, Y_1) \to (X, Y_2)$.
  - Helper methods `c.add_vbus(x, [y0, y1, y2])` and `c.add_hbus(y, [x0, x1, x2])` automatically sort coordinates and create clean point-to-point subsegments.

### 3.5 Multi-Circuit Architecture
- In academic laboratory assignments and modular designs:
  - Put the specific assigned variant in the `main` circuit.
  - Put standard classical reference designs (e.g., `Классический_8_в_3`, `Дешифратор_2_в_4_без_E`) as additional named subcircuits in the same `.circ` file.
  - This allows instructors and students to inspect both the textbook base circuit and the assigned variant in a single file.

---

## 4. Ground-Truth Component Pin Geometry

For a component placed at anchor `loc="(X,Y)"`, its pin positions are calculated as `(X + dx, Y + dy)`.

### 4.1 Wiring (`lib="0"`)
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

### 4.2 Logic Gates (`lib="1"`)
Gates facing `east` have their output at `(0, 0)` relative to `loc`.

#### Standard Size (`size="50"`, medium):
| Gate | Inputs | Input Pin Offsets `(dx, dy)` |
| :--- | :---: | :--- |
| **AND Gate** | 2 | `in0: (-50, -20)`, `in1: (-50, 20)` |
| **AND Gate** | 3 | `in0: (-50, -20)`, `in1: (-50, 0)`, `in2: (-50, 20)` |
| **AND Gate** | 4 | `in0: (-50, -20)`, `in1: (-50, -10)`, `in2: (-50, 10)`, `in3: (-50, 20)` |
| **AND Gate** | 5 | `in0: (-50, -20)`, `in1: (-50, -10)`, `in2: (-50, 0)`, `in3: (-50, 10)`, `in4: (-50, 20)` |
| **AND Gate** | 8 | `(-50, -40)`, `(-50, -30)`, `(-50, -20)`, `(-50, -10)`, `(-50, 10)`, `(-50, 20)`, `(-50, 30)`, `(-50, 40)` |
| **OR Gate** | 2 | `in0: (-50, -20)`, `in1: (-50, 20)` |
| **OR Gate** | 3 | `in0: (-50, -20)`, `in1: (-50, 0)`, `in2: (-50, 20)` |
| **OR Gate** | 4 | `in0: (-50, -20)`, `in1: (-50, -10)`, `in2: (-50, 10)`, `in3: (-50, 20)` |
| **OR Gate** | 5 | `in0: (-50, -20)`, `in1: (-50, -10)`, `in2: (-50, 0)`, `in3: (-50, 10)`, `in4: (-50, 20)` |
| **OR Gate** | 8 | `(-50, -40)`, `(-50, -30)`, `(-50, -20)`, `(-50, -10)`, `(-50, 10)`, `(-50, 20)`, `(-50, 30)`, `(-50, 40)` |
| **NAND Gate** | 2 | `in0: (-60, -20)`, `in1: (-60, 20)` (bubble adds 10px width) |
| **NOR Gate** | 2 | `in0: (-60, -20)`, `in1: (-60, 20)` |
| **XOR Gate** | 2 | `in0: (-60, -20)`, `in1: (-60, 20)` |

#### Narrow Size (`size="30"`):
| Gate | Inputs | Input Pin Offsets `(dx, dy)` | Output `(dx, dy)` |
| :--- | :---: | :--- | :--- |
| **AND Gate (Narrow)** | 2 | `in0: (-30, -10)`, `in1: (-30, 10)` | `(0, 0)` |
| **OR Gate (Narrow)** | 2 | `in0: (-30, -10)`, `in1: (-30, 10)` | `(0, 0)` |
| **NOT Gate** | 1 | `in: (-30, 0)` | `(0, 0)` |
| **Buffer** | 1 | `in: (-20, 0)` | `(0, 0)` |

---

### 4.3 Memory / Sequential Elements (`lib="4"`)
Flip-Flop bodies are 40x40. Outputs $Q$ and $\overline{Q}$ are on the right edge:
| Component | Pin Name | dx | dy | Description |
| :--- | :--- | :---: | :---: | :--- |
| **D Flip-Flop** | `d`<br>`clock`<br>`q`<br>`notq`<br>`reset`<br>`preset`<br>`enable` | `-40`<br>`-40`<br>`0`<br>`0`<br>`-10`<br>`-30`<br>`-20` | `0`<br>`20`<br>`0`<br>`20`<br>`30`<br>`30`<br>`30` | Data input<br>Clock input<br>Normal output $Q$<br>Inverted output $\overline{Q}$<br>Async Clear<br>Async Preset<br>Clock Enable |
| **Register** | `in`<br>`out`<br>`clock`<br>`clear`<br>`enable` | `-30`<br>`0`<br>`-20`<br>`-10`<br>`-30` | `0`<br>`0`<br>`20`<br>`20`<br>`10` | Parallel Data In<br>Parallel Data Out<br>Clock<br>Clear<br>Enable |
| **Counter** | `out`<br>`in`<br>`clock`<br>`clear`<br>`load`<br>`count`<br>`carry` | `0`<br>`-30`<br>`-20`<br>`-10`<br>`-30`<br>`-30`<br>`0` | `0`<br>`0`<br>`20`<br>`20`<br>`-10`<br>`10`<br>`10` | Counter value out<br>Parallel load in<br>Clock<br>Clear<br>Load enable<br>Count enable<br>Carry output |

---

## 5. Canonical Combinational Logic Topologies

### 5.1 Дешифратор (Binary Decoder 2-to-4)
- **Boolean Functions:**
  $$Y_0 = \overline{A_1} \cdot \overline{A_0} \cdot E$$
  $$Y_1 = \overline{A_1} \cdot A_0 \cdot E$$
  $$Y_2 = A_1 \cdot \overline{A_0} \cdot E$$
  $$Y_3 = A_1 \cdot A_0 \cdot E$$
- **Implementation:**
  - 2 address inputs $A_0, A_1$, 1 enable input $E$ (strobe).
  - 2 NOT gates for address inverting.
  - 4 AND gates (3 inputs each with $E$, or 2 inputs without $E$).
  - Vertical distribution buses for $E$ ($X=100$), $A_0$ ($X=120$), $A_1$ ($X=140$), $\overline{A_0}$ ($X=220$), $\overline{A_1}$ ($X=240$).
  - Direct builder: `build_decoder_2to4(proj, name="main", with_enable=True)`.

### 5.2 Шифратор (Binary & Positional Matrix Encoders)
- **Top-to-Bottom Matrix Topology («Иксы сверху»):**
  - Standard digital and academic schematics place inputs $X_0 \dots X_{N-1}$ horizontally along the top ($Y=80$) facing south (`facing="south"`, `labelloc="north"`).
  - Horizontal spacing between pins MUST be $\Delta X = 40$ px (e.g., $X = 120 + i \times 40$). This completely eliminates text label collision.
  - From each pin $X_i$, a full vertical bus runs straight down to $Y_{bottom}$.
  - **The $X_0$ Full-Length Bus Rule:** The bus for $X_0$ is **NEVER** cut off into a 10-20px stub. It runs the entire height of the matrix alongside $X_1 \dots X_{N-1}$ down to $Y_{bottom}$.
- **General $N$-to-$M$ Positional Logic on OR Gates:**
  For $N$ inputs $X_0 \dots X_{N-1}$ and $M = \lceil\log_2 N\rceil$ output bits $Y_0 \dots Y_{M-1}$:
  $$\text{Input } X_i \text{ connects to OR gate } Y_k \iff ((i \gg k) \ \& \ 1) == 1$$
- **Real-World Activity / Validation Output ($V$ / $A$ / $GS$):**
  In real encoder ICs (e.g. 74148, К555ИВ1), input $X_0$ encodes $00000_2$. To distinguish between $X_0$ being pressed vs no inputs being pressed, an Activity gate $V$ ($V = X_0 \lor X_1 \lor \dots \lor X_{N-1}$) is placed at the bottom, connecting $X_0$ actively into the circuit.
- **8-to-3 Octal Encoder:**
  - $Y_0 = X_1 + X_3 + X_5 + X_7$ (4-input OR)
  - $Y_1 = X_2 + X_3 + X_6 + X_7$ (4-input OR)
  - $Y_2 = X_4 + X_5 + X_6 + X_7$ (4-input OR)
  - Direct builder: `build_encoder_8to3(proj, name="Классический_8_в_3")`.
- **10-to-4 BCD Encoder:**
  - $Y_0 = X_1 + X_3 + X_5 + X_7 + X_9$ (5-input OR)
  - $Y_1 = X_2 + X_3 + X_6 + X_7$ (4-input OR)
  - $Y_2 = X_4 + X_5 + X_6 + X_7$ (4-input OR)
  - $Y_3 = X_8 + X_9$ (2-input OR)
  - Direct builder: `build_encoder_10to4_bcd(proj, name="Шифратор_10_в_4_BCD")`.
- **Variant Encoders (e.g. 20-to-5 for number 19):**
  - Use `build_matrix_encoder(proj, name="main", num_inputs=20, target_variant=19, with_valid=True)`.

### 5.3 Мультиплексор (Multiplexer 4-to-1 & 8-to-1)
- **4-to-1 Logic:**
  $$Y = (D_0 \cdot \overline{A_1} \cdot \overline{A_0} \cdot E) \lor (D_1 \cdot \overline{A_1} \cdot A_0 \cdot E) \lor (D_2 \cdot A_1 \cdot \overline{A_0} \cdot E) \lor (D_3 \cdot A_1 \cdot A_0 \cdot E)$$
- **Structure:**
  - 4 (or 8) AND gates combining each data input $D_i$ with its unique binary address minterm and enable $E$.
  - 1 final multi-input OR gate collecting all AND gate outputs into single output $Y$.
  - Direct builders: `build_multiplexer_4to1(proj)` and `build_multiplexer_8to1(proj)`.

### 5.4 Демультиплексор (Demultiplexer 1-to-4 & 1-to-8)
- **1-to-4 Logic:**
  $$Y_i = DI \cdot (\text{Address} == i) \cdot E$$
- **Structure:**
  - Single informational input $DI$, enable $E$, and address selection lines.
  - 4 (or 8) AND gates driving independent output lines $Y_0 \dots Y_3$.
  - Direct builders: `build_demultiplexer_1to4(proj)` and `build_demultiplexer_1to8(proj)`.

---

## 6. Critical Engineering Pitfalls & Post-Mortem (Архитектурные ошибки и антипаттерны)

### 6.1 Pitfall 1: Multi-Input Gate Body Expansion (Ловушка расширения высоты многовходовых вентилей)
- **Problem:** When an OR or AND gate has $> 5$ inputs (e.g. 8, 10, or 20 inputs), Logisim's `AbstractGate` dynamically expands the vertical height of the component according to:
  $$\text{Height} = \max(10 \times \text{inputs},\ \text{size})$$
  A 10-input gate expands to 110 px in height ($Y_g \pm 50$), and a 20-input gate expands to 210 px in height ($Y_g \pm 100$).
- **Symptom:** Placing adjacent gates with standard pitch ($< 120\text{--}160$ px) causes the gate bodies to visually overlap, their input pins to collide, and accidental short-circuits to form.
- **Strict Rule:** Allocate a minimum vertical pitch between multi-input gate centers:
  $$\Delta Y_{pitch} \ge \max(120,\ K_{inputs} \times 14) + 60\text{ px}$$
  Always maintain at least 40-60 px of clean canvas margin between the outermost input pins of adjacent gates.

### 6.2 Pitfall 2: Routing Horizontal Wires Through Gate Center (Ошибка короткого замыкания и красной петли)
- **Problem:** For an East-facing gate at $(X_g, Y_g)$, its **OUTPUT PIN** is located exactly at $(X_g, Y_g)$. For an even number of inputs (2, 4, 8, 10 inputs), input pins are distributed symmetrically at $dy = \pm 10, \pm 20 \dots$, meaning **NO INPUT PORT EXISTS AT $dy = 0$**.
- **Symptom:** If an input tap or pass-through wire is routed along $Y = Y_g$, it penetrates into the gate body and touches the output pin $(X_g, Y_g)$, shorting the gate's output back into its own inputs. In Logisim, this produces an oscillating feedback loop that turns the wire **bright red** with an unconnected blue `X` on the output pin.
- **Strict Rule:** **The horizontal coordinate $Y = Y_g$ is strictly reserved for the output wire to the right.** Never route an input wire, bus tap, or signal through $Y = Y_g$.

### 6.3 Pitfall 3: The Amputated $X_0$ Stub Pitfall (Ошибка «обрубка» шины $X_0$)
- **Problem:** In binary encoders, input $X_0$ corresponds to code $00000_2$. Because none of the bits in $00000_2$ are 1, $X_0$ does not connect to any binary output OR gates ($Y_0 \dots Y_4$). If an agent draws wires only to active bits, $X_0$ ends up with a 10-20 px stub hanging in empty space.
- **Symptom:** The user/instructor sees a broken, cut-off wire ("X0 обрезан") and assumes the schematic is broken.
- **Strict Rule:** In matrix encoders, the vertical bus line for $X_0$ must run down the **full length of the matrix to the exact same $Y_{bottom}$ as all other inputs ($X_1 \dots X_n$)**. In addition, to make $X_0$ actively functional as in real-world ICs (74148, К555ИВ1), connect $X_0$ to an Activity/Validation gate $V$ ($V = X_0 \lor X_1 \lor \dots \lor X_n$) or zero indicator.

### 6.4 Pitfall 4: Top-to-Bottom Matrix Layout vs Crowded Arrays (Топология «Иксы сверху»)
- **Problem:** Arranging 20 input pins horizontally with $\le 20$ px pitch causes severe label collisions (e.g. `X18` and `X19` overlapping into an unreadable blob).
- **Strict Rule:** When placing pins along the top, use **$\Delta X = 40$ px pitch**, set `facing="south"`, and set `labelloc="north"`. This gives each pin 40 px of clean horizontal space, keeping all labels perfectly legible.

---

## 7. Python API & Instant Code Recipes

### Recipe: Programmatic Matrix Encoder Generation
```python
from scripts.logisim_builder import (
    Project, build_matrix_encoder, build_decoder_2to4,
    build_multiplexer_4to1, build_demultiplexer_1to4
)

# 1. Initialize project
proj = Project(name="main")

# 2. Add canonical matrix encoder (inputs along top, full X0 bus, no red loops)
build_matrix_encoder(
    proj,
    name="main",
    num_inputs=20,
    title="Матричный шифратор 20 в 5: число 19 (10011_2)",
    target_variant=19,
    with_valid=True
)

# 3. Add other standard laboratory blocks
build_decoder_2to4(proj, name="Дешифратор_2_в_4", with_enable=True)
build_multiplexer_4to1(proj, name="Мультиплексор_4_в_1", with_enable=True)
build_demultiplexer_1to4(proj, name="Демультиплексор_1_в_4", with_enable=True)

# 4. Save (automatically writes full <mappings> and <toolbar>)
proj.save("lab_circuits.circ")
```

---

## 8. Verification Checklist

Before finalizing any `.circ` file, verify:

1. **Toolbar & Mappings Included:** Verify `<toolbar>` contains Poke Tool and Edit Tool.
2. **All coordinates are multiples of 10.**
3. **Every wire has either $X_1 = X_2$ or $Y_1 = Y_2$** (zero diagonal lines).
4. **No wire passes through a gate center $Y = Y_g$** (prevents red feedback loop bug).
5. **Multi-input gates have adequate vertical clearance:** $\Delta Y \ge \max(120, K \times 14) + 60$ px.
6. **No amputated stubs:** $X_0$ bus line runs full length down to $Y_{bottom}$.
7. **No label collisions:** Top pin array pitch is $\Delta X \ge 40$ px; inputs face south (`labelloc="north"`).
8. **No overlapping collinear wire runs:** Use `add_vbus` / `add_hbus` for bus taps.
9. **Run automated validator:**
   ```bash
   cmd.exe /c "python scripts/validate_circ.py <path_to_circuit.circ>"
   ```
