
from lmfdb.tests import LmfdbTest
import os
import glob
import itertools
import collections
import re

# An odd run of backslashes followed by a character that does not start a Python escape.
INVALID_ESCAPE = re.compile(r'(?<!\\)(?:\\\\)*\\[^\\\'"abfnrtvxNuU0-7\n]')


class TemplateNamespaceCollisionTest(LmfdbTest):

    def test_template_collisions(self):
        """check lmfdb code directories for duplicate template names"""
        templates = list(itertools.chain.from_iterable([(x, cur) for x in files] for cur, dir, files in os.walk('.') if cur.split('/')[-1] == 'templates'))
        counts = collections.Counter([r[0] for r in templates])
        dups = [x for x in counts if counts[x] > 1]
        collisions = [r for r in templates if r[0] in dups]
        if collisions:
            print()
        for x in dups:
            print("Template file %s appears in: %s" % (x, [r[1] for r in collisions if r[0] == x]))
        assert not collisions, "Template namespace collisions: %s" % collisions

    def test_string_literal_escapes(self):
        """check that Jinja string literals in templates double their backslashes"""
        # Jinja decodes string literals as Python escapes: title='\(x\)' renders as
        # written only because \( is not an escape, and Python 3.12+ warns about it.
        lexer = self.app.jinja_env.lexer
        bad = []
        for path in sorted(glob.glob('lmfdb/**/templates/**/*.html', recursive=True)):
            with open(path) as f:
                source = f.read()
            for lineno, token, value in lexer.tokeniter(source, path):
                if token == 'string' and INVALID_ESCAPE.search(value):
                    bad.append("%s:%s %s" % (path, lineno, value))
        assert not bad, "Double the backslashes in these Jinja strings:\n" + "\n".join(bad)
