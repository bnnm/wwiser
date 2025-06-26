import re

# dumb templater for quick output, don't try this at home. repurposed from:
#   http://code.activestate.com/recipes/496702/
#   https://git.joonis.de/snippets/4

class Template(object):
    """ Compiles a template to python code. Lines are print'd as-is while blocks are executed.
        Format:
        (printed text)
        ${ code: } #python code, has access to args passed to render()
            (prints text depending on the code)
        ${ : } #block end signaled by ":"

        ${ if exists('var'): } #special function, same as: if 'var ' in locals/globals():
            ...
        ${: else x > 5: }
        ${ : }
        ${ #comment }
        $\\{:} escaped
        ${_write(x)} or ${x} or ${'%s' % x} or ${"", x} #x must exist
        ${:if:}{{test}}${:}  #also ok
        ${
          if:
        } #also ok
    """

    # block patterns (DOTALL: . matches LF, *? non-greedy match)
    # matches "...${...}..."
    DELIMITER = re.compile(r"\$\{(.*?)\}", re.DOTALL)
    BLOCK_END = ':'
    ESCAPES = [('\\{','{')]
    AUTOWRITE = re.compile(r"(^[\'\"])|(^[a-zA-Z0-9_\[\]\'\"]+$)")
    FN_WRITE = '_write'
    FN_INCLUDE = '_include'

    def __init__(self, text=None):
        if text is None:
            raise ValueError('text required')
        self._file = 'template.py'
        self._code = self._compile(text)

    def _compile(self, template):
        indent = 0 # indented code
        spaces = 4

        # creates a final text 'program' made of parts = lines
        parts = []

        # may need this thing in first token/line for python2?
        #encoding_hack = '# -*- coding: utf-8 -*-'

        # split template into chunks of regular text and ${..} commands
        for i, part in enumerate(self.DELIMITER.split(template)):
            for base, change in self.ESCAPES:
                part = part.replace(base, change)

            if i % 2 == 0: # "even" parts = output
                if not part:
                    continue

                # regular output is created by calling: 'write("""thing""")'
                part = part.replace('\\', '\\\\').replace('"', '\\"')
                part = '%s%s("""%s""")' % (' ' * indent, self.FN_WRITE, part)

            else: # "odd" parts = commands
                part = part.rstrip()
                if not part:
                    continue

                #commands may be ":" (block end), "(:) ...:" (python code) or "name" (autowritten var 'name')
                command = part.strip()
                if command.startswith(':'): #block end
                    if not indent:
                        raise SyntaxError('no block statement to terminate: ${%s}$' % part)
                    indent -= spaces
                    part = command[1:]

                    #subblock must be (...):
                    if not part.endswith(':'):
                        continue

                elif self.AUTOWRITE.match(command):
                    part = '%s(%s)' % (self.FN_WRITE, command) #output var

                # in case of multiline command, and some cleanup
                lines = part.splitlines()
                margin = min(len(l) - len(l.lstrip()) for l in lines if l.strip())
                part = '\n'.join(' ' * indent + l[margin:] for l in lines)

                if part.endswith(':'):
                    indent += spaces

            # next program chunk
            parts.append(part)

        if indent:
            raise SyntaxError('block statement not terminated (%i)' % indent)

        # finished program lines
        program = '\n'.join(parts)
        return compile(program, self._file, 'exec') #resulting 'code' can be called with exec(code, args)

    def render(self, **code_globals):
        text = []

        # 'write' will be called to output plain text, adds text to outer list
        def _write(*args):
            for value in args:
                text.append(str(value))

        # 'exists' may be  called to check for var existence, since vars must exist in code_globals
        def _exists(arg):
            return arg in code_globals

        #'include' 
        #def _include(file):
        #    pass


        # contains passed render(key=value), that will become code's globals
        code_globals['__file__'] = self._file
        code_globals[self.FN_WRITE] = _write
        #code_globals[self.FN_INCLUDE] = _include
        code_globals['_exists'] = _exists

        # execute template code (loads 'text')
        exec(self._code, code_globals) #, code_locals

        # create final text output
        return ''.join(text)
