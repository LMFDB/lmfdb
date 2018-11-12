from lmfdb.base import LmfdbTest
from lmfdb.db_backend import PostgresDatabase
from sage.parallel.decorate import parallel
from sage.all import ZZ, sqrt, ceil
import multiprocessing
from traceback import print_exc
import logging
import time

ncpus = min(multiprocessing.cpu_count(), 10)

class CMFTest(LmfdbTest):
    def runTest():
        pass

    def newform(self, label, dim):
        url = '/ModularForm/GL2/Q/holomorphic/' + label.replace('.','/') + '/'
        try:
            now = time.time()
            page = self.tc.get(url)
            load = time.time() - now
            k = int(label.split(".")[1])
            if k > 1:
                assert label in page.data
                if dim <= 80:
                    assert 'L-function %s' % label in page.data
                assert 'L-function %s.%s' % tuple(label.split('.')[:2])  in page.data
                assert 'Analytic rank' in page.data
            if dim == 1:
                assert 'Satake parameters' in page.data
            else:
                assert 'Embeddings' in page.data
            return (load, url)
        except Exception as err:
            print "Error on page "+url
            print str(err)
            print_exc()
            return (None, url)

    @parallel(ncpus = ncpus)
    def all_newforms(self, level, weight):
        logging.getLogger().disabled = True
        db = PostgresDatabase()
        logging.getLogger().disabled = False
        res = []
        errors = []
        n = 0
        for nf in list(db.mf_newforms.search({'level':level,'weight':weight}, ['label', 'dim'])):
            n += 1
            r = self.newform(nf['label'],  nf['dim'])
            res.append(r)
            if r[0] is None:
                errors.append(r[1])

        if errors:
            print "Tested %d pages  with level = %d weight = %d with %d errors occurring on the following pages:" %(n, level, weight, len(errors))
            for url in errors:
                print url

        return res

    @parallel(ncpus = ncpus)
    def all_newspaces(self, level, weight):
        logging.getLogger().disabled = True
        db = PostgresDatabase()
        logging.info.disabled = False
        errors = []
        res = []
        n = 0
        url = '/ModularForm/GL2/Q/holomorphic/%d/%d/' % (level, weight)
        newspaces = list(db.mf_newspaces.search({'level':level,'weight':weight, 'char_parity':-1 if bool(weight % 2) else 1}, ['label', 'dim']))
        newforms = list(db.mf_newforms.search({'level':level,'weight':weight}, ['label', 'space_label', 'dim']))
        dim = db.mf_gamma1_subspaces.lucky({'level':level,'weight':weight, 'sub_level':level, 'sub_mult': 1}, projection = 'sub_dim')
        if dim is None:
            for ns in newspaces:
                assert ns['dim'] == 0
            assert newforms == []
            return []

        try:
            n += 1
            gamma1_dim = 0
            now = time.time()
            page = self.tc.get(url)
            load = time.time() - now
            assert 'The following table gives the dimensions of various subspaces of' in page.data
            for space in newspaces:
                assert space['label'] in page.data
                gamma1_dim += space['dim']
            assert gamma1_dim == dim

            gamma1_dim = 0
            for form in newforms:
                assert form['label'] in page.data
                gamma1_dim += form['dim']
            assert gamma1_dim == dim
            res.append((load, url))

        except Exception as err:
                print "Error on page "+url
                print str(err)
                print print_exc()
                errors.append(url)
                res.append((None, url))


        for ns in newspaces:
            n += 1
            label = ns['label']
            dim = ns['dim']
            gamma1_dim += dim
            url = '/ModularForm/GL2/Q/holomorphic/' + label.replace('.','/') + '/'
            try:
                now = time.time()
                page = self.tc.get(url)
                load = time.time() - now
                space_dim = 0
                assert label in page.data
                for nf in newforms:
                    if nf['space_label'] == label:
                        assert nf['label'] in page.data
                        space_dim += nf['dim']
                assert space_dim == dim
                res.append((load, url))
            except Exception as err:
                print "Error on page "+url
                print str(err)
                print print_exc()
                errors.append(url)
                res.append((None, url))

        #test wrong parity newspaces
        for ns in list(db.mf_newspaces.search({'level':level,'weight':weight, 'char_parity':1 if bool(weight % 2) else -1}, ['label', 'dim'])):
            label = ns['label']
            dim = ns['dim']
            url = '/ModularForm/GL2/Q/holomorphic/' + label.replace('.','/') + '/'
            try:
                now = time.time()
                page = self.tc.get(url)
                load = time.time() - now
                assert "There are no modular forms of weight" in page.data
                assert "odd" in page.data
                assert "even" in page.data
                res.append((load, url))
            except Exception as err:
                print "Error on page "+url
                print str(err)
                print print_exc()
                errors.append(url)
                res.append((None, url))


        if errors:
            print "Tested %d pages  with level = %d weight = %d with %d errors occurring on the following pages:" %(n, level, weight, len(errors))
            for url in errors:
                print url

        return res



    def test_all(self):
        todo = []
        from lmfdb.db_backend import db
        maxNk2 = db.mf_newforms.max('Nk2')
        for Nk2 in range(1, maxNk2 + 1):
            for N in ZZ(Nk2).divisors():
                k = sqrt(Nk2/N)
                if k in ZZ:
                    todo.append((N, int(k)))
        formerrors = list(self.all_newforms(todo))
        spaceserrors = list(self.all_newspaces(todo))
        errors = []
        res = []
        for k, io in enumerate([formerrors, spaceserrors]):
            for i, o in io:
                if not isinstance(o, list):
                    if k == 0:
                        command = "all_newforms"
                    else:
                        command = "all_newspaces"
                    errors.append( [command, i] )
                else:
                    res.extend(o)

        if errors == []:
            print "No errors while running the tests!"
        else:
            print "Unexpected errors occurring while running:"
            for e in errors:
                print e

        broken_urls = [ u for l, u in res  if u is None ]
        working_urls = [ (l, u) for l, u in res if u is not None]
        working_urls.sort(key= lambda elt: elt[0])
        just_times = [ l for l, u in working_urls]
        total = len(working_urls)
        if broken_urls == []:
            print "All the pages passed the tets"
            if total > 0:
                print "Average loading time: %.2f" % (sum(just_times)/total,)
                print "Min: %.2f Max %.2f" % (just_times[0], just_times[-1])
                print "Quartiles: %.2f %.2f %.2f" % tuple([just_times[ max(0, int(total*f) - 1)] for f in [0.25, 0.5, 0.75]])
                print "Slowest pages:"
                for t, u in working_urls[-10:]:
                    print "%.2f - %s" % (t,u)
            if total > 2:
                print "Histogram"
                h = 0.5
                nbins = (just_times[-1] - just_times[0])/h
                while  nbins < 50:
                    h *= 0.5
                    nbins = (just_times[-1] - just_times[0])/h
                nbins = ceil(nbins)
                bins = [0]*nbins
                i = 0
                for elt in just_times:
                    while elt > (i + 1)*h + just_times[0]:
                        i += 1
                    bins[i] += 1
                for i, b in enumerate(bins):
                    d = 100*float(b)/total
                    print '%.2f\t|' %((i + 0.5)*h +  just_times[0]) + '-'*(int(d)-1) + '| - %.2f%%' % d
        else:
            print "These pages didn't pass the tests:"
            for u in broken_urls:
                print u









