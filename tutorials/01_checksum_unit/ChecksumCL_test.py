"""
==========================================================================
 ChecksumCL_test.py
==========================================================================
Test cases for CL checksum unit.

Author : Yanghui Ou
  Date : June 6, 2019
"""
from __future__ import absolute_import, division, print_function

from unittest import TestCase

import hypothesis
from hypothesis import strategies as st

from ChecksumCL import ChecksumMcycleCL, ChecksumScycleCL
from ChecksumFL import b128_to_words, checksum, words_to_b128
from ChecksumFL_test import FuncTestsFL
from pymtl3 import *
from pymtl3.stdlib.cl.queues import BypassQueueCL
from pymtl3.stdlib.test import TestSinkCL, TestSrcCL

#-------------------------------------------------------------------------
# Wrap CL component into a function
#-------------------------------------------------------------------------

class WrappedCheckSumCL( Component ):

  def construct( s, DutType=ChecksumScycleCL ):
    s.recv = NonBlockingCalleeIfc( Bits128 )
    s.give = NonBlockingCalleeIfc( Bits32  )
    
    s.checksum_unit = DutType()
    s.out_q = BypassQueueCL( num_entries=1 )
    s.connect_pairs(
      s.recv,               s.checksum_unit.recv,
      s.checksum_unit.send, s.out_q.enq,
      s.out_q.deq,          s.give,
    )

def checksum_cl( words, nstages=None ):
  bits_in = words_to_b128( words )

  dut = WrappedCheckSumCL()
  if nstages is not None:
    dut.set_param( "top.construct", DutType=ChecksumMcycleCL )
    dut.set_param( "top.checksum_unit.construct", nstages=nstages )
  dut.apply( SimpleSim )

  while not dut.recv.rdy():
    dut.tick()

  dut.recv( bits_in )
  dut.tick()

  while not dut.give.rdy():
    dut.tick()

  return dut.give()

#-------------------------------------------------------------------------
# Reuse FL tests
#-------------------------------------------------------------------------
# FIXME: Side effect: TestCasesFL gets executed again

class FuncTestsScycleCL( FuncTestsFL ):
  
  def func_impl( s, words ):
    return checksum_cl( words )    

  # Use hypothesis to compare the wrapped CL function against FL
  @hypothesis.given(
    words = st.lists( st.integers(0, 2**16-1), min_size=8, max_size=8 ) 
  )
  def test_hypothesis( s, words ):
    words = [ b16(x) for x in words ]
    assert s.func_impl( words ) == checksum( words )

class FuncTests2cycleCL( FuncTestsFL ):
  
  def func_impl( s, words ):
    return checksum_cl( words, 2 )    

class FuncTests4cycleCL( FuncTestsFL ):
  
  def func_impl( s, words ):
    return checksum_cl( words, 4 )    

#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness( Component ):
  def construct( s, DutType, src_msgs, sink_msgs ):

    s.src  = TestSrcCL( Bits128, src_msgs )
    s.dut  = DutType()
    s.sink = TestSinkCL( Bits32, sink_msgs )

    s.connect_pairs(
      s.src.send, s.dut.recv,
      s.dut.send, s.sink.recv,
    )

  def done( s ):
    return s.src.done() and s.sink.done()

  def line_trace( s ):
    return "{}>{}>{}".format(
      s.src.line_trace(), s.dut.line_trace(), s.sink.line_trace()
    )

  def run_sim( s, max_cycles=1000 ):
    # Run simulation
    print("")
    ncycles = 0
    s.sim_reset()
    print("{:3}: {}".format( ncycles, s.line_trace() ))
    while not s.done() and ncycles < max_cycles:
      s.tick()
      ncycles += 1
      print("{:3}: {}".format( ncycles, s.line_trace() ))

    # Check timeout
    assert ncycles < max_cycles


#-------------------------------------------------------------------------
# Src/sink based tests
#-------------------------------------------------------------------------

class SrcSinkTestsScycleCL( TestCase ):

  @classmethod
  def setup_class( cls ):
    cls.DutType = ChecksumScycleCL
    cls.nstages = None
  
  # TODO: clean this up.
  def test_simple( s ):
    words  = concat( b16(8), b16(7), b16(6), b16(5), b16(4), b16(3), b16(2), b16(1) )
    result = b32( 0x00780024 )
    th = TestHarness( s.DutType, [ words ], [ result ] )
    if s.nstages is not None:
      th.set_param( "top.dut.construct", nstages=s.nstages )
    th.apply( SimpleSim )
    th.run_sim()

  def test_pipeline( s ):
    words0  = concat( b16(8), b16(7), b16(6), b16(5), b16(4), b16(3), b16(2), b16(1) )
    result0 = b32( 0x00780024 )
    words1  = concat( b16(1), b16(2), b16(3), b16(4), b16(5), b16(6), b16(7), b16(8) )
    result1 = b32( 0x00cc0024 )

    src_msgs  = [ words0, words1, words0, words1 ]
    sink_msgs = [ result0, result1, result0, result1 ]

    th = TestHarness( s.DutType, src_msgs, sink_msgs )
    if s.nstages is not None:
      th.set_param( "top.dut.construct", nstages=s.nstages )
    th.apply( SimpleSim )
    th.run_sim()

  def test_backpressure( s ):
    words0  = concat( b16(8), b16(7), b16(6), b16(5), b16(4), b16(3), b16(2), b16(1) )
    result0 = b32( 0x00780024 )
    words1  = concat( b16(1), b16(2), b16(3), b16(4), b16(5), b16(6), b16(7), b16(8) )
    result1 = b32( 0x00cc0024 )

    src_msgs  = [ words0, words1, words0, words1 ]
    sink_msgs = [ result0, result1, result0, result1 ]

    th = TestHarness( s.DutType, src_msgs, sink_msgs )
    if s.nstages is not None:
      th.set_param( "top.dut.construct", nstages=s.nstages )
    th.set_param( "top.sink.construct", initial_delay=10 )
    th.apply( SimpleSim )
    th.run_sim()
  
  # Yanghui : perhaps we should use customized strategy here to make it
  # looks better?
  @hypothesis.given(
    input_msgs = st.lists( 
                   st.lists( st.integers(0, 2**16-1), min_size=8, max_size=8
                   ).map( lambda lst: [ b16(x) for x in lst ] ) 
                 ),
    nstages    = st.integers( 0, 8  ),
    src_init   = st.integers( 0, 10 ),
    src_intv   = st.integers( 0, 3  ),
    sink_init  = st.integers( 0, 10 ),
    sink_intv  = st.integers( 0, 3  ),
  )
  def test_hypothesis( s, input_msgs, nstages, src_init, src_intv, sink_init, sink_intv ):
    for words in input_msgs:
      words = [ b16(x) for x in words ]
    src_msgs  = [ words_to_b128( words ) for words in input_msgs ]
    sink_msgs = [ checksum( words ) for words in input_msgs ]

    th = TestHarness( s.DutType, src_msgs, sink_msgs  )
    if s.nstages is not None:
      th.set_param( "top.dut.construct", nstages=s.nstages )
    th.set_param( "top.src.construct", initial_delay = src_init, interval_delay = src_intv )
    th.set_param( "top.sink.construct", initial_delay = sink_init, interval_delay = sink_intv )
    th.apply( SimpleSim )
    th.run_sim()

#-------------------------------------------------------------------------
# Reuse single cycle tests to test multi cycle design
#-------------------------------------------------------------------------

class SrcSinkTests2cycleCL( SrcSinkTestsScycleCL ):

  @classmethod
  def setup_class( cls ):
    cls.DutType = ChecksumMcycleCL
    cls.nstages = 2

class SrcSinkTests4cycleCL( SrcSinkTestsScycleCL ):

  @classmethod
  def setup_class( cls ):
    cls.DutType = ChecksumMcycleCL
    cls.nstages = 4
