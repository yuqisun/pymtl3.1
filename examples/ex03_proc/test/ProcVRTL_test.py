"""
=========================================================================
ProcVRTL_test.py
=========================================================================
Includes test cases for the translated TinyRV0 processor.

Author : Shunning Jiang, Yanghui Ou
  Date : June 15, 2019
"""
import random

import pytest

from examples.ex03_proc.ProcRTL import ProcRTL
from pymtl3 import *
from pymtl3.passes.backends.yosys import *
from pymtl3.passes.tracing import *

from .harness import asm_test, assemble

random.seed(0xdeadbeef)


#-------------------------------------------------------------------------
# ProcVRTL_Tests
#-------------------------------------------------------------------------
# It is as simple as inheriting from RTL tests and overwrite [run_sim]
# function to apply the translation and import pass.

from .ProcRTL_test import ProcRTL_Tests as BaseTests

@pytest.mark.usefixtures("cmdline_opts")
class ProcVRTL_Tests( BaseTests ):

  def run_sim( s, th, gen_test ):

    th.elaborate()

    # Assemble the program
    mem_image = assemble( gen_test() )

    # Load the program into memory
    th.load( mem_image )

    # Check command line arguments for vcd dumping
    if vcd_file_name:
      th.set_metadata( VcdGenerationPass.vcd_file_name, vcd_file_name )
      th.dut.set_metadata( YosysVerilatorImportPass.vl_trace, True )
      th.dut.set_metadata( YosysVerilatorImportPass.vl_trace_filename, vcd_file_name )

    # Translate the DUT and import it back in using the yosys backend.
    th.dut.set_metadata( YosysTranslationImportPass.enable, True )

    th = YosysTranslationImportPass()( th )

    # Create a simulator and run simulation
    th.apply( DefaultPassGroup(print_line_trace=True) )
    th.sim_reset()

    while not th.done() and th.sim_cycle_count() < max_cycles:
      th.sim_tick()

    # Force a test failure if we timed out
    assert th.sim_cycle_count() < max_cycles

#-------------------------------------------------------------------------
# Test translation script
#-------------------------------------------------------------------------

def test_proc_translate():
  import os
  from os.path import dirname
  script_path = dirname(dirname(__file__)) + '/proc-translate'
  os.system(f'python {script_path}')
