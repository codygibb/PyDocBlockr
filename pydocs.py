import re
from collections import deque

import sublime
import sublime_plugin

# max number of lines we will attempt to parse a function definition for
MAX_LINES = 25


def counter():
    count = 0
    while True:
        count += 1
        yield(count)


class PydocsCommand(sublime_plugin.TextCommand):
    def __init__(self, arg):
        super(PydocsCommand, self).__init__(arg)
        self.fn_comment_lookup = {}

    def run(self, edit):
        start = self.view.sel()[0].end()
        line = self.get_definition(self.view.line(start).begin() - 1)
        res = self.parse_header(line)
        if res:
            name, args = res
            snippet = self.generate_snippet(name, args)
            print 'before:', self.fn_comment_lookup
            self.fn_comment_lookup[name] = 'hey'
            print 'after:', self.fn_comment_lookup
            print
            self.write(snippet)
        else:
            self.write('\n')
    
    def get_definition(self, pos):
        lines = deque()
        open_parens = 0

        for i in range(0, MAX_LINES):
            line = self.read_line(pos)
            if not line:
                break

            pos -= len(line) + 1 # move pos to the line above
            line = re.sub(R'#.*', '', line) # strip comments
            lines.appendleft(line)

            for c in line:
                if c == ')':
                    open_parens += 1
                elif c == '(':
                    open_parens -= 1

            if open_parens == 0:
                break

        return ' '.join(lines)

    def parse_header(self, line):
        name_regex = R'[a-zA-Z_$][a-zA-Z_$0-9]*'
        fn_def_regex = R'def\s*(?P<name>' + name_regex + R')\s*\((?P<args>.*)\)\s*:'

        res = re.search('(?:' + fn_def_regex + ')', line)

        if not res:
            return None

        groups = res.groupdict()
        args = groups['args'].split(',')
        for i in range(0, len(args)):
            # 'foo = None' -> 'foo'
            args[i] = args[i].split('=')[0].strip()


        if args and (args[0] == 'self' or args[0] == 'cls'):
            # don't include 'self' or 'cls' arguments
            args = args[1:]

        return (groups['name'], args)

    def generate_snippet(self, name, args):
        """ creates a doc comment for the given function and arguments
        (just like this one!)
        
        @name String : name of the function
        @args List : strings of the arguments of function
        
        @return String -> formatted comment template
        """
        lines = []
        lines.append(' ${1:[%s description]}\n' % name)

        for arg in args:
            lines.append('@%s ${1:[type]} : ${1:[description]}' % arg)
        if args:
            lines[-1] += '\n'

        lines.append('@return ${1:[type]} -> ${1:[description]}')
        
        self.fix_tab_stops(lines)

        snippet = '\n'.join(lines) + '\n"""'
        return snippet

    def fix_tab_stops(self, lines):
        tab_index = counter()

        def swap_tabs(m):
            return "%s%d%s" % (m.group(1), next(tab_index), m.group(2))

        for index, line in enumerate(lines):
            lines[index] = re.sub("(\\$\\{)\\d+(:[^}]+\\})", swap_tabs, line)

    def read_line(self, pos):
        if pos >= self.view.size():
            return

        next_line = self.view.line(pos)
        return self.view.substr(next_line)

    def write(self, s):
        self.view.run_command('insert_snippet', {'contents': s})