from lmfdb.base import LmfdbTest
from lmfdb.db_backend import PostgresDatabase
from sage.parallel.decorate import parallel
from sage.all import ZZ, sqrt
import multiprocessing
from traceback import print_exc
import logging

ncpus = min(multiprocessing.cpu_count(), 40)

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
            print str(err)
            print_exc()
            return url

    @parallel(ncpus = ncpus)
    def all_newforms(self, level, weight):
        logging.getLogger().disabled = True
        db = PostgresDatabase()
        logging.getLogger().disabled = False
        errors = []
        n = 0
        for nf in list(db.mf_newforms.search({'level':level,'weight':weight}, ['label', 'dim'])):
            n += 1
            url = self.newform(nf['label'],  nf['dim'])
            if url is not None:
                errors.append(url)

        if errors:
            print "Tested %d pages  with level = %d weight = %d with %d errors occurring on the following pages:" %(n, level, weight, len(errors))
            for url in errors:
                print url

        return errors

    @parallel(ncpus = ncpus)
    def all_newspaces(self, level, weight):
        logging.getLogger().disabled = True
        db = PostgresDatabase()
        logging.info.disabled = False
        errors = []
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
            page = self.tc.get(url)
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
        except Exception as err:
                print "Error on page "+url
                print str(err)
                print print_exc()
                errors.append(url)
        return errors


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
                print print_exc()
                errors.append(url)

        #test wrong parity newspaces
        for ns in list(db.mf_newspaces.search({'level':level,'weight':weight, 'char_parity':1 if bool(weight % 2) else -1}, ['label', 'dim'])):
            label = ns['label']
            dim = ns['dim']
            url = '/ModularForm/GL2/Q/holomorphic/' + label.replace('.','/') + '/'
            try:
                assert dim == 0
                page = self.tc.get(url)
                assert "There are no modular forms of weight" in page.data
                assert "odd" in page.data
                assert "even" in page.data
            except Exception as err:
                print "Error on page "+url
                print str(err)
                print print_exc()
                errors.append(url)


        if errors:
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
        formerrors = list(self.all_newforms(todo))
        spaceserrors = list(self.all_newspaces(todo))
        errors = []
        for k, io in enumerate([formerrors, spaceserrors]):
            for i, o in io:
                if not isinstance(o, list):
                    if k == 0:
                        command = "all_newforms"
                    else:
                        command = "all_newspaces"
                    errors.append( [command, i] )
                else:
                    errors.extend(o)

        if errors == []:
            print "No errors!"
        else:
            print "Errors occurring on the following pages:"
            for url in errors:
                print url
            assert False



