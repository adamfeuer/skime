What skime is
==============

skime is a Scheme implementation written in Python.

Installing
----------

skime requires the PyYaml library, and the nose library if you want to run the
tests. To install, do the following (ideally in a python virtual environment):

    pip install nose
    pip install pyyaml
    make skime

If you want to run the tests:

    make test

Overview
--------

skime consists of 2 major parts: one produces bytecode and other executes it.
First on is a classic combo of lexer, parser and compiler, and the second one
is virtual machine with its own small instruction set.

Skime produces bytecode on-the-fly, when Scheme source code is evaluated.
Parser and compiler both act as aggregated components for a VM.

Lexical scopes and variable tables
----------------------------------

Scheme source code consists of multiple nested lexical scopes.  Each lexical
scope is represented with an instance of Environment class. Environment is
connected with a parent lexical scope in the code and stores local variables of
it's scope.  Names and values of local variables are stored separately in
arrays and addressed by indexes. Environment maps variable index to variable
name so it's always possible to get a value of a variable by name.

Environment handles access to variables: assignments, reading, allocation.
Allocation simply means creating a slot for a variable with initial value of
undefined.

Undefined represented in Python code with instances of Undef class.

To get location of a variable Location instances are used. Location stores
environment and index in variables table. Location objects are comparable.

Since variables from the outer scope are available to inner scope, Environment
is capable of looking up location recursively towards root scope.

Execution context
-----------------

For function execution Skime uses an abstraction called Context that ties a
form (result of compiling an expression into bytecode), an environment and a
parent context. Each context has a stack and instruction pointer (ip). Context
provides an interface for stack operation: pushing, popping, popping many,
inserting many, getting value from the top of the stack and so forth.

Now lets have a look at the form object. Form stores an environment this form
was compiled in, and a bytecode sequence. Form can be either disassembled
(turned into some string representation) or evaluated. Evaluation needs an
environment (local variables table) and a root context (usually taken from VM
instance).

Primitives
----------

Obviously not everything is written in Scheme. Some basic functions come from
the Python land and thus called primitives. Primitives are wrappers around
Python's callables that know it's arity and Python function to call to do
actual execution.

Primitives are stored in top-level environment (environment of the VM instance)
as PyPrimitive (or PyCallable) instances. Arity is a tuple of 2, where first
value means minimal number of argiments and second value means maximum number
of arguments. -1 means "no limit".

Exception handling for type errors in primitives implemented as a decorator
type\_error\_decorator that catches Python's TypeError and raises Skime's
WrongArgType with the same message.

Here are primitives that back + and * in Scheme:

    @type_error_decorator
    def plus(vm, *args):
        return sum(args)

    @type_error_decorator
    def mul(vm, *args):
        res = 1
        for x in args:
            res *= x
        return res

First argument all primitives take is a VM instance that can be used by the
primitive. Actually the only use of VM instance in Skime primitives is to do
evaluation where necessary.

Scheme types
------------

Scheme types list and symbol are implemented in Python as Pair and Symbol
classes. Since Scheme is a functional language and in functional languages list
comprehensions often use notion of tail and head, and because car and cdr are
functions you cannot imagine Scheme without, Python list is not exactly what we
need.

Pair in Skime stores head element and a reference to list tail. For instance, a
Scheme list (1 2 3) is built as 3 nested Python pairs:

    pair(1, pair(2, pair(3, None))))

This makes car and cdr implementation trivial.

Procedures
----------

Skime has another class that reflects Scheme language constructs. The very core
of Scheme, a procedure, is implemented as a Procedure instance.

Example
-------

Consider the following Scheme code:

    (begin
      (define a (* 99 11))
      (define b (+ 29 33))
      (+ a b))

If we trace bytecode of the whole program, it looks like this

    array('i',
    [9, 0,
    9, 1,
    5, 2,
    1, 2,
    6, 72,
    9, 2,
    9, 3,
    5, 0,
    1, 2,
    6, 73,
    5, 72,
    5, 73,
    5, 0,
    1, 2])

Here is disassembled version:
----------------------------- 

Diasassemble of form at B7CF24AC
literals:

    0: 99
    1: 11
    2: 29
    3: 33

Instructions:
------------

    0000         push_literal literal=0
    0002         push_literal literal=1
    0004           push_local idx: 2, name: *
    0006                 call argc=2
    0008            set_local idx: 72, name: a
    000A         push_literal literal=2
    000C         push_literal literal=3
    000E           push_local idx: 0, name: +
    0010                 call argc=2
    0012            set_local idx: 73, name: b
    0014           push_local idx: 72, name: a
    0016           push_local idx: 73, name: b
    0018           push_local idx: 0, name: +
    001A                 call argc=2

