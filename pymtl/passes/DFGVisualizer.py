from pymtl import *
from pymtl.components import UpdateVar
from BasePass import BasePass
from SimUpdateVarNetPass import SimUpdateVarNetPass
from SimUpdateVarPass import SimUpdateVarPass
from collections import defaultdict, deque
import ast

class DFGVisualizer( BasePass ):

  def apply( self, model ):

    if not hasattr( model, "tick" ):
      if isinstance( model, UpdateVarNet ):
        SimUpdateVarNetPass().apply( model )

      if isinstance( model, UpdateVar ):
        SimUpdateVarPass().apply( model )

    self.visualize( model )

  def visualize( self, model ):
    deps = defaultdict(set)
    visitor = DetectDataDependency( deps, model._id_obj )

    for blk in model._all_id_upblk.values():
      print
      print "+++++++++++++++++++++++++++++++++++++++++++++++++++"
      print "+ {} at {} ".format( blk.__name__ , repr(blk.hostobj) )
      print "+++++++++++++++++++++++++++++++++++++++++++++++++++"
      print
      visitor.enter( blk )

    # Extract dependency graph information

    all_ids = set()
    for (x, y) in deps:
      all_ids.add( x )
      all_ids.add( y )

    all_objs   = { x: model._id_obj[x] for x in all_ids }
    in_degree  = { x: 0 for x in all_ids }
    out_degree = { x: 0 for x in all_ids }

    for (x, y) in deps:
      in_degree [ y ] += 1
      out_degree[ x ] += 1

    upblk_rank = {}
    for i, x in enumerate( model._batch_schedule ):
      for y in x:
        upblk_rank[ id(y) ] = i

    from graphviz import Digraph

    dot = Digraph()
    dot.graph_attr["rank"] = "source"
    dot.graph_attr["ratio"] = "0.5"
    dot.graph_attr["margin"] = "0.1"

    # We first figure out all external signals which is easy: look at deg

    for i, o in all_objs.iteritems():
      assert in_degree[i] > 0 or out_degree[i] > 0

      if   in_degree[i] == 0: # this is an input port
        dot.node( repr(o), shape='triangle', style='filled', color='gray68',fontsize='20' )
      elif out_degree[i] == 0: # this is an output port
        dot.node( repr(o), shape='invtriangle', style='filled', color='gray80',fontsize='20' )
      else: # normal object
        dot.node( repr(o), shape='ellipse' )

    # Here we figure out all sequential elements. The gist is as follows.
    # Each (x, y) dependency pair flows data from x to y. It can be the
    # case where:
    #   - y = x in some upblk
    #   - if x == 0: y = 1 in some upblk
    #   - ...
    # OK, note that we also have the batch schedule where the 0-th batch
    # is scheduled at the beginning of tick. As a result if
    # - blk A is in the first batch and blk B is not,
    # - blk A reads x in z = x and blk B writes x in x = y
    # Then the dependency is inverted: rd < wr instead of wr < rd which
    # means that x is sequential. As a result, we need to remove z = x
    # from the graph.

    for (x, y) in deps:

      comb_edge = True

      # Only check internal signals to remove sequential elements

      if len( model._all_write_upblks[x] ) == 1:

        # wrblk (B) writes variable x

        wrblk_rank = upblk_rank[ list(model._all_write_upblks[x])[0] ]

        for (lineno, rdblk) in deps[ (x,y) ]: # all occured dependencies

          # rdblk (A) reads variable x

          if upblk_rank[ rdblk ] < wrblk_rank: # rd < wr, inverted!
            dot.node( repr(all_objs[x]), shape='msquare', style='filled', color='lightsalmon', fontsize='20' )
            dot.node( repr(all_objs[y]), shape='msquare', style='filled', color='salmon', fontsize='20' )
            comb_edge = False

      if comb_edge:
        print repr(all_objs[x]), "->", repr(all_objs[y])
        # dot.edge( repr(all_objs[x]), repr(all_objs[y]) )
      else:
        print repr(all_objs[x]), "->", repr(all_objs[y])
        # dot.edge( repr(all_objs[x]), repr(all_objs[y]), constraint='false', style='dashed' )

    # TODO add net
    # dot.render("/tmp/dataflow.gv", view=True)

import astor # DEBUG
_DEBUG = True

class DetectDataDependency( ast.NodeVisitor ):
  def __init__( self, dependencies, id_obj ):
    self.dependencies = dependencies
    self.id_obj = id_obj

  # https://docs.python.org/2/library/ast.html

  def enter( self, blk ):
    self.blk = blk
    self.context_reads = set()
    self.visit( blk.ast )
    assert not self.context_reads

  #-----------------------------------------------------------------------
  # Enumerate all kinds of expr
  #-----------------------------------------------------------------------

  def visit_BoolOp( self, node ):
    if _DEBUG: print "BoolOp", astor.to_source( node ); print
    objs = set()
    for expr in node.values:
      objs |= self.visit( expr )
    return objs

  def visit_BinOp( self, node ):
    if _DEBUG: print "BinOp", astor.to_source( node ); print
    return self.visit( node.left ) | self.visit( node.right )

  def visit_UnaryOp( self, node ):
    if _DEBUG: print "UnaryOp", astor.to_source( node ); print
    return self.visit( node.operand )

  # invalid
  def visit_LambdaOp( self, node ):
    if _DEBUG: print "LambdaOp", astor.to_source( node ); print

  def visit_IfExp( self, node ):
    if _DEBUG: print "IfExp", astor.to_source( node ); print
    return self.visit( node.test ) | self.visit( node.body ) | self.visit( node.orelse )

  # invalid
  def visit_Dict( self, node ):
    if _DEBUG: print "Dict", astor.to_source( node ); print

  # invalid
  def visit_Set( self, node ):
    if _DEBUG: print "Set", astor.to_source( node ); print

  # invalid
  def visit_ListComp( self, node ):
    if _DEBUG: print "ListComp", astor.to_source( node ); print

  # invalid
  def visit_SetComp( self, node ):
    if _DEBUG: print "SetComp", astor.to_source( node ); print

  # invalid
  def visit_DictComp( self, node ):
    if _DEBUG: print "DictComp", astor.to_source( node ); print

  # invalid
  def visit_GeneratorExp( self, node ):
    if _DEBUG: print "GeneratorExp", astor.to_source( node ); print

  # invalid
  def visit_Yield( self, node ):
    if _DEBUG: print "Yield", astor.to_source( node ); print

  def visit_Compare( self, node ):
    if _DEBUG: print "Compare", astor.to_source( node ); print
    assert len(node.ops) == 1

    objs = self.visit( node.left )
    for expr in node.comparators:
      objs |= self.visit( expr )
    return objs

  # call cs
  def visit_Call( self, node ):
    if _DEBUG: print "Call", astor.to_source( node ); print
    return set()

  # invalid
  def visit_Repr( self, node ):
    if _DEBUG: print "Repr", astor.to_source( node ); print

  # invalid
  def visit_Num( self, node ):
    if _DEBUG: print "Num", astor.to_source( node ); print
    return set()

  # ignore
  def visit_Str( self, node ):
    if _DEBUG: print "Str", astor.to_source( node ); print
    return set()

  def visit_Attribute( self, node ):
    if _DEBUG: print "Attribute", astor.to_source( node ); print
    objs = node._objs[ id(self.blk) ] if hasattr( node, "_objs" ) else set()
    return objs | self.visit( node.value )

  def visit_Subscript( self, node ):
    if _DEBUG: print "Subscript", astor.to_source( node ); print
    objs = node._objs[ id(self.blk) ] if hasattr( node, "_objs" ) else set()
    return objs | self.visit( node.value ) | self.visit( node.slice )

  # temporary variable?
  def visit_Name( self, node ):
    if _DEBUG: print "Name", astor.to_source( node ); print
    return set()

  # invalid
  def visit_List( self, node ):
    if _DEBUG: print "List", astor.to_source( node ); print

  # invalid
  def visit_Tuple( self, node ):
    if _DEBUG: print "Tuple", astor.to_source( node ); print

  #-----------------------------------------------------------------------
  # Enumerate all kinds of stmt
  #-----------------------------------------------------------------------

  # def cs(), task?
  def visit_FunctionDef( self, node ):
    if _DEBUG: print "FunctionDef", astor.to_source( node ); print

    assert not node.args.args

    for stmt in node.body:
      self.visit( stmt )

  # invalid
  def visit_ClassDef( self, node ):
    if _DEBUG: print "ClassDef", astor.to_source( node ); print

  # invalid
  def visit_Return( self, node ):
    if _DEBUG: print "Return", astor.to_source( node ); print

  # invalid
  def visit_Delete( self, node ):
    if _DEBUG: print "Delete", astor.to_source( node ); print

  def visit_Assign( self, node ):
    if _DEBUG: print "Assign", astor.to_source( node ); print

    value_reads = self.visit( node.value ) | self.context_reads
    value_writes = set()
    for expr in node.targets:
      value_writes |= self.visit( expr )

    print
    print "--- source ---:", astor.to_source( node )
    print "context_reads:", [ repr(self.id_obj[x]) for x in self.context_reads ]

    for rd_id in value_reads:
      for wr_id in value_writes:
        print "{} -> {}".format( repr(self.id_obj[rd_id]), repr(self.id_obj[wr_id]) )

        self.dependencies[ (rd_id, wr_id) ].add( (node.lineno, id(self.blk)) )

  def visit_AugAssign( self, node ):
    if _DEBUG: print "AugAssign", astor.to_source( node ); print

    value_reads = self.visit( node.value ) | self.context_reads
    value_writes = self.visit( target )

    print
    print "--- source ---:", astor.to_source( node )
    print "context_reads:", [ repr(self.id_obj[x]) for x in self.context_reads ]

    for rd_id in value_reads:
      for wr_id in value_writes:
        print "{} -> {}".format( repr(self.id_obj[rd_id]), repr(self.id_obj[wr_id]) )

        self.dependencies[ (rd_id, wr_id) ].add( (node.lineno, self.blk) )

  # invalid
  def visit_Print( self, node ):
    if _DEBUG: print "Print", astor.to_source( node ); print

  # TODO
  def visit_For( self, node ):
    if _DEBUG: print "For", astor.to_source( node ); print

  # invalid, hls?
  def visit_While( self, node ):
    if _DEBUG: print "While", astor.to_source( node ); print

  def visit_If( self, node ):
    if _DEBUG: print "If", astor.to_source( node ); print

    # The test expression is added to data dependency of the rest of if

    test_reads  = self.visit( node.test )

    need_to_pop = test_reads.copy()
    self.context_reads |= test_reads

    for stmt in node.body:
      self.visit( stmt )

    for stmt in node.orelse:
      tmp_reads    = self.visit( stmt )
      need_to_pop |= tmp_reads
      self.context_reads |= tmp_reads

    self.context_reads -= need_to_pop
    return test_reads

  # invalid
  def visit_With( self, node ):
    if _DEBUG: print "With", astor.to_source( node ); print

  # invalid
  def visit_Raise( self, node ):
    if _DEBUG: print "Raise", astor.to_source( node ); print

  # invalid
  def visit_TryExcept( self, node ):
    if _DEBUG: print "TryExcept", astor.to_source( node ); print

  # invalid
  def visit_TryFinally( self, node ):
    if _DEBUG: print "TryFinally", astor.to_source( node ); print

  # invalid
  def visit_Assert( self, node ):
    if _DEBUG: print "Assert", astor.to_source( node ); print

  # invalid
  def visit_Import( self, node ):
    if _DEBUG: print "Import", astor.to_source( node ); print

  # invalid
  def visit_ImportFrom( self, node ):
    if _DEBUG: print "ImportFrom", astor.to_source( node ); print

  # invalid
  def visit_Exec( self, node ):
    if _DEBUG: print "Exec", astor.to_source( node ); print

  # invalid
  def visit_Global( self, node ):
    if _DEBUG: print "Global", astor.to_source( node ); print

  # invalid hanger expression
  def visit_Expr( self, node ):
    if _DEBUG: print "Expr", astor.to_source( node ); print

  # invalid
  def visit_Pass( self, node ):
    if _DEBUG: print "Pass", astor.to_source( node ); print

  # invalid
  def visit_Break( self, node ):
    if _DEBUG: print "Break", astor.to_source( node ); print

  # invalid
  def visit_Continue( self, node ):
    if _DEBUG: print "Continue", astor.to_source( node ); print

  #-----------------------------------------------------------------------
  # Enumerate all kinds of slice
  #-----------------------------------------------------------------------

  def visit_Slice( self, node ):
    if _DEBUG: print "Slice", astor.to_source( node ); print
    return set()

  def visit_Extslice( self, node ):
    if _DEBUG: print "ExtSlice", astor.to_source( node ); print

  def visit_Index( self, node ):
    if _DEBUG: print "Index", astor.to_source( node ); print
    return self.visit( node.value )
