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
    Coordinate, Wire,
    build_decoder_2to4, build_encoder_8to3, build_encoder_10to4_bcd,
    build_matrix_encoder, build_multiplexer_4to1, build_multiplexer_8to1,
    build_demultiplexer_1to4, build_demultiplexer_1to8,
    build_half_adder, build_full_adder, build_half_subtractor,
    build_comparator_1bit, build_rs_latch, build_shift_register_4bit,
    build_async_counter_4bit
)
from validate_circ import validate_circ
from inspect_circ import inspect_circuit


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

        # Gates (unlabeled per academic standards)
        xor_gate = c.add(XorGate(260, 110, inputs=2, size=50))
        and_gate = c.add(AndGate(260, 190, inputs=2, size=50))

        # Outputs
        pin_s = c.add(Pin(360, 110, label="Sum", facing="west", output=True))
        pin_c = c.add(Pin(360, 190, label="Carry", facing="west", output=True))

        # Wires from Pin A to XOR in0 and AND in0 (perpendicular auto-routing)
        c.connect(pin_a, "pin", xor_gate, "in0")
        c.connect(pin_a, "pin", and_gate, "in0")

        # Wires from Pin B to XOR in1 and AND in1 (perpendicular auto-routing)
        c.connect(pin_b, "pin", xor_gate, "in1")
        c.connect(pin_b, "pin", and_gate, "in1")

        # Outputs
        c.connect(xor_gate, "out", pin_s, "pin")
        c.connect(and_gate, "out", pin_c, "pin")

        out_path = os.path.join(self.examples_dir, "half_adder.circ")
        proj.save(out_path)
        self.assertTrue(validate_circ(out_path, self.logisim_jar if os.path.exists(self.logisim_jar) else None))

    def test_decoder_2to4(self):
        """2-to-4 Decoder matching standard academic lab circuits."""
        proj = Project(name="main")
        build_decoder_2to4(proj, name="main", with_enable=False)

        out_path = os.path.join(self.examples_dir, "decoder_2to4.circ")
        proj.save(out_path)
        self.assertTrue(validate_circ(out_path, self.logisim_jar if os.path.exists(self.logisim_jar) else None))

    def test_d_flip_flop_divider(self):
        """Frequency divider using D Flip-Flop with inverted feedback (!Q -> D)."""
        proj = Project(name="main")
        c = proj.main

        clk_pin = c.add(Pin(100, 180, label="CLK"))
        dff = c.add(DFlipFlop(260, 160))
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

    def test_toolbar_and_mappings_generation(self):
        """Verifies that every generated project includes toolbar and mappings for Logisim GUI."""
        proj = Project(name="main")
        c = proj.main
        c.add(Pin(100, 100, label="IN"))
        xml_str = proj.to_xml_string()

        self.assertIn("<toolbar>", xml_str)
        self.assertIn("name=\"Poke Tool\"", xml_str)
        self.assertIn("name=\"Edit Tool\"", xml_str)
        self.assertIn("<mappings>", xml_str)

    def test_segmented_bus_helper(self):
        """Verifies that add_vbus and add_hbus generate non-overlapping contiguous segments."""
        proj = Project(name="main")
        c = proj.main
        v_wires = c.add_vbus(100, [300, 100, 200]) # Unsorted input
        self.assertEqual(len(v_wires), 2)
        # Check segment 1: (100, 100) -> (100, 200)
        # Check segment 2: (100, 200) -> (100, 300)
        self.assertIn(Wire((100, 100), (100, 200)), c.wires)
        self.assertIn(Wire((100, 200), (100, 300)), c.wires)

        h_wires = c.add_hbus(200, [400, 150, 250])
        self.assertEqual(len(h_wires), 2)
        self.assertIn(Wire((150, 200), (250, 200)), c.wires)
        self.assertIn(Wire((250, 200), (400, 200)), c.wires)

    def test_canonical_builders(self):
        """Verifies that standard canonical builders generate valid circuits."""
        proj = Project(name="main")
        build_decoder_2to4(proj, name="main", with_enable=True)
        build_encoder_8to3(proj, name="Классический_8_в_3")
        build_multiplexer_4to1(proj, name="Мультиплексор_4_в_1", with_enable=True)
        build_demultiplexer_1to4(proj, name="Демультиплексор_1_в_4", with_enable=True)
        build_matrix_encoder(proj, name="Шифратор_20_в_5", num_inputs=20, target_variant=19, with_valid=False)

        out_path = os.path.join(self.examples_dir, "canonical_suite.circ")
        proj.save(out_path)
        self.assertTrue(validate_circ(out_path, self.logisim_jar if os.path.exists(self.logisim_jar) else None))

    def test_circuit_inspection_strict_compliance(self):
        """Verifies that all generated circuits strictly pass inspect_circuit."""
        encoder_proj = Project(name="main")
        build_matrix_encoder(encoder_proj, name="main", num_inputs=20, target_variant=19, with_valid=False)
        enc_path = os.path.join(self.examples_dir, "matrix_encoder_20to5.circ")
        encoder_proj.save(enc_path)

        rep = inspect_circuit(enc_path, strict=True)
        self.assertTrue(rep.passed, f"Encoder inspection failed: {rep.errors}")
        self.assertEqual(len(rep.dangling_endpoints), 0, "No dangling endpoints allowed")
        self.assertEqual(len(rep.tangential_violations), 0, "No tangential wire connections allowed")
        self.assertEqual(len(rep.gates), 5, "Strictly 5 OR gates for 20-to-5 encoder")

        # Also verify canonical_suite.circ, half_adder.circ, decoder_2to4.circ
        for fname in ["canonical_suite.circ", "half_adder.circ", "decoder_2to4.circ", "d_flip_flop_divider.circ"]:
            fpath = os.path.join(self.examples_dir, fname)
            if os.path.exists(fpath):
                r = inspect_circuit(fpath, strict=True)
                self.assertTrue(r.passed, f"{fname} inspection failed: {r.errors}")
                self.assertEqual(len(r.tangential_violations), 0, f"{fname} has tangential wire violations: {r.tangential_violations}")

    def test_universal_builders_suite(self):
        """Verifies that all newly added universal builders generate 100% compliant circuits."""
        proj = Project(name="main")
        build_half_adder(proj, name="Half_Adder")
        build_full_adder(proj, name="Full_Adder")
        build_half_subtractor(proj, name="Half_Subtractor")
        build_comparator_1bit(proj, name="Comparator_1Bit")
        build_rs_latch(proj, name="RS_Latch")
        build_shift_register_4bit(proj, name="Shift_Register_4Bit")
        build_async_counter_4bit(proj, name="Async_Counter_4Bit")
        build_demultiplexer_1to8(proj, name="Demux_1to8", with_enable=True)
        build_multiplexer_8to1(proj, name="Mux_8to1", with_enable=True)

        out_path = os.path.join(self.examples_dir, "universal_suite.circ")
        proj.save(out_path)

        # Validate with inspect_circ
        r = inspect_circuit(out_path, strict=True)
        self.assertTrue(r.passed, f"Universal suite inspection failed: {r.errors}")
        self.assertEqual(len(r.dangling_endpoints), 0, "No dangling endpoints in universal suite")

        # Validate with validate_circ (including Java engine)
        self.assertTrue(validate_circ(out_path, self.logisim_jar if os.path.exists(self.logisim_jar) else None))


if __name__ == "__main__":
    unittest.main()
