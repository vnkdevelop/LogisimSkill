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

### 3.4 Segmented Bus Routing & Strict Wire Termination
- **Segmented Point-to-Point Runs:** When tapping a bus line at multiple points, **never draw a single continuous wire across all taps**. In Logisim, overlapping collinear wire segments can cause phantom shorts or failing T-junctions.
  - For vertical bus at $X$ with taps at $Y_0, Y_1, Y_2$: create wire $(X, Y_0) \to (X, Y_1)$ and wire $(X, Y_1) \to (X, Y_2)$.
  - Helper methods `c.add_vbus(x, [y0, y1, y2])` and `c.add_hbus(y, [x0, x1, x2])` automatically sort coordinates and create clean point-to-point subsegments.
- **Strict Wire Termination (Zero Hanging Lines):**
  - **A bus line must terminate STRICTLY at its lowest (or furthest) connected component tap.**
  - Continuing vertical wires past the lowest connected gate into empty space ("линии вниз, они не нужны, потому что там ничего нету, просто так проведены") is strictly forbidden.
  - For each input $X_i$, its vertical bus starts at the pin and ends at $\max(\text{gate\_taps}[X_i])$.
  - If an input has zero gate connections (such as $X_0$ in a pure binary encoder where $0_{10} = 00000_2$), **do NOT draw a dangling vertical stub**. An input pin without a dangling stub is valid, whereas a wire ending in empty space is a defect.

### 3.5 Component Labeling Rules (Strict Academic Standards)
- **Label Inputs and Outputs ONLY:**
  - Pins representing inputs (`Pin` with `output="false"`, e.g. `A0`, `A1`, `E`, `DI`, `X0...X19`) and outputs (`Pin` with `output="true"`, e.g. `Y0...Y4`, `DO0...DO7`) **must** be clearly labeled according to the user's task or laboratory specifications.
- **Never Label Internal Logic Gates or Flip-Flops:**
  - Standard logic gates (`AND Gate`, `OR Gate`, `NOT Gate`, `NAND Gate`, `NOR Gate`, `XOR Gate`, `XNOR Gate`) and sequential elements (`D Flip-Flop`, `T Flip-Flop`, `JK Flip-Flop`, `Counter`, `Register`) **MUST REMAIN UNLABELED** (`label=""`).
  - *Rationale:* In Logisim, component labels are drawn directly on top of the gate body or beside it. Labeling every internal gate (e.g. `AND_0`, `OR_Y1`, `NOT_1`) clutters the schematic, violates ГОСТ/academic electrical diagram conventions, and causes teacher rejection.
  - Labels on internal elements are permitted **ONLY** when explicitly and specifically requested by the user.

### 3.6 Multi-Circuit Architecture
- In academic laboratory assignments and modular designs:
  - Put the specific assigned variant in the `main` circuit.
  - Put standard classical reference designs (e.g., `Классический_8_в_3`, `Дешифратор_2_в_4_без_E`) as additional named subcircuits in the same `.circ` file.
  - This allows instructors and students to inspect both the textbook base circuit and the assigned variant in a single file.

### 3.7 Topology Freedom & Canonical Reference Compliance (Свобода компоновки и соответствие первоисточникам)
- **Категорический запрет на догматический хардкод компоновки:** Нельзя жестко фиксировать единую ориентацию («входы всегда только сверху, а выходы только справа» или «провод всегда только вниз к Y»). Схемы в цифровой схемотехнике разнообразны и должны выглядеть так, как их привыкли видеть инженеры, преподаватели и студенты в учебниках и справочниках:
  1. **Входы слева $\to$ выходы справа:** Классический горизонтальный поток сигналов (дешифраторы, сумматоры, мультиплексоры, регистры, шифраторы горизонтального типа).
  2. **Входы сверху $\to$ выходы справа или снизу:** Матричные шифраторы, матричные преобразователи кодов, диодные сетки, таблицы прошивок ПЗУ.
  3. **Входы снизу $\to$ выходы сверху:** Линии адресации и стробирования, шины выбора кристаллов (CS/OE).
  4. **Любая иная каноническая ориентация из задания:** Если в методичке, даташите или на схеме из интернета выходы расположены внизу, а входы справа — схема должна строиться именно в этой канонической проекции.
- **Инварианты качества при любой ориентации:**
  - Сигналы движутся естественно и читаемо, без визуальной каши.
  - Каждый проводник соединяет ровно те точки, которые требуются, и не продолжается дальше в пустоту (строгий запрет холостых хвостов).
  - Ни один провод не пересекает выходной пин вентиля или его корпус (полная защита от красных петель и КЗ).
  - Все координаты кратны 10px, сетка строгая, проводники строго ортогональны (Manhattan).
  - Схема функционально 100% работоспособна и верифицирована.

### 3.8 Normal (Perpendicular) Port Entry & Exit Rule (Правило перпендикулярного входа и выхода проводов)
- **The Core Problem (Касательный/скользящий ввод и вывод проводов):**
  Connecting wires directly into component pins tangentially or along the edge of the component symbol looks broken, violates engineering schematic conventions, and fails automated inspection.
  
  ```text
  [ЗАПРЕЩЕНО - Касательный выход (Image 1)]:      [ЗАПРЕЩЕНО - Касательный вход (Image 2)]:
       |\                                                |  (провод падает сбоку в пин)
       | >O                                              v
       |/  |  <-- Вертикальный сброс прямо         +-----+-----+
           |      с кончика инвертора без отступа! |  *  |     )
           v      (0px горизонтального вылета)     |  *  | AND )
                                                   |  *  |     )
                                                   +-----+-----+

  [ТРЕБУЕТСЯ - Нормальный ортогональный ввод/вывод с отступом (Image 3)]:
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
     A vertical wire originating directly at $(X_{out}, Y_{out})$ is strictly forbidden.
  2. **East-facing Gate Inputs:** Wire MUST approach horizontally from the left by at least 1-2 grid cells:
     $$(X_{in} - \Delta X, Y_{in}) \longrightarrow (X_{in}, Y_{in}), \quad \Delta X \ge 10\text{--}20\text{ px}$$
     Any vertical distribution bus or corner must sit at $X_{bus} \le X_{in} - 10\text{ px}$. A vertical wire terminating directly on $(X_{in}, Y_{in})$ is strictly forbidden.
  3. **3-Segment Z-Routing (`hvh`):** When connecting two horizontal ports at different Y coordinates ($Y_1 \ne Y_2$), **never use 2-segment L-routing** (`hv` or `vh`), which creates a tangential vertical segment at one of the endpoints. Always use 3-segment routing:
     $$(X_1, Y_1) \longrightarrow (X_{mid}, Y_1) \longrightarrow (X_{mid}, Y_2) \longrightarrow (X_2, Y_2)$$
     where $X_1 < X_{mid} < X_2$. `Circuit.connect()` in `logisim_builder.py` automatically uses `hvh` routing by default.

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

### 5.2 Шифратор (Binary & Positional Encoders)
- **Топологическая гибкость (Top-to-Right vs Left-to-Right):**
  Шифраторы строятся в соответствии с тем, как они представлены в конкретном задании или учебнике:
  1. **Матричная компоновка («Иксы сверху»):** Входы $X_0 \dots X_{N-1}$ размещаются сверху горизонтально ($Y=80$) с направлением на юг (`facing="south"`, `labelloc="north"`). Шаг $\Delta X \ge 40$ px исключает наложение меток. Шины опускаются к элементам ИЛИ справа и заканчиваются строго на нижнем подключенном контакте. Идеально для многовходовых шифраторов (16..20 входов).
  2. **Классическая горизонтальная компоновка («Иксы слева»):** Входы $X_0 \dots X_{N-1}$ располагаются вертикально слева (`facing="east"`), вертикальные шины распределяют сигналы на элементы ИЛИ справа. Общепринята в учебниках для базовых шифраторов 4-в-2, 8-в-3, 10-в-4 BCD. При горизонтальной компоновке строго соблюдается правило защиты: линия $Y = Y_g$ резервируется под выходной провод, а входы вентилей заводятся с шагом $dy = \pm 10, \pm 20 \dots$, что гарантирует отсутствие паразитных петель.
- **Правило для $X_0$ (Вход 0):**
  - В простом шифраторе вход $X_0$ кодирует $00000_2$. Поскольку ни один бит не активен, $X_0$ не подается на элементы ИЛИ.
  - **Запрет висячих отрезков:** На пин $X_0$ категорически запрещено вешать холостой отрезок провода в 20-40px, обрывающийся в воздухе. Пин $X_0$ располагается чисто, без висячих концов.
- **General $N$-to-$M$ Positional Logic on OR Gates:**
  For $N$ inputs $X_0 \dots X_{N-1}$ and $M = \lceil\log_2 N\rceil$ output bits $Y_0 \dots Y_{M-1}$:
  $$\text{Input } X_i \text{ connects to OR gate } Y_k \iff ((i \gg k) \ \& \ 1) == 1$$
  - Every OR gate represents one output bit ($Y_0$ weight 1, $Y_1$ weight 2, $Y_2$ weight 4, $Y_3$ weight 8, $Y_4$ weight 16).
  - Logic gates must remain **UNLABELED** (`label=""`). Only the output pins carry labels (e.g. `Y0 (1)`, `Y1 (2)`, etc.).
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
  - Use `build_matrix_encoder(proj, name="main", num_inputs=20, target_variant=19, with_valid=False)`.

### 5.3 Мультиплексор (Multiplexer 4-to-1 & 8-to-1)
- **4-to-1 Logic:**
  $$Y = (D_0 \cdot \overline{A_1} \cdot \overline{A_0} \cdot E) \lor (D_1 \cdot \overline{A_1} \cdot A_0 \cdot E) \lor (D_2 \cdot A_1 \cdot \overline{A_0} \cdot E) \lor (D_3 \cdot A_1 \cdot A_0 \cdot E)$$
- **Structure:**
  - 4 (or 8) AND gates combining each data input $D_i$ with its unique binary address minterm and enable $E$. Gates remain unlabeled.
  - 1 final multi-input OR gate collecting all AND gate outputs into single output $Y$.
  - Direct builders: `build_multiplexer_4to1(proj)` and `build_multiplexer_8to1(proj)`.

### 5.4 Демультиплексор (Demultiplexer 1-to-4 & 1-to-8)
- **1-to-4 Logic:**
  $$Y_i = DI \cdot (\text{Address} == i) \cdot E$$
- **Structure:**
  - Single informational input $DI$, enable $E$, and address selection lines.
  - 4 (or 8) AND gates driving independent output lines $Y_0 \dots Y_3$. Gates remain unlabeled.
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

### 6.3 Pitfall 3: Dangling Lines & Dead-End Wire Stubs (Ошибка висячих проводников и лишних линий)
- **Problem:** Two common mistakes occur when drawing bus lines:
  1. Pulling vertical input lines down past the lowest gate into empty space ("линии вниз, они не нужны, потому что там ничего нету, просто так проведены").
  2. Drawing an artificial 20-40px wire stub on an unconnected input (like $X_0$) that ends in mid-air.
- **Symptom:** Logisim circuits look amateurish and fail automated topological checks. Every wire endpoint with degree 1 that doesn't connect to a pin is a dangling wire error.
- **Strict Rule:** Every wire segment **must connect two valid points** (either component ports or a junction with another wire). Vertical bus lines stop strictly at the lowest gate port.

### 6.4 Pitfall 4: Gate Label Clutter (Засорение схемы текстовыми метками вентилей)
- **Problem:** Adding labels like `OR_Y4`, `AND_0`, `NOT` to internal logic gates.
- **Symptom:** Logisim renders labels directly on the gate symbol. Schematics look cluttered and violate academic formatting rules.
- **Strict Rule:** **Only input pins and output pins may carry labels.** All logic gates and flip-flops must have `label=""`.

### 6.5 Pitfall 5: Layout Dogmatism & Over-Constraining (Ловушка жесткого хардкода компоновки)
- **Problem:** Forcing every single circuit into the exact same rigid topology (e.g. demanding that inputs must always and everywhere be strictly on top or on the left). Different logical blocks in engineering and educational practice have established, recognizable appearances (e.g., decoders and adders flow left-to-right, matrix encoders flow top-to-right, control buses flow from bottom to top).
- **Symptom:** Schematics look unnatural, monotonous, or conflict with how students and teachers were taught to read them in standard textbooks and lab manuals.
- **Strict Rule:** **Do not dogmatically hardcode pin or bus positions.** Structure the schematic so it mirrors the canonical diagram from authoritative engineering sources, while strictly preserving core quality invariants: zero dangling wire stubs, zero feedback loop collisions, clean 10px snapping, and unlabeled internal gates.

### 6.6 Pitfall 6: Tangential / Grazing Port Connections (Ошибка касательного подключения к пинам)
- **Problem:** Routing a wire that turns directly on the coordinate of a component pin (0px lead-in/lead-out), causing the wire to run tangentially along the side of the component or drop vertically right off the tip of an inverter.
- **Symptom:** Inverters have wires hanging directly down from the inversion bubble; AND/OR gates have wires entering from the top or bottom edges into input pins. The schematic looks sloppy, violates electrical drawing standards, and fails automated inspection.
- **Strict Rule:** Every pin connection MUST be strictly perpendicular (normal) to the component boundary. Provide a clean 10-20px lead-in or lead-out segment before any orthogonal turn. `Circuit.connect()` and `inspect_circ.py` automatically enforce this invariant.

### 6.7 Pitfall 7: Collector Gate Channel Overlap & Accidental Short-Circuits (Ошибка паразитного замыкания выходов при объединении в ИЛИ)
- **Problem:** When collecting multiple gate outputs (e.g. 8 AND gates in an 8-to-1 multiplexer) into a multi-input OR gate, routing multiple signals through the same vertical channel ($X$) or allowing horizontal output lines to cross vertical channels of other gates causes Logisim to generate junction solder dots.
- **Symptom:** Two or more AND gate outputs become electrically shorted together. Visually, it appears as though one AND gate branches into multiple inputs of the OR gate (a bizarre fork with dots), destroying signal independence.
- **Strict Rule (Staircase Channel Routing):**
  - Every single connection into a multi-input collector gate MUST have its own dedicated, strictly unique vertical channel $X_i$.
  - Use nested staircase routing: gates located further from the centerline turn at outer $X$ channels, while gates closer to the centerline turn at inner $X$ channels.
  - Zero output lines may intersect or share coordinates. `inspect_circ.py` automatically audits electrical nets to guarantee that no two gate outputs are ever shorted together.

---

## 7. Automated Circuit Inspection & Self-Check Tool (`inspect_circ.py`)

Always run the built-in circuit inspector before finalizing any `.circ` file:

```bash
cmd.exe /c "python scripts/inspect_circ.py <path_to_circuit.circ>"
```

### What `inspect_circ.py` Automatically Audits:
1. **Toolbar & Mappings:** Verifies `<toolbar>` has `Poke Tool` and `Edit Tool` so GUI tools never disappear.
2. **Strict Component Labeling:** Detects and flags any internal gates or flip-flops that have forbidden labels. Can auto-clean with `--fix-labels`.
3. **Wire Snapping & Orthogonality:** Confirms all coordinates snap to 10px grid and zero diagonal wires exist.
4. **Dangling Wire Detection:** Finds any wire endpoint that terminates in mid-air (degree 1 with no component port).
5. **Perpendicular Port Alignment:** Enforces that every wire enters and exits component ports perpendicularly along the port normal with at least 1-2 grid cells clearance (zero tangential/grazing connections).
6. **Electrical Short-Circuit Audit:** Detects multiple gate outputs shorted together on the same net (output contention), preventing accidental junction dots and false branching.
7. **Electrical Connectivity & Truth Table Trace:** Traces signal propagation from every input to every gate and output pin, printing the complete logical truth table matrix to verify functionality against real-world engineering models.

---

## 8. Python API & Instant Code Recipes

### Recipe: Programmatic Matrix Encoder Generation
```python
from scripts.logisim_builder import (
    Project, build_matrix_encoder, build_decoder_2to4,
    build_multiplexer_4to1, build_demultiplexer_1to4
)

# 1. Initialize project
proj = Project(name="main")

# 2. Add canonical matrix encoder (inputs along top, strictly terminated wires, unlabeled gates)
build_matrix_encoder(
    proj,
    name="main",
    num_inputs=20,
    title="Шифратор 20 в 5: число 19 (10011_2) (Вариант 9, Табл. 4.2)",
    target_variant=19,
    with_valid=False
)

# 3. Add other standard laboratory blocks
build_decoder_2to4(proj, name="Дешифратор_2_в_4", with_enable=True)
build_multiplexer_4to1(proj, name="Мультиплексор_4_в_1", with_enable=True)
build_demultiplexer_1to4(proj, name="Демультиплексор_1_в_4", with_enable=True)

# 4. Save (automatically writes full <mappings> and <toolbar>)
proj.save("lab_circuits.circ")
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
