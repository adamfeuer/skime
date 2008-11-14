from ..types.symbol import Symbol as sym
from ..types.pair   import Pair as pair

from ..errors import ParseError

def parse(text, name="__unknown__"):
    "Parse a piece of text."
    return Parser(text, name).parse()

class Parser(object):
    "A simple recursive descent parser for Scheme."
    sym_quote = sym("quote")
    sym_quasiquote = sym("quasiquote")
    sym_unquote = sym("unquote")
    sym_unquote_slicing = sym("unquote-slicing")
    
    def __init__(self, text, name="__unknown__"):
        # input
        self.text = text
        # scope name
        self.name = name
        # current position, incremented as we go
        self.pos = 0
        # current line, used for error reporting
        self.line = 1

    def parse(self):
        "Parse the text and return a sexp."
        expr = self.parse_expr()
        self.skip_all()
        if self.more():
            self.report_error("Expecting end of code, but more code is got")
        return expr


    def parse_expr(self):
        "Parses input up to the next expression"
        def parse_pound():
            "Parses lexems starting with #: #t, #f and such"
            if self.peak(idx=1) == 't':
                # skip #t, that is, 2 characters
                # then return True
                self.pop(n=2)
                return True
            if self.peak(idx=1) == 'f':
                # skip #f, that is, 2 characters
                # then return False
                self.pop(n=2)
                return False
            if self.peak(idx=1) == '(':
                # parse_vector is currently a no-op
                return self.parse_vector()
        def parse_number_or_symbol():
            "Parses number or symbol"
            if self.isdigit(self.peak(idx=1)):
                return self.parse_number()
            return self.parse_symbol()
            
        mapping = {
            '#' : parse_pound,
            '(' : self.parse_list,
            "'" : self.parse_quote,
            '`' : self.parse_quote,
            ',' : self.parse_unquote,
            '+' : parse_number_or_symbol,
            '-' : parse_number_or_symbol,
            '"' : self.parse_string
            }

        # skips whitespaces and comments
        self.skip_all()

        if not self.more():
            raise ParseError("Nothing to be parsed.")
        # pick a routing to parse
        # next expression
        ch = self.peak()
        routine = mapping.get(ch)
        
        if routine is not None:
            return routine()
        
        if self.isdigit(ch):
            return self.parse_number()
        return self.parse_symbol()


    def parse_number(self):
        sign1 = 1
        if self.eat('-'):
            sign1 = -1
        self.eat('+')

        num1 = self.parse_unum()
        if self.eat('/'):
            num2 = self.parse_unum()
            if num2 is None:
                self.report_error("Invalid number format, expecting denominator")
            num1 = float(num1)/num2
        if self.peak() in ['+', '-']:
            sign2 = 1
            if self.eat('-'):
                sign2 = -1
            self.eat('+')
            num2 = self.parse_unum()
            if num2 is None:
                num2 = 1
            if not self.eat('i'):
                self.report_error("Invalid number format, expecting 'i' for complex")
            if num2 != 0:
                num1 = num1 + sign2*num2*1j

        return sign1*num1

    def parse_unum(self):
        "Parse an unsigned number."
        isfloat = False
        pos1 = self.pos
        while self.isdigit(self.peak()):
            self.pop()
        if self.eat('.'):
            isfloat = True
        while self.isdigit(self.peak()):
            self.pop()
        pos2 = self.pos
        if pos2 == pos1:
            return None
        if isfloat:
            return float(self.text[pos1:pos2])
        else:
            return int(self.text[pos1:pos2])


    def parse_list(self):
        """
        Parses a list expression, including an empty list.

        List can be one of

        empty list                 : ()
        list with one element      : (1)
        list with multiple elements: (1 2 3)
        concatenated lists         : (1 2 . 3)
        
        """
        self.eat('(')
        elems = []
        while self.more():
            self.skip_all()
            # a case with empty list: ()
            if self.peak() == ')':
                elems.append(None)
                break
            # cases with a dot
            # (1 . 2)   => pair(1, 2)
            # (1 .2)    => pair(1, 2)
            # (1 2 . 3) => pair(1, pair(2, 3))
            if self.peak() == '.' and self.peak(idx=1) != '.':
                self.eat('.')
                elems.append(self.parse_expr())
                self.skip_all()
                break
            elems.append(self.parse_expr())
        # if list isn't properly close, report it
        if not self.eat(')'):
            self.report_error("Expected ')', got %s" % self.peak())
        # say at this point we have
        # a list of elements [1, 2, 3, 4] (Python list)
        #
        # We need to turn it into a car/cdr list in Scheme
        # implemented with Pair instances in Python:
        #
        # pair(1, pair(2, pair(3, pair(4, None))))
        #
        # what we do is reverse list tail and
        # construct pairs starting with the (originally) last element:
        #
        # last element is 4
        # reversed list is 3, 2, 1
        #
        # (3, 4)
        # (2, (3, 4)
        # (1, (2, (3, 4)))
        first = elems.pop()
        for x in reversed(elems):
            first = pair(x, first)
        return first

    def parse_quote(self):
        "Parses quoted ('sym) and semiquoted expressions"
        if self.peak() == '\'':
            s = Parser.sym_quote
        else:
            s = Parser.sym_quasiquote
        self.pop()
        return pair(s, pair(self.parse_expr(), None))

    def parse_unquote(self):
        """
        Parses unquoting (macro expansions) like (,func 100 200)
        as well as unquote slicing.
        """
        self.eat(',')
        if self.eat('@'):
            return pair(Parser.sym_unquote_slicing,
                        pair(self.parse_expr(), None))
        return pair(Parser.sym_unquote,
                    pair(self.parse_expr(), None))

    def parse_symbol(self):
        """
        Parses a symbol
        """
        pos1 = self.pos
        self.pop()
        # symbols cannot contain backslash,
        # parentheses, comma and at sign
        while self.more() and \
              not self.isspace(self.peak()) and \
              not self.peak() in ['\'', ')', '(', ',', '@']:
            self.pop()
        pos2 = self.pos
        return sym(self.text[pos1:pos2])

    def parse_string(self):
        """
        Parses a string, respects escaped characters.

        Cases to handle:

        "" (empty string)
        "Scheme in Python"
        "Scheme\\"
        "Scheme\nin Python"
        "Scheme\tinPython"

        single quote strings are not used allowed
        """
        mappings = {
            '"':'"',
            '\\':'\\',
            'n':'\n',
            't':'\t'
            }
            
        self.eat('"')
        strings = []
        pos1 = self.pos
        while self.more():
            # "", empty string
            if self.peak() == '"':
                break
            if self.peak() == '\\':
                self.pop()
                ch = self.peak()
                if ch in mappings:
                    strings.append(self.text[pos1:self.pos-1])
                    strings.append(mappings[ch])
                    self.pop()
                    pos1 = self.pos
            else:
                if self.peak() == '\n':
                    self.line += 1
                self.pop()
        strings.append(self.text[pos1:self.pos])
        if not self.eat('"'):
            report_error("Expecting '\"' to end a string.")
        return ''.join(strings)
                

    def parse_vector(self):
        pass

    def skip_all(self):
        "Skip all non-relevant characters: whitespaces and comments."
        while True:
            self.skip_ws()
            if self.peak() == ';':
                self.skip_comment()
            else:
                break

    def skip_ws(self):
        "Skip whitespaces."
        while self.more():
            if self.eat('\n'):
                self.line += 1
            elif self.isspace(self.peak()):
                self.pop()
            else:
                break

    def skip_comment(self):
        "Skip comments."
        while self.eat(';'):
            while self.more() and not self.eat('\n'):
                self.pop()
            self.line += 1

    def pop(self, n=1):
        "Increase self.pos by n."
        self.pos += n

    def more(self):
        "Whether we have more content to parse."
        return self.pos < len(self.text)
            
    def eat(self, char):
        "Try to get a character ahead of current position."
        if self.peak() != char:
            return False
        self.pos += 1
        return True

    def peak(self, idx=0):
        "Get the character head at position self.pos + idx."
        if self.pos + idx < len(self.text):
            return self.text[self.pos + idx]
        return None

    def isdigit(self, ch):
        "Test whether ch is a digit."
        return ch is not None and ch.isdigit()

    def isspace(self, ch):
        "Test whether ch is whitespace."
        return ch is not None and ch.isspace()
        
    def report_error(self, msg):
        "Raise a ParserError with msg."
        raise ParseError("%s:%d %s" % (self.name, self.line, msg))
