from lmfdb.base import LmfdbTest
from lmfdb.db_backend import PostgresDatabase
from sage.parallel.decorate import parallel
from sage.all import ZZ, sqrt
import multiprocessing

ncpus = min(multiprocessing.cpu_count(), 4)

class CMFTest(LmfdbTest):
    def runTest():
        pass

    def newform(self, label, dim):
        url = '/ModularForm/GL2/Q/holomorphic/' + label.replace('.','/') + '/'
        try:
            page = self.tc.get(url)
            assert label in page.data
            if dim <= 80:
                assert 'L-function %s' % label in page.data
            assert 'L-function %s.%s' % tuple(label.split('.')[:2])  in page.data
            assert 'Analytic rank' in page.data
            if dim == 1:
                assert 'Satake parameters' in page.data
            else:
                assert 'Embeddings' in page.data
            return None
        except Exception as err:
            print "Error on page "+url
            print str(e)
            return url

    @parallel(ncpus = ncpus)
    def all_newforms(self, level, weight):
        db = PostgresDatabase()
        errors = []
        n = 0
        for nf in list(db.mf_newforms.search({'level':level,'weight':weight}, ['label', 'dim'])):
            n += 1
            url = self.newform(nf['label'],  nf['dim'])
            if url is not None:
                errors.append(url)

        if not errors:
            print "Tested %d pages with level = %d weight = %d with no errors" % (n, level, weight)
        else:
            print "Tested %d pages  with level = %d weight = %d with %d errors occurring on the following pages:" %(n, level, weight, len(errors))
            for url in errors:
                print url

        return errors

    @parallel(ncpus = ncpus)
    def all_newspaces(self, level, weight):
        db = PostgresDatabase()
        errors = []
        n = 0
        gamma1_dim = 0
        url = '/ModularForm/GL2/Q/holomorphic/%d/%d/' % (level, weight)
        newspaces = list(db.mf_newspaces.search({'level':level,'weight':weight}, ['label', 'dim']))
        newforms = list(db.mf_newforms.search({'level':level,'weight':weight}, ['label', 'space_label', 'dim']))
        dim = db.mf_gamma1_subspaces({'level':level,'weight':weight}, projection = 'dim')
        if dim is None:
            assert newspaces == []
            assert newforms == []
            return
        try:
            n += 1
            total_dim = 0
            page = self.tc.get(url)
            assert 'The following table gives the dimensions of various subspaces of' in page.data
            for space in newspaces:
                assert space['label'] in page.data
                total_dim += space['dim']
            assert gamma1_dim ==  db.mf_gamma1_subspaces({'level':level,'weight':weight}, projection = 'dim')

            for form in newforms:
                assert form['label'] in page.data
        except Exception as err:
                print "Error on page "+url
                print str(err)
                errors.append(url)


        for ns in newspaces:
            n += 1
            label = ns['label']
            dim = ns['dim']
            gamma1_dim += dim
            url = '/ModularForm/GL2/Q/holomorphic/' + label.replace('.','/') + '/'
            try:
                page = self.tc.get(url)
                space_dim = 0
                assert label in page.data
                for nf in newforms:
                    if nf['space_label'] == label:
                        assert nf['label'] in page.data
                        space_dim += nf['dim']
                assert space_dim == dim
            except Exception as err:
                print "Error on page "+url
                print str(err)
                errors.append(url)

        if not errors:
            print "Tested %d pages with level = %d weight = %d with no errors" % (n, level, weight)
        else:
            print "Tested %d pages  with level = %d weight = %d with %d errors occurring on the following pages:" %(n, level, weight, len(errors))
            for url in errors:
                print url

        return errors



    def test_all(self):
        todo = []
        from lmfdb.db_backend import db
        for Nk2 in range(1, db.mf_newforms.max('Nk2') + 1):
            for N in ZZ(Nk2).divisors():
                k = sqrt(Nk2/N)
                if k in ZZ:
                    todo.append((N, int(k)))
        formerros = list(self.all_newforms(todo))
        spaceserrors = list(self.all_newspaces(todo))
        errors = []
        for io in [formerros, spaceserrors]:
            for _, o in formerros:
                errors.extend(o)

        if not errors:
            print "No errors!"
        else:
            print "Errors occurring on the following pages:"
            for url in errors:
                print url



