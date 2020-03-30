import os
import pytest

if 'CI' in os.environ:
  # Set up the CI hypothesis profile which limits the max number of tries
  # The 'CI' profile will be specified through the testing command of the
  # CI script.
  from hypothesis import settings
  settings.register_profile("CI", max_examples=10)

def pytest_addoption(parser):
  try:
    group = parser.getgroup("pytest-pymtl3")
    group.addoption( "--test-verilog", action="store", default='', nargs='?',
                      const='zeros', choices=[ '', 'zeros', 'ones', 'rand' ],
                      help="run verilog translation, " )
    group.addoption( "--dump-vcd", action="store_true",
                      help="dump vcd for each test" )
  except ValueError:
    pass

@pytest.fixture
def test_verilog(request):
  """Test Verilog translation rather than python."""
  return request.config.option.test_verilog

@pytest.fixture
def dump_vcd(request):
  """Dump VCD for each test."""
  if request.config.option.dump_vcd:
    test_module = request.module.__name__
    test_name   = request.node.name
    return '{}.{}.vcd'.format( test_module, test_name )
  else:
    return ''

def pytest_configure(config):
  import sys
  sys._called_from_test = True
  if config.option.dump_vcd:
    sys._pymtl_dump_vcd = True
  else:
    sys._pymtl_dump_vcd = False

def pytest_unconfigure(config):
  import sys
  del sys._called_from_test
  del sys._pymtl_dump_vcd

def pytest_cmdline_preparse(config, args):
  """Don't write *.pyc and __pycache__ files."""
  import sys
  sys.dont_write_bytecode = True

def pytest_runtest_setup(item):
  test_verilog = item.config.option.test_verilog
  if test_verilog and 'test_verilog' not in item.funcargnames:
    pytest.skip("ignoring non-Verilog tests")
