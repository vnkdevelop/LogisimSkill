"""
Unit tests and example generation for Logisim Circuit Builder.
"""

import os
import sys
import unittest

# Add scripts directory to sys.path
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from logisim_builder import (
    Project, Pin, AndGate, OrGate, NotGate, XorGate, DFlipFlop,
    Coordinate, Wire
)
from validate_circ import validate_circ


class TestLogisimBuilder(unittest.TestCase):
    def setUp(self):
        self.examples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "examples"))
        os.makedirs(self.examples_dir, exist_ok=True)
        self.logisim_jar = r"D:\ААС\logisim-win-2.7.1.exe"

    def test_coordinate_snapping(self):
        c1 = Coordinate(103, 198)
        self.assertEqual(c1.x, 100)
        self.assertEqual(c1.y, 200)

    def test_half_adder(self):
        proj = Project(name="main")
        c = proj.main

        # Inputs
        pin_a = c.add(Pin(80, 100, label="A"))
        pin_b = c.add(Pin(80, 140, label="B"))

        # Gates
        xor_gate = c.add(XorGate(260, 110, inputs=2, size=50, label="XOR"))
        and_gate = c.add(AndGate(260, 190, inputs=2, size=50, label="AND"))

        # Outputs
        pin_s = c.add(Pin(360, 110, label="Sum", facing="west", output=True))
        pin_c = c.add(Pin(360, 190, label="Carry", facing="west", output=True))

        # Wires from Pin A to XOR in0 and AND in0
        c.connect(pin_a, "pin", xor_gate, "in0", routing="hv")
        c.connect(pin_a, "pin", and_gate, "in0", routing="hv")

        # Wires from Pin B to XOR in1 and AND in1
        c.connect(pin_b, "pin", xor_gate, "in1", routing="hv")
        c.connect(pin_b, "pin", and_gate, "in1", routing="hv")

        # Outputs
        c.connect(xor_gate, "out", pin_s, "pin", routing="hv")
        c.connect(and_gate, "out", pin_c, "pin", routing="hv")

        out_path = os.path.join(self.examples_dir, "half_adder.circ")
        proj.save(out_path)
        self.assertTrue(validate_circ(out_path, self.logisim_jar if os.path.exists(self.logisim_jar) else None))

    def test_decoder_2to4(self):
        """2-to-4 Decoder matching standard academic lab circuits."""
        proj = Project(name="main")
        c = proj.main

        # Inputs
        a0 = c.add(Pin(100, 160, label="a0"))
        a1 = c.add(Pin(100, 260, label="a1"))

        # Inverters
        not0 = c.add(NotGate(200, 180, size=30))
        not1 = c.add(NotGate(200, 280, size=30))

        # Connect a0 -> not0
        c.connect(a0, "pin", not0, "in", routing="hv")
        # Connect a1 -> not1
        c.connect(a1, "pin", not1, "in", routing="hv")

        # 4 AND gates
        and0 = c.add(AndGate(340, 100, inputs=2, size=50, label="Y0"))
        and1 = c.add(AndGate(340, 180, inputs=2, size=50, label="Y1"))
        and2 = c.add(AndGate(340, 260, inputs=2, size=50, label="Y2"))
        and3 = c.add(AndGate(340, 340, inputs=2, size=50, label="Y3"))

        # Outputs
        y0 = c.add(Pin(420, 100, label="Y0=!a1!a0", facing="west", output=True))
        y1 = c.add(Pin(420, 180, label="Y1=!a1 a0", facing="west", output=True))
        y2 = c.add(Pin(420, 260, label="Y2= a1!a0", facing="west", output=True))
        y3 = c.add(Pin(420, 340, label="Y3= a1 a0", facing="west", output=True))

        c.connect(and0, "out", y0, "pin")
        c.connect(and1, "out", y1, "pin")
        c.connect(and2, "out", y2, "pin")
        c.connect(and3, "out", y3, "pin")

        # Routing to inputs
        # Y0 = !a1 & !a0
        c.connect(not0, "out", and0, "in0", routing="hv")
        c.connect(not1, "out", and0, "in1", routing="hv")

        # Y1 = !a1 & a0
        c.connect(a0, "pin", and1, "in0", routing="hv")
        c.connect(not1, "out", and1, "in1", routing="hv")

        # Y2 = a1 & !a0
        c.connect(not0, "out", and2, "in0", routing="hv")
        c.connect(a1, "pin", and2, "in1", routing="hv")

        # Y3 = a1 & a0
        c.connect(a0, "pin", and3, "in0", routing="hv")
        c.connect(a1, "pin", and3, "in1", routing="hv")

        out_path = os.path.join(self.examples_dir, "decoder_2to4.circ")
        proj.save(out_path)
        self.assertTrue(validate_circ(out_path, self.logisim_jar if os.path.exists(self.logisim_jar) else None))

    def test_d_flip_flop_divider(self):
        """Frequency divider using D Flip-Flop with inverted feedback (!Q -> D)."""
        proj = Project(name="main")
        c = proj.main

        clk_pin = c.add(Pin(100, 180, label="CLK"))
        dff = c.add(DFlipFlop(260, 160, label="DFF"))
        q_pin = c.add(Pin(360, 160, label="Q", facing="west", output=True))
        notq_pin = c.add(Pin(360, 180, label="!Q", facing="west", output=True))

        # Clock connection
        c.connect(clk_pin, "pin", dff, "clock", routing="hv")

        # Q output
        c.connect(dff, "q", q_pin, "pin")

        # !Q output
        c.connect(dff, "notq", notq_pin, "pin")

        # Feedback !Q to D: from (260, 180) down to y=220, left to x=180, up to y=160, right to D at (220, 160)
        c.wire((260, 180), (280, 180))
        c.wire((280, 180), (280, 220))
        c.wire((280, 220), (180, 220))
        c.wire((180, 220), (180, 160))
        c.wire((180, 160), (220, 160)) # connects to D at (260-40, 160)

        out_path = os.path.join(self.examples_dir, "d_flip_flop_divider.circ")
        proj.save(out_path)
        self.assertTrue(validate_circ(out_path, self.logisim_jar if os.path.exists(self.logisim_jar) else None))


if __name__ == "__main__":
    unittest.main()
