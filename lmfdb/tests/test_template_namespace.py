from lmfdb.tests import LmfdbTest
import os, itertools, collections

class TemplateNamespaceCollisionTest(LmfdbTest):

    def test_template_collisions(self):
        """check lmfdb code directories for duplicate template names"""
        templates = [ r for r in itertools.chain.from_iterable([(x,cur) for x in files] for cur,dir,files in os.walk('.') if cur.split('/')[-1] == 'templates') ]
        counts = collections.Counter([r[0] for r in templates])
        dups = [x for x in counts if counts[x] > 1]
        collisions = [r for r in templates if r[0] in dups]
        if collisions:
            print ""
        for x in dups:
            print "Template file %s appears in: %s"%(x,[r[1] for r in collisions if r[0] == x])
        assert not collisions, "Template namespace collisions: %s"%collisions
