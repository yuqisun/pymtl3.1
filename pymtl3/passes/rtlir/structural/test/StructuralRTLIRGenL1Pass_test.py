#=========================================================================
# StructuralRTLIRGenL1Pass_test.py
#=========================================================================
# Author : Peitian Pan
# Date   : May 19, 2019
"""Test the generation of level 1 structural RTLIR."""

from __future__ import absolute_import, division, print_function

from pymtl3.datatypes import *
import pymtl3.dsl as dsl
from pymtl3.passes.rtlir.rtype import RTLIRDataType as rdt, RTLIRType as rt
from pymtl3.passes.rtlir.structural import StructuralRTLIRSignalExpr as sexp
from pymtl3.passes.rtlir.structural.StructuralRTLIRGenL1Pass import (
    StructuralRTLIRGenL1Pass,
)


def test_L1_const_numbers():
  class A( dsl.Component ):
    def construct( s ):
      s.const = [ Bits32(42) for _ in xrange(5) ]
  a = A()
  a.elaborate()
  a.apply( StructuralRTLIRGenL1Pass() )
  ns = a._pass_structural_rtlir_gen
  assert ns.consts == [('const', rt.Array([5], rt.Const(rdt.Vector(32))), a.const)]

def test_L1_connection_order():
  class A( dsl.Component ):
    def construct( s ):
      s.in_1 = dsl.InPort( Bits32 )
      s.in_2 = dsl.InPort( Bits32 )
      s.out1 = dsl.OutPort( Bits32 )
      s.out2 = dsl.OutPort( Bits32 )
      s.connect( s.in_1, s.out1 )
      s.connect( s.in_2, s.out2 )
  a = A()
  a.elaborate()
  a.apply( StructuralRTLIRGenL1Pass() )
  ns = a._pass_structural_rtlir_gen
  comp = sexp.CurComp(a, 's')
  assert ns.connections == \
    [(sexp.CurCompAttr(comp, 'in_1'), sexp.CurCompAttr(comp, 'out1')),
     (sexp.CurCompAttr(comp, 'in_2'), sexp.CurCompAttr(comp, 'out2'))]

def test_L1_port_index():
  class A( dsl.Component ):
    def construct( s ):
      s.in_ = [ dsl.InPort( Bits32 ) for _ in xrange(5) ]
      s.out = dsl.OutPort( Bits32 )
      s.connect( s.in_[2], s.out )
  a = A()
  a.elaborate()
  a.apply( StructuralRTLIRGenL1Pass() )
  ns = a._pass_structural_rtlir_gen
  comp = sexp.CurComp(a, 's')
  assert ns.connections == \
    [(sexp.PortIndex(sexp.CurCompAttr(comp, 'in_'), 2), sexp.CurCompAttr(comp, 'out'))]

def test_L1_wire_index():
  class A( dsl.Component ):
    def construct( s ):
      s.in_ = [ dsl.InPort( Bits32 ) for _ in xrange(5) ]
      s.wire = [ dsl.Wire( Bits32 ) for _ in xrange(5) ]
      s.out = dsl.OutPort( Bits32 )
      s.connect( s.wire[2], s.out )
      for i in xrange(5):
        s.connect( s.wire[i], s.in_[i] )
  a = A()
  a.elaborate()
  a.apply( StructuralRTLIRGenL1Pass() )
  ns = a._pass_structural_rtlir_gen
  comp = sexp.CurComp(a, 's')
  assert ns.connections[0] == \
    (sexp.WireIndex(sexp.CurCompAttr(comp, 'wire'), 2), sexp.CurCompAttr(comp, 'out'))

def test_L1_const_index():
  class A( dsl.Component ):
    def construct( s ):
      s.const = [ 42 for _ in xrange(5) ]
      s.out = dsl.OutPort( Bits32 )
      s.connect( s.const[2], s.out )
  a = A()
  a.elaborate()
  a.apply( StructuralRTLIRGenL1Pass() )
  ns = a._pass_structural_rtlir_gen
  comp = sexp.CurComp(a, 's')
  # The expression structure is removed and only the constant value
  # is left in this node.
  assert ns.connections == \
    [(sexp.ConstInstance(a.const[2], 42), sexp.CurCompAttr(comp, 'out'))]

def test_L1_bit_selection():
  class A( dsl.Component ):
    def construct( s ):
      s.in_ = dsl.InPort( Bits32 )
      s.out = dsl.OutPort( Bits1 )
      s.connect( s.in_[0], s.out )
  a = A()
  a.elaborate()
  a.apply( StructuralRTLIRGenL1Pass() )
  ns = a._pass_structural_rtlir_gen
  comp = sexp.CurComp(a, 's')
  # PyMTL DSL converts bit selection into 1-bit part selection!
  assert ns.connections == \
    [(sexp.PartSelection(sexp.CurCompAttr(comp, 'in_'), 0, 1), sexp.CurCompAttr(comp, 'out'))]

def test_L1_part_selection():
  class A( dsl.Component ):
    def construct( s ):
      s.in_ = dsl.InPort( Bits32 )
      s.out = dsl.OutPort( Bits4 )
      s.connect( s.in_[4:8], s.out )
  a = A()
  a.elaborate()
  a.apply( StructuralRTLIRGenL1Pass() )
  ns = a._pass_structural_rtlir_gen
  comp = sexp.CurComp(a, 's')
  assert ns.connections == \
    [(sexp.PartSelection(sexp.CurCompAttr(comp, 'in_'), 4, 8), sexp.CurCompAttr(comp, 'out'))]
