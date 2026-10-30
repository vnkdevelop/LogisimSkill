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
    Coordinate, Wire, XnorGate, Buffer, Demultiplexer, Decoder, Splitter,
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
        self.logisim_jar = os.environ.get("LOGISIM_JAR", "")
        if not self.logisim_jar:
            for cand in [r"D:\ААС\logisim-win-2.7.1.exe", "logisim-win-2.7.1.exe", "logisim.jar"]:
                if os.path.exists(cand):
                    self.logisim_jar = cand
                    break

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
        """2-to-4 Decoder matching canonical digital logic reference circuits."""
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
        build_matrix_encoder(proj, name="Шифратор_16_в_4", num_inputs=16, with_valid=False)

        out_path = os.path.join(self.examples_dir, "canonical_suite.circ")
        proj.save(out_path)
        self.assertTrue(validate_circ(out_path, self.logisim_jar if os.path.exists(self.logisim_jar) else None))

    def test_circuit_inspection_strict_compliance(self):
        """Verifies that all generated circuits strictly pass inspect_circuit."""
        encoder_proj = Project(name="main")
        build_matrix_encoder(encoder_proj, name="main", num_inputs=16, with_valid=False)
        enc_path = os.path.join(self.examples_dir, "matrix_encoder_16to4.circ")
        encoder_proj.save(enc_path)

        rep = inspect_circuit(enc_path, strict=True)
        self.assertTrue(rep.passed, f"Encoder inspection failed: {rep.errors}")
        self.assertEqual(len(rep.dangling_endpoints), 0, "No dangling endpoints allowed")
        self.assertEqual(len(rep.tangential_violations), 0, "No tangential wire connections allowed")
        self.assertEqual(len(rep.gates), 4, "Strictly 4 OR gates for 16-to-4 encoder")

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

    def test_collision_and_overlap_detection(self):
        """Verifies that inspect_circuit catches overlapping components (e.g. adjacent pins placed too close)."""
        proj = Project(name="main")
        c = proj.main
        # Two output pins with only 10px pitch (overlapping circle bodies as in user screenshot)
        c.add(Pin(200, 100, label="OUT0", facing="west", output=True, labelloc="east"))
        c.add(Pin(200, 110, label="OUT1", facing="west", output=True, labelloc="east"))

        tmp_path = os.path.join(self.examples_dir, "test_overlap.circ")
        try:
            proj.save(tmp_path)
            r = inspect_circuit(tmp_path, strict=True)
            self.assertFalse(r.passed, "Overlapping pins must fail inspection!")
            self.assertTrue(any("Collision" in err or "Overlap" in err for err in r.errors),
                            f"Expected collision error, got: {r.errors}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


    def test_xnor_and_buffers_compliance(self):
        """Verifies XNOR Gate geometry and Buffer/Splitter port compliance."""
        proj = Project(name="main")
        c = proj.main

        xnor = c.add(XnorGate(200, 200, inputs=2, size=50))
        p_in0 = c.add(Pin(80, 180, label="A"))
        p_in1 = c.add(Pin(80, 220, label="B"))
        p_out = c.add(Pin(300, 200, label="Y", facing="west", output=True))

        c.connect(p_in0, "pin", xnor, "in0")
        c.connect(p_in1, "pin", xnor, "in1")
        c.connect(xnor, "out", p_out, "pin")

        tmp_path = os.path.join(self.examples_dir, "test_xnor_suite.circ")
        try:
            proj.save(tmp_path)
            r = inspect_circuit(tmp_path, strict=True)
            self.assertTrue(r.passed, f"XNOR Gate inspection failed: {r.errors}")
            self.assertTrue(validate_circ(tmp_path, self.logisim_jar if os.path.exists(self.logisim_jar) else None))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_demux_and_decoder_macro_compliance(self):
        """Verifies Demultiplexer and Decoder macro geometry compliance."""
        proj = Project(name="main")
        c = proj.main

        demux = c.add(Demultiplexer(200, 200, select=1))
        p_in = c.add(Pin(120, 200, label="IN"))
        p_out0 = c.add(Pin(320, 190, label="O0", facing="west", output=True))
        p_out1 = c.add(Pin(320, 210, label="O1", facing="west", output=True))
        p_sel = c.add(Pin(220, 280, label="SEL", facing="north"))

        c.connect(p_in, "pin", demux, "in")
        c.connect(demux, "out0", p_out0, "pin")
        c.connect(demux, "out1", p_out1, "pin")
        c.connect(p_sel, "pin", demux, "sel")

        tmp_path = os.path.join(self.examples_dir, "test_demux_macro.circ")
        try:
            proj.save(tmp_path)
            r = inspect_circuit(tmp_path, strict=True)
            self.assertTrue(r.passed, f"Demux macro inspection failed: {r.errors}")
            self.assertTrue(validate_circ(tmp_path, self.logisim_jar if os.path.exists(self.logisim_jar) else None))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
