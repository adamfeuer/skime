#!/usr/bin/env python

from os import path
from optparse import OptionParser
from skime.vm import VM

from skime.compiler.compiler import Compiler
from skime.compiler.parser import parse

op       = OptionParser()
op.add_option('-S', action="store_true", dest="do_not_run",
              help = "Compile source file and drop into .s file then stop.");

(options, args) = op.parse_args()

def is_valid_path(source_file_path):
   """
   Returns true if given path exists and is a file
   Arguments:
   - `path`: path of Scheme source file
   """
   source_file_path = path.abspath(source_file_path)
   return path.exists(source_file_path) and path.isfile(source_file_path)


source_file = open(args[0])

vm          = VM()
compiler    = Compiler()
proc        = compiler.compile(parse(source_file.read()), vm.env)


if not options.do_not_run:
    result      = vm.run(proc)

    print "Result is %s" % result
    source_file.close()
else:
    print "Bytecode:\n%s" % str(proc.bytecode)
    print "Disasm run:\n%s\n" % str(proc.disasm())
