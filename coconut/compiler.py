#!/usr/bin/env python

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# INFO:
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

"""
Author: Evan Hubinger
Date Created: 2014
Description: The Coconut Compiler.
"""

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# IMPORTS:
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

from __future__ import with_statement, print_function, absolute_import, unicode_literals, division

from .util import *
from . import parser
import argparse
import os
import os.path

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# UTILITIES:
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class executor(object):
    """Compiled Python Executor."""
    def __init__(self, extras=None):
        """Creates The Executor."""
        self.variables = {}
        if extras is not None:
            for k,v in extras.items():
                self.variables[k] = v
    def run(__self, __code, __error=print_error):
        """Executes Python Code."""
        __globals = globals().copy()
        __locals = locals().copy()
        for __k, __v in __self.variables.items():
            globals()[__k] = __v
        try:
            exec(__code)
        except Exception:
            __error()
        __overrides = {}
        for __k, __v in list(globals().items()):
            if __k in __self.variables:
                __self.variables[__k] = __v
                del globals()[__k]
            elif __k not in __globals:
                __overrides[__k] = __v
                del globals()[__k]
        for __k, __v in locals().items():
            if __k in __self.variables:
                __self.variables[__k] = __v
            elif __k not in __locals:
                __self.variables[__k] = __v
        for __k, __v in __overrides.items():
            __self.variables[__k] = __v
        for __k, __v in __globals.items():
            globals()[__k] = __v

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# MAIN:
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class cli(object):
    """The Coconut Command-Line Interface."""
    code_ext = ".coc"
    comp_ext = ".py"
    commandline = argparse.ArgumentParser(description="The Coconut Programming Language.")
    commandline.add_argument("paths", metavar="path", type=str, nargs="*", default=[], help="names of files/directories to compile")
    commandline.add_argument("-v", "--version", action="store_const", const=True, default=False, help="print version information")
    commandline.add_argument("-s", "--strict", action="store_const", const=True, default=False, help="enforce code cleanliness standards")
    commandline.add_argument("-r", "--run", action="store_const", const=True, default=False, help="run files after compiling them")
    commandline.add_argument("-n", "--nowrite", action="store_const", const=True, default=False, help="disable writing of compiled code")
    commandline.add_argument("-i", "--interact", action="store_const", const=True, default=False, help="start the interpreter after compiling files")
    commandline.add_argument("-d", "--debug", action="store_const", const=True, default=False, help="show compiled python being executed")
    commandline.add_argument("-c", "--code", type=str, nargs=argparse.REMAINDER, default=[], help="run code passed in as string")
    commandline.add_argument("--autopep8", type=str, nargs=argparse.REMAINDER, default=None, help="use autopep8 to format compiled code")
    running = False
    runner = None

    def __init__(self, color=None, prompt=">>> ", moreprompt="    "):
        """Creates The CLI."""
        self.gui = terminal(color)
        self.prompt = self.gui.addcolor(prompt, color)
        self.moreprompt = self.gui.addcolor(moreprompt, color)

    def start(self):
        """Gets Command-Line Arguments."""
        args = self.commandline.parse_args()
        self.parse(args)

    def parse(self, args):
        """Parses Command-Line Arguments."""
        self.processor = parser.processor(args.strict)
        self.debug = args.debug
        if args.version:
            self.gui.print("[Coconut] Version "+repr(VERSION)+" running on Python "+sys.version)
        if args.autopep8 is not None:
            self.processor.autopep8(args.autopep8)
        for code in args.code:
            self.execute(self.processor.parse_single(code))
        for path in args.paths:
            if os.path.isfile(path):
                self.compile_file(path, not args.nowrite, args.run)
            elif os.path.isdir(path):
                self.compile_module(path, not args.nowrite, args.run)
            else:
                self.gui.print("[Coconut] Error: Could not find path "+repr(path))
        if args.interact or not (args.paths or args.code or args.version):
            self.start_prompt()

    def compile_module(self, dirname, write=True, run=False):
        """Compiles A Module."""
        for dirpath, dirnames, filenames in os.walk(dirname):
            self.setup_module(dirpath)
            for filename in filenames:
                if os.path.splitext(filename)[1] == self.code_ext:
                    self.compile_file(filename, write, run, True)

    def compile_file(self, filename, write=True, run=False, module=False):
        """Compiles A File."""
        if write:
            codefilename, destfilename = self.resolve(filename)
        else:
            codefilename = filename
            destfilename = None
        self.compile(codefilename, destfilename, run, module)

    def compile(self, codefilename, destfilename=None, run=False, module=False):
        """Compiles A Source Coconut File To A Destination Python File."""
        self.gui.print("[Coconut] Compiling "+repr(codefilename)+"...")
        code = readfile(openfile(codefilename, "r"))
        if module:
            compiled = self.processor.parse_module(code)
        else:
            compiled = self.processor.parse_file(code)
        if destfilename is not None:
            writefile(openfile(destfilename, "w"), compiled)
            self.gui.print("[Coconut] Compiled "+repr(destfilename)+".")
        if run:
            self.execute(compiled)

    def resolve(self, filename):
        """Resolves A Filename Into Source And Destination Files."""
        base, ext = os.path.splitext(filename)
        codefilename = base + ext
        destfilename = base + self.comp_ext
        return codefilename, destfilename

    def setup_module(self, dirpath):
        """Sets Up A Module Directory."""
        writefile(openfile(os.path.join(dirpath, "__coconut__.py"), "w"), parser.headers["code"])

    def start_prompt(self):
        """Starts The Interpreter."""
        self.gui.print("[Coconut] Interpreter:")
        self.running = True
        while self.running:
            self.execute(self.handle(input(self.prompt)))

    def exit(self):
        """Exits The Interpreter."""
        self.running = False

    def handle(self, code):
        """Compiles Coconut Interpreter Input."""
        try:
            compiled = self.processor.parse_single(code)
        except (parser.ParseFatalException, parser.ParseException):
            while True:
                line = input(self.moreprompt)
                if line:
                    code += "\n"+line
                else:
                    break
            try:
                compiled = self.processor.parse_single(code)
            except (parser.ParseFatalException, parser.ParseException):
                return print_error()
        return compiled

    def execute(self, compiled):
        """Executes Compiled Code."""
        if self.runner is None:
            self.start_runner()
        if self.debug:
            self.gui.print("[Coconut] Executing "+repr(compiled)+"...")
        self.runner.run(compiled)

    def start_runner(self):
        """Starts The Runner."""
        self.runner = executor({
            "exit" : self.exit
            })
        self.runner.run(parser.headers["code"])