# =========================================================================
# BasePass.py
# =========================================================================
# An "abstract" base class for all passes.
#
# Author : Shunning Jiang
# Date   : Dec 17, 2017

from builtins import object


class PassMetadata(object):
    pass


class BasePass(object):
    def __init__(self, debug=False):  # initialize parameters
        self.debug = debug

    def __call__(self, m):  # execute pass on model m
        pass
