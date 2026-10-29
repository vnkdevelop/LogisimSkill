---
name: logisim
description: "Author, design, and validate pixel-perfect digital logic circuit files (.circ) for Logisim 2.7.1 and Logisim-evolution. Covers exact component pin geometry, Manhattan wire routing, subcircuit modular hierarchy, multi-bit buses, arithmetic modules, flip-flops, and automated validation."
---

# Logisim Circuit Architect Skill

A complete engineering specification and universal workflow for generating 100% compliant, pixel-perfect `.circ` circuit files that open natively in **Logisim 2.7.1** and **Logisim-evolution** with zero graphical glitches, full GUI toolbar interactivity, zero disconnects, and immediate simulation readiness.

---

## 1. Zero-Exploration Generation Protocol (No Scratch Scripts Needed)

When tasked with creating or modifying a Logisim schematic, **never write temporary discovery scripts, test scripts, or environment probing commands**. 

All component pin offsets, gate geometries, bus distribution methods, canonical circuit topologies, and validation routines are exhaustively documented in this skill and implemented in `scripts/logisim_builder.py` and `scripts/inspect_circ.py`.

### The 4-Step Immediate Execution Pipeline:
1. **Identify the Target Circuit & Truth Table:**
   - Classify the target: Combinational (Adders, Subtractors, Encoders, Decoders, Multiplexers, Demultiplexers, Comparators, ALUs), Sequential (Latches, Flip-Flops, Registers, Counters, FSMs), or Modular (Subcircuits, Buses, Tunnels).
   - Use the canonical Boolean equations and topologies defined in [Section 5](#5-canonical-circuit-topologies--boolean-logic-encyclopedia).
2. **Choose Geometric Layout Projection:**
   - Horizontal ($Left \to Right$): Decoders, multiplexers, adders, registers, comparators.
   - Matrix ($Top \to Right$ or $Top \to Bottom$): Encoders, ROM/PLA matrices, diode grids.
   - Do not dogmatically force all circuits into the same layout; mirror textbook conventions.
3. **Generate the `.circ` File Directly:**
   - Use `scripts/logisim_builder.py` pre-built generators (`build_matrix_encoder`, `build_decoder_2to4`, `build_multiplexer_4to1`, `build_full_adder`, `build_async_counter_4bit`, etc.) OR synthesize the XML structure directly.
   - Project auto-saves with full `<mappings>` and `<toolbar>` blocks.
4. **Audit in 0.5s with Built-in Inspector:**
   ```bash
   cmd.exe /c "python scripts/inspect_circ.py <path_to_circuit.circ>"
   ```
   No Java compilation or manual tests needed — the Python inspector statically verifies 100% compliance with zero false negatives.

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
> `Project.to_xml_string()` and `Project.save()` in `scripts/logisim_builder.py` automatically inject this entire block by default.

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
- **Horizontal Pin Arrays:** Placing pins horizontally side-by-side with $\le 20$ px pitch causes severe label collisions (e.g. "X18" and "X19" overlapping). Always maintain $\ge 40$ px if horizontal placement is used (e.g., matrix encoders).
- **Label Orientation:**
  - Left-hand inputs: `facing="east"`, `labelloc="west"`.
  - Right-hand outputs: `facing="west"`, `output="true"`, `labelloc="east"`.
  - Top inputs: `facing="south"`, `labelloc="north"`.
  - Bottom outputs: `facing="north"`, `output="true"`, `labelloc="south"`.

### 3.4 Segmented Bus Routing & Strict Wire Termination
- **Segmented Point-to-Point Runs:** When tapping a bus line at multiple points, **never draw a single continuous wire across all taps**. In Logisim, overlapping collinear wire segments can cause phantom shorts or failing T-junctions.
  - For vertical bus at $X$ with taps at $Y_0, Y_1, Y_2$: create wire $(X, Y_0) \to (X, Y_1)$ and wire $(X, Y_1) \to (X, Y_2)$.
  - Helper methods `c.add_vbus(x, [y0, y1, y2])` and `c.add_hbus(y, [x0, x1, x2])` automatically sort coordinates and create clean point-to-point subsegments.
- **Strict Wire Termination (Zero Hanging Lines):**
  - **A bus line must terminate STRICTLY at its lowest (or furthest) connected component tap.**
  - Continuing vertical wires past the lowest connected gate into empty space is strictly forbidden.
  - For each input $X_i$, its vertical bus starts at the pin and ends at $\max(\text{gate\_taps}[X_i])$.
  - If an input has zero gate connections (such as $X_0$ in a pure binary encoder where $0_{10} = 00000_2$), **do NOT draw a dangling vertical stub**. An input pin without a dangling stub is valid, whereas a wire ending in empty space is a defect.

### 3.5 Component Labeling Rules (Strict Academic Standards)
- **Label Inputs and Outputs ONLY:**
  - Pins representing inputs (`Pin` with `output="false"`, e.g. `A0`, `A1`, `E`, `DI`, `X0...X19`) and outputs (`Pin` with `output="true"`, e.g. `Y0...Y4`, `DO0...DO7`) **must** be clearly labeled according to the user's task or laboratory specifications.
- **Never Label Internal Logic Gates or Flip-Flops:**
  - Standard logic gates (`AND Gate`, `OR Gate`, `NOT Gate`, `NAND Gate`, `NOR Gate`, `XOR Gate`, `XNOR Gate`) and sequential elements (`D Flip-Flop`, `T Flip-Flop`, `JK Flip-Flop`, `Counter`, `Register`) **MUST REMAIN UNLABELED** (`label=""`).
  - *Rationale:* In Logisim, component labels are drawn directly on top of the gate body or beside it. Labeling every internal gate (e.g. `AND_0`, `OR_Y1`, `NOT_1`) clutters the schematic, violates ГОСТ/academic electrical diagram conventions, and causes rejection.
  - Labels on internal elements are permitted **ONLY** when explicitly requested by the user.

### 3.6 Perpendicular (Normal) Port Entry & Exit Rule
Connecting wires directly into component pins tangentially or along the edge of the component symbol looks broken and violates electrical schematic standards:

```text
[ЗАПРЕЩЕНО - Касательный выход]:              [ЗАПРЕЩЕНО - Касательный вход]:
     |\                                              |  (провод падает сбоку в пин)
     | >O                                            v
     |/  |  <-- Вертикальный сброс прямо       +-----+-----+
         |      с кончика инвертора без        |  *  |     )
         v      отступа! (0px по X)            |  *  | AND )
                                               |  *  |     )
                                               +-----+-----+

[ТРЕБУЕТСЯ - Нормальный ортогональный ввод/вывод с отступом]:
     |\
     | >O--------+  <-- Отступ мин. 1-2 клетки (10-20px) перед поворотом!
     |/          |
                 |
                 +------->  <-- Поворот в сторону входа за 1-2 клетки
                         |
                   +-----v-----+
                   |  *  |     )
                   |  *  | AND )
                   |  *  |     )
                   +-----+-----+
```

- **Strict Geometric Invariants:**
  1. **East-facing Gate Output:** Wire MUST travel horizontally to the right by at least 1-2 grid cells before any vertical turn:
     $$(X_{out}, Y_{out}) \longrightarrow (X_{out} + \Delta X, Y_{out}), \quad \Delta X \ge 10\text{--}20\text{ px}$$
  2. **East-facing Gate Inputs:** Wire MUST approach horizontally from the left by at least 1-2 grid cells:
     $$(X_{in} - \Delta X, Y_{in}) \longrightarrow (X_{in}, Y_{in}), \quad \Delta X \ge 10\text{--}20\text{ px}$$
  3. **3-Segment Z-Routing (`hvh`):** When connecting two horizontal ports at different Y coordinates ($Y_1 \ne Y_2$), **never use 2-segment L-routing** (`hv` or `vh`). Always use 3-segment routing:
     $$(X_1, Y_1) \longrightarrow (X_{mid}, Y_1) \longrightarrow (X_{mid}, Y_2) \longrightarrow (X_2, Y_2)$$
     where $X_1 < X_{mid} < X_2$. `Circuit.connect()` in `logisim_builder.py` automatically uses `hvh` routing by default.

---

## 4. Ground-Truth Component Pin Geometry & Library Index

For a component placed at anchor `loc="(X,Y)"`, its pin positions are calculated as `(X + dx, Y + dy)`.

### 4.1 Wiring (`lib="0"`)
| Component | Default Attributes | Pin Name | dx | dy | Direction |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Pin (Input)** | `facing="east"`, `output="false"` | `pin` | `0` | `0` | Output to circuit |
| **Pin (Output)** | `facing="west"`, `output="true"` | `pin` | `0` | `0` | Input from circuit |
| **Clock** | `facing="east"` | `out` | `0` | `0` | Clock signal |
| **Constant** | `facing="east"`, `value="0x1"` | `out` | `0` | `0` | Output |
| **Power** | `facing="north"` | `out` | `0` | `0` | VCC |
| **Ground** | `facing="south"` | `out` | `0` | `0` | GND |
| **Tunnel** | `facing="west"` | `pin` | `0` | `0` | Shared net |
| **Splitter** | `facing="east"`, `fanout="2"` | `trunk`<br>`out0`<br>`out1` | `0`<br>`20`<br>`20` | `0`<br>`-20`<br>`-10` | Combined bus<br>Bit 0<br>Bit 1 |

### 4.2 Logic Gates (`lib="1"`)
Gates facing `east` have their output at `(0, 0)` relative to `loc`.

#### Standard Size (`size="50"`, medium):
| Gate | Inputs | Input Pin Offsets `(dx, dy)` | Output `(dx, dy)` |
| :--- | :---: | :--- | :---: |
| **AND Gate** | 2 | `in0: (-50, -20)`, `in1: (-50, 20)` | `(0, 0)` |
| **AND Gate** | 3 | `in0: (-50, -20)`, `in1: (-50, 0)`, `in2: (-50, 20)` | `(0, 0)` |
| **AND Gate** | 4 | `in0: (-50, -20)`, `in1: (-50, -10)`, `in2: (-50, 10)`, `in3: (-50, 20)` | `(0, 0)` |
| **AND Gate** | 5 | `in0: (-50, -20)`, `in1: (-50, -10)`, `in2: (-50, 0)`, `in3: (-50, 10)`, `in4: (-50, 20)` | `(0, 0)` |
| **AND Gate** | 8 | `(-50, -40)`, `(-50, -30)`, `(-50, -20)`, `(-50, -10)`, `(-50, 10)`, `(-50, 20)`, `(-50, 30)`, `(-50, 40)` | `(0, 0)` |
| **OR Gate** | 2 | `in0: (-50, -20)`, `in1: (-50, 20)` | `(0, 0)` |
| **OR Gate** | 3 | `in0: (-50, -20)`, `in1: (-50, 0)`, `in2: (-50, 20)` | `(0, 0)` |
| **OR Gate** | 4 | `in0: (-50, -20)`, `in1: (-50, -10)`, `in2: (-50, 10)`, `in3: (-50, 20)` | `(0, 0)` |
| **OR Gate** | 5 | `in0: (-50, -20)`, `in1: (-50, -10)`, `in2: (-50, 0)`, `in3: (-50, 10)`, `in4: (-50, 20)` | `(0, 0)` |
| **OR Gate** | 8 | `(-50, -40)`, `(-50, -30)`, `(-50, -20)`, `(-50, -10)`, `(-50, 10)`, `(-50, 20)`, `(-50, 30)`, `(-50, 40)` | `(0, 0)` |
| **NAND Gate** | 2 | `in0: (-60, -20)`, `in1: (-60, 20)` (bubble adds 10px width) | `(0, 0)` |
| **NOR Gate** | 2 | `in0: (-60, -20)`, `in1: (-60, 20)` | `(0, 0)` |
| **XOR Gate** | 2 | `in0: (-60, -20)`, `in1: (-60, 20)` | `(0, 0)` |
| **XNOR Gate** | 2 | `in0: (-70, -20)`, `in1: (-70, 20)` (extra curve + bubble) | `(0, 0)` |

#### Narrow Size (`size="30"`):
| Gate | Inputs | Input Pin Offsets `(dx, dy)` | Output `(dx, dy)` |
| :--- | :---: | :--- | :---: |
| **AND Gate (Narrow)** | 2 | `in0: (-30, -10)`, `in1: (-30, 10)` | `(0, 0)` |
| **OR Gate (Narrow)** | 2 | `in0: (-30, -10)`, `in1: (-30, 10)` | `(0, 0)` |
| **NOT Gate** | 1 | `in: (-30, 0)` | `(0, 0)` |
| **Buffer** | 1 | `in: (-20, 0)` | `(0, 0)` |

### 4.3 Memory / Sequential Elements (`lib="4"`)
Flip-Flop bodies are 40x40. Outputs $Q$ and $\overline{Q}$ are on the right edge:
| Component | Pin Name | dx | dy | Description |
| :--- | :--- | :---: | :---: | :--- |
| **D Flip-Flop** | `d`<br>`clock`<br>`q`<br>`notq`<br>`reset`<br>`preset`<br>`enable` | `-40`<br>`-40`<br>`0`<br>`0`<br>`-10`<br>`-30`<br>`-20` | `0`<br>`20`<br>`0`<br>`20`<br>`30`<br>`30`<br>`30` | Data input<br>Clock input<br>Normal output $Q$<br>Inverted output $\overline{Q}$<br>Async Clear<br>Async Preset<br>Clock Enable |
| **T Flip-Flop** | `t`<br>`clock`<br>`q`<br>`notq`<br>`reset`<br>`preset`<br>`enable` | `-40`<br>`-40`<br>`0`<br>`0`<br>`-10`<br>`-30`<br>`-20` | `0`<br>`20`<br>`0`<br>`20`<br>`30`<br>`30`<br>`30` | Toggle input<br>Clock input<br>Normal output $Q$<br>Inverted output $\overline{Q}$<br>Async Clear<br>Async Preset<br>Clock Enable |
| **J-K Flip-Flop** | `j`<br>`clock`<br>`k`<br>`q`<br>`notq`<br>`reset`<br>`preset`<br>`enable` | `-40`<br>`-40`<br>`-40`<br>`0`<br>`0`<br>`-10`<br>`-30`<br>`-20` | `0`<br>`10`<br>`20`<br>`0`<br>`20`<br>`30`<br>`30`<br>`30` | J input<br>Clock input<br>K input<br>Normal output $Q$<br>Inverted output $\overline{Q}$<br>Async Clear<br>Async Preset<br>Clock Enable |
| **Register** | `in`<br>`out`<br>`clock`<br>`clear`<br>`enable` | `-30`<br>`0`<br>`-20`<br>`-10`<br>`-30` | `0`<br>`0`<br>`20`<br>`20`<br>`10` | Parallel Data In<br>Parallel Data Out<br>Clock<br>Clear<br>Enable |
| **Counter** | `out`<br>`in`<br>`clock`<br>`clear`<br>`load`<br>`count`<br>`carry` | `0`<br>`-30`<br>`-20`<br>`-10`<br>`-30`<br>`-30`<br>`0` | `0`<br>`0`<br>`20`<br>`20`<br>`-10`<br>`10`<br>`10` | Counter value out<br>Parallel load in<br>Clock<br>Clear<br>Load enable<br>Count enable<br>Carry output |

### 4.4 Arithmetic (`lib="3"`)
| Component | Pin Name | dx | dy | Description |
| :--- | :--- | :---: | :---: | :--- |
| **Adder** | `inA`<br>`inB`<br>`out`<br>`cin`<br>`cout` | `-40`<br>`-40`<br>`0`<br>`-20`<br>`-20` | `-10`<br>`10`<br>`0`<br>`-20`<br>`20` | Input A<br>Input B<br>Sum Out<br>Carry In<br>Carry Out |
| **Subtractor** | `inA`<br>`inB`<br>`out`<br>`bin`<br>`bout` | `-40`<br>`-40`<br>`0`<br>`-20`<br>`-20` | `-10`<br>`10`<br>`0`<br>`-20`<br>`20` | Minuend A<br>Subtrahend B<br>Diff Out<br>Borrow In<br>Borrow Out |
| **Comparator** | `inA`<br>`inB`<br>`gt`<br>`eq`<br>`lt` | `-40`<br>`-40`<br>`0`<br>`0`<br>`0` | `-10`<br>`10`<br>`-10`<br>`0`<br>`10` | Input A<br>Input B<br>Output $A > B$<br>Output $A = B$<br>Output $A < B$ |

---

## 5. Canonical Circuit Topologies & Boolean Logic Encyclopedia

### 5.1 Encoders (Шифраторы)
A binary encoder converts a 1-out-of-$N$ (unary/positional) code on inputs $X_0 \dots X_{N-1}$ into an $M$-bit binary number ($M = \lceil\log_2 N\rceil$) on outputs $Y_{M-1} \dots Y_0$.

- **General Formula for OR-Gate Synthesis:**
  $$\text{Input } X_i \text{ connects to OR gate } Y_k \iff ((i \gg k) \ \& \ 1) == 1$$
- **The Rule for $X_0$ (Why $X_0$ is Not Connected):**
  - In binary, $0_{10} = \mathbf{00000_2}$.
  - The outputs $Y_k$ are produced by OR gates. A zero on all outputs requires that **no input signal activates any OR gate**.
  - Therefore, $X_0$ does not connect to ANY output OR gate.
  - An unconnected input $X_0$ is mathematically and schematically correct. **Never draw a dangling wire stub on $X_0$.**
- **Canonical Topologies:**
  1. **Matrix Encoder (Top-to-Right):** Inputs $X_0 \dots X_{N-1}$ sit along the top ($Y=80$) facing south with $\ge 40$ px pitch. Vertical bus lines drop down and terminate strictly at their lowest connected gate tap. Ideal for $\ge 8$ inputs.
  2. **Horizontal Encoder (Left-to-Right):** Inputs $X_0 \dots X_{N-1}$ sit vertically on the left. Vertical distribution buses feed horizontally into OR gates. Standard for 4-to-2 and 8-to-3 encoders.
- **Priority Encoders (with Activity Flag $V$ / $EO$ / $GS$):**
  If the assignment requires distinguishing between "$X_0$ is active ($0_{10}$ selected)" vs "no inputs are active", add an OR gate for the Valid flag:
  $$V = X_0 \lor X_1 \lor \dots \lor X_{N-1}$$

### 5.2 Decoders (Дешифраторы)
A decoder converts an $n$-bit binary address $A_{n-1} \dots A_0$ into $2^n$ unary output lines $Y_0 \dots Y_{2^n - 1}$.

- **2-to-4 Decoder Logic (with Enable $E$):**
  $$Y_0 = \overline{A_1} \cdot \overline{A_0} \cdot E$$
  $$Y_1 = \overline{A_1} \cdot A_0 \cdot E$$
  $$Y_2 = A_1 \cdot \overline{A_0} \cdot E$$
  $$Y_3 = A_1 \cdot A_0 \cdot E$$
- **3-to-8 Decoder Logic:**
  Each output $Y_i$ is driven by a 3-input (or 4-input with $E$) AND gate corresponding to the minterm $m_i$:
  $$Y_i = A_2^{(b_2)} \cdot A_1^{(b_1)} \cdot A_0^{(b_0)} \cdot E$$

### 5.3 Multiplexers (Мультиплексоры)
A multiplexer routes one of $2^n$ data inputs $D_i$ to a single output $Y$ according to an $n$-bit address $A$.

- **4-to-1 Multiplexer Logic:**
  $$Y = (D_0 \cdot \overline{A_1} \cdot \overline{A_0} \cdot E) \lor (D_1 \cdot \overline{A_1} \cdot A_0 \cdot E) \lor (D_2 \cdot A_1 \cdot \overline{A_0} \cdot E) \lor (D_3 \cdot A_1 \cdot A_0 \cdot E)$$
- **Staircase Collector Routing Rule (Crucial Anti-Short Rule):**
  When collecting the outputs of all AND gates into the final multi-input OR gate:
  - Every single connection must have its own strictly dedicated vertical channel $X_i$.
  - Use nested staircase routing: outer AND gates route through outer vertical channels; inner AND gates route through inner vertical channels.
  - **Never route a vertical wire across another gate's horizontal output line** (Logisim creates an automatic solder junction dot, shorting the gates together).

### 5.4 Demultiplexers (Демультиплексоры)
A demultiplexer directs a single input signal $DI$ to one of $2^n$ outputs $Y_i$ according to address lines $A$.

- **1-to-4 Demultiplexer Logic:**
  $$Y_i = DI \cdot (\text{Address} == i) \cdot E$$
- Structure: $2^n$ discrete AND gates, each receiving $DI$, $E$, and the appropriate true/inverted address lines.

### 5.5 Adders & Subtractors (Сумматоры и вычитатели)
- **1-bit Half Adder:**
  $$S = A \oplus B, \quad C = A \cdot B$$
- **1-bit Full Adder:**
  $$P = A \oplus B, \quad S = P \oplus C_{in}$$
  $$C_{out} = (A \cdot B) \lor (P \cdot C_{in})$$
- **1-bit Half Subtractor:**
  $$D = A \oplus B, \quad B_{out} = \overline{A} \cdot B$$
- **1-bit Full Subtractor:**
  $$D = A \oplus B \oplus B_{in}, \quad B_{out} = \overline{A}B \lor \overline{(A \oplus B)}B_{in}$$
- **Multi-bit Ripple Carry Adder:** Cascade $N$ Full Adders where $C_{out}[i] \to C_{in}[i+1]$.

### 5.6 Comparators (Компараторы)
- **1-bit Magnitude Comparator:**
  $$GT\ (A > B) = A \cdot \overline{B}$$
  $$EQ\ (A = B) = \overline{A \oplus B}\quad (\text{XNOR})$$
  $$LT\ (A < B) = \overline{A} \cdot B$$

### 5.7 Latches & Flip-Flops (Триггеры)
- **RS Latch (NOR-based):**
  Cross-coupled NOR gates: $Q = \overline{R \lor \overline{Q}}$, $\overline{Q} = \overline{S \lor Q}$.
  $S=1 \implies Q=1$; $R=1 \implies Q=0$; $S=R=0 \implies$ Memory; $S=R=1 \implies$ Forbidden.
- **D Flip-Flop (Toggle Divider):**
  Connecting $\overline{Q} \to D$ creates a frequency divider (divides clock frequency by 2).
- **T Flip-Flop:**
  Toggles output $Q$ on clock edge when $T=1$. Built with D Flip-Flop using $D = T \oplus Q$.
- **J-K Flip-Flop:**
  Universal flip-flop: $J=1, K=0 \implies Set$; $J=0, K=1 \implies Reset$; $J=K=1 \implies Toggle$.

### 5.8 Counters (Счетчики)
- **Asynchronous (Ripple) Up-Counter:**
  Cascade $N$ toggle flip-flops ($\overline{Q} \to D$). The clock of stage $i+1$ is driven by $\overline{Q}_i$ (for rising-edge triggered FFs) or $Q_i$ (for falling-edge triggered FFs).
- **Synchronous Binary Counter:**
  All flip-flops share a common clock. Flip-flop $i$ toggles only when all preceding bits are 1:
  $$T_0 = 1, \quad T_1 = Q_0, \quad T_2 = Q_0 \cdot Q_1, \quad T_3 = Q_0 \cdot Q_1 \cdot Q_2$$
- **Modulo-$N$ Counter:**
  A binary counter equipped with an AND gate detecting state $N$ connected to the asynchronous Clear / Reset line.

### 5.9 Shift Registers (Сдвиговые регистры)
- **Serial-In Parallel-Out (SIPO):** Cascade $N$ D Flip-Flops: $D_{in} \to D_0$, $Q_0 \to D_1 \dots Q_{N-2} \to D_{N-1}$. All clock inputs share the common clock bus.
- **Parallel-In Parallel-Out (PIPO):** $N$ independent D Flip-Flops clocked simultaneously.
- **Johnson Counter (Twisted Ring):** SIPO shift register where $\overline{Q}_{N-1}$ is fed back to $D_0$. Cycles through $2N$ states.

### 5.10 Subcircuits & Modular Hierarchies
- In Logisim, any circuit `<circuit name="SubName">` within the project can be instantiated in another circuit as a modular black box:
  `<comp lib="#" loc="(X,Y)" name="SubName"/>`
- Pins inside the subcircuit define its external boundary ports.
- **Tunnels (`Tunnel`):** Use tunnels for clean distribution of clocks, resets, or complex multi-wire buses across the sheet without spaghetti wires.

---

## 6. Critical Engineering Pitfalls & Post-Mortem (Архитектурные ошибки и антипаттерны)

### 6.1 Pitfall 1: Multi-Input Gate Body Expansion (Ловушка расширения высоты многовходовых вентилей)
- **Problem:** When an OR or AND gate has $> 5$ inputs (e.g. 8, 10, or 20 inputs), Logisim dynamically expands the vertical height:
  $$\text{Height} = \max(10 \times \text{inputs},\ \text{size})$$
  A 10-input gate expands to 110 px in height ($Y_g \pm 50$), and a 20-input gate expands to 210 px in height ($Y_g \pm 100$).
- **Strict Rule:** Allocate generous vertical pitch between multi-input gate centers:
  $$\Delta Y_{pitch} \ge \max(120,\ K_{inputs} \times 14) + 60\text{ px}$$

### 6.2 Pitfall 2: Routing Horizontal Wires Through Gate Center (Ошибка короткого замыкания и красной петли)
- **Problem:** For an East-facing gate at $(X_g, Y_g)$, its **OUTPUT PIN** is located exactly at $(X_g, Y_g)$. If an input tap or pass-through wire is routed along $Y = Y_g$, it penetrates into the gate body and touches the output pin $(X_g, Y_g)$, shorting the output back into its own inputs. This turns the wire **bright red** with an unconnected blue `X`.
- **Strict Rule:** **The horizontal coordinate $Y = Y_g$ is strictly reserved for the output wire to the right.** Never route an input wire or bus tap along $Y = Y_g$.

### 6.3 Pitfall 3: Dangling Lines & Dead-End Wire Stubs (Ошибка висячих проводников)
- **Problem:** 
  1. Pulling vertical input lines down past the lowest gate into empty space.
  2. Drawing an artificial 20-40px wire stub on an unconnected input (like $X_0$) that ends in mid-air.
- **Strict Rule:** Every wire segment **must connect two valid points** (either component ports or a junction with another wire). Vertical bus lines stop strictly at the lowest gate port. Unconnected pins (like $X_0$) have zero attached wires.

### 6.4 Pitfall 4: Gate Label Clutter (Засорение схемы текстовыми метками вентилей)
- **Problem:** Adding labels like `OR_Y4`, `AND_0`, `NOT` to internal logic gates.
- **Strict Rule:** **Only input pins and output pins may carry labels.** All logic gates and flip-flops must have `label=""`.

### 6.5 Pitfall 5: Layout Dogmatism & Over-Constraining (Ловушка жесткого хардкода компоновки)
- **Problem:** Forcing every single circuit into the exact same rigid topology.
- **Strict Rule:** Mirror canonical textbook topologies (e.g., decoders and adders flow left-to-right, matrix encoders flow top-to-right, control buses flow from bottom to top).

### 6.6 Pitfall 6: Tangential / Grazing Port Connections (Ошибка касательного подключения к пинам)
- **Problem:** Routing a wire that turns directly on the coordinate of a component pin (0px lead-in/lead-out), causing the wire to run tangentially along the side of the component or drop vertically right off the tip of an inverter.
- **Strict Rule:** Every pin connection MUST be strictly perpendicular (normal) to the component boundary. Provide a clean 10-20px lead-in or lead-out segment before any orthogonal turn.

### 6.7 Pitfall 7: Collector Gate Channel Overlap & Accidental Short-Circuits (Ошибка паразитного замыкания выходов)
- **Problem:** When collecting multiple gate outputs into a multi-input OR gate, routing multiple signals through the same vertical channel or allowing horizontal output lines to cross vertical channels of other gates causes Logisim to generate junction solder dots.
- **Strict Rule (Staircase Channel Routing):**
  - Every connection into a collector gate MUST have its own dedicated, strictly unique vertical channel $X_i$.
  - Use nested staircase routing: outer gates turn at outer $X$ channels; inner gates turn at inner $X$ channels. Zero output lines may intersect or share coordinates.

---

## 7. Automated Circuit Inspection & Self-Check Tool (`inspect_circ.py`)

Always run the built-in circuit inspector before finalizing any `.circ` file:

```bash
cmd.exe /c "python scripts/inspect_circ.py <path_to_circuit.circ>"
```

### What `inspect_circ.py` Automatically Audits:
1. **Toolbar & Mappings:** Verifies `<toolbar>` has `Poke Tool` and `Edit Tool` so GUI tools never disappear.
2. **Strict Component Labeling:** Detects and flags any internal gates or flip-flops that have forbidden labels.
3. **Wire Snapping & Orthogonality:** Confirms all coordinates snap to 10px grid and zero diagonal wires exist.
4. **Dangling Wire Detection:** Finds any wire endpoint that terminates in mid-air (degree 1 with no component port).
5. **Perpendicular Port Alignment:** Enforces that every wire enters and exits component ports perpendicularly along the port normal with at least 1-2 grid cells clearance (zero tangential/grazing connections).
6. **Electrical Short-Circuit Audit:** Detects multiple gate outputs shorted together on the same net (output contention), preventing accidental junction dots and false branching.
7. **Electrical Connectivity & Truth Table Trace:** Traces signal propagation from every input to every gate and output pin, printing the complete logical truth table matrix to verify functionality.

---

## 8. Python API & Universal Code Recipes

### Recipe 1: Universal Canonical Block Generation
```python
from scripts.logisim_builder import (
    Project,
    build_matrix_encoder,
    build_decoder_2to4,
    build_multiplexer_4to1,
    build_demultiplexer_1to4,
    build_half_adder,
    build_full_adder,
    build_half_subtractor,
    build_comparator_1bit,
    build_rs_latch,
    build_shift_register_4bit,
    build_async_counter_4bit
)

# 1. Initialize project
proj = Project(name="main")

# 2. Add assigned circuit to main
build_matrix_encoder(
    proj,
    name="main",
    num_inputs=20,
    title="Шифратор 20 в 5: число 19 (10011_2) (Вариант 9, Табл. 4.2)",
    target_variant=19,
    with_valid=False
)

# 3. Add other requested blocks as separate subcircuits in the same project
build_decoder_2to4(proj, name="Дешифратор_2_в_4", with_enable=True)
build_multiplexer_4to1(proj, name="Мультиплексор_4_в_1", with_enable=True)
build_full_adder(proj, name="Полный_Сумматор")
build_async_counter_4bit(proj, name="Двоичный_Счетчик_4бит")

# 4. Save (automatically writes full <mappings> and <toolbar>)
proj.save("my_circuits.circ")
```

### Recipe 2: Custom Arbitrary Logic Synthesis
```python
from scripts.logisim_builder import Project, Pin, AndGate, OrGate, NotGate, XorGate

proj = Project(name="main")
c = proj.main

# Inputs
a = c.add(Pin(80, 100, label="A"))
b = c.add(Pin(80, 160, label="B"))

# Discrete gates (unlabeled)
xor1 = c.add(XorGate(240, 100, size=50))
and1 = c.add(AndGate(240, 180, size=50))

# Outputs
s = c.add(Pin(320, 100, label="S", facing="west", output=True))
co = c.add(Pin(320, 180, label="C", facing="west", output=True))

# Clean connections
c.connect(xor1, "out", s, "pin")
c.connect(and1, "out", co, "pin")

# Bus distribution
c.wire(a.get_port("pin"), (120, 100))
c.add_vbus(120, [100, 80, 160])
c.wire((120, 80), (180, 80))
c.wire((120, 160), (190, 160))

c.wire(b.get_port("pin"), (140, 160))
c.add_vbus(140, [160, 120, 200])
c.wire((140, 120), (180, 120))
c.wire((140, 200), (190, 200))

proj.save("custom_logic.circ")
```

---

## 9. Verification Checklist

Before delivering any `.circ` file, verify:

1. **Toolbar & Mappings Included:** Verify `<toolbar>` contains Poke Tool and Edit Tool.
2. **All coordinates are multiples of 10.**
3. **Every wire has either $X_1 = X_2$ or $Y_1 = Y_2$** (zero diagonal lines).
4. **Strict Perpendicular Port Connections:** Every wire enters and exits pins strictly perpendicular to the component edge with $\ge 10\text{--}20$ px clearance before turning (zero tangential / grazing connections).
5. **No wire passes through a gate center $Y = Y_g$** (prevents red feedback loop bug).
6. **Multi-input gates have adequate vertical clearance:** $\Delta Y \ge \max(120, K \times 14) + 60$ px.
7. **Strict Wire Termination:** Vertical buses terminate strictly at their lowest connected gate tap (zero hanging lines into void).
8. **Component Labeling:** Only inputs and outputs are labeled. Internal gates and flip-flops have `label=""`.
9. **No label collisions:** Top pin array pitch is $\Delta X \ge 40$ px; inputs face south (`labelloc="north"`).
10. **No overlapping collinear wire runs:** Use `add_vbus` / `add_hbus` for bus taps.
11. **Run automated circuit inspector & validator:**
    ```bash
    cmd.exe /c "python scripts/inspect_circ.py <path_to_circuit.circ>"
    cmd.exe /c "python scripts/validate_circ.py <path_to_circuit.circ>"
    ```
