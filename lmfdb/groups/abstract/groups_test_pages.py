from lmfdb.tests import LmfdbTest
from lmfdb.lmfdb_database import LMFDBDatabase
from sage.parallel.decorate import parallel
import multiprocessing
from sage.all import ZZ, floor, ceil
from traceback import print_exc
import logging
import time
from sage.libs.gap.libgap import libgap

ncpus = min(multiprocessing.cpu_count(), 10)

class GroupsTest(LmfdbTest):
    def runTest(self):
        pass

    def setUp(self):
        from lmfdb.app import app
        app.config["TESTING"] = True
        self.app = app
        self.tc = app.test_client()
        import lmfdb.website
        assert lmfdb.website
        logging.getLogger().disabled = True
        self.db = LMFDBDatabase()
        logging.getLogger().disabled = False

    def abstract_group(self, label):
        url = f'/Groups/Abstract/{label}'
        try:
            now = time.time()
            page = self.tc.get(url)
            text = page.get_data(as_text=True)
            load = time.time() - now
            for s in [label, "Rank"]:
                assert s in text
            return load, url
        except Exception as err:
            print(f"Error on page {url}")
            print(str(err))
            print_exc()
            return None, url

    @parallel(ncpus=ncpus)
    def abstract_groups_of_order(self, N, imin, imax):
        self.setUp()
        errors = []
        res = []
        n = 0
        for label in self.db.gps_groups.search({"order": N, "counter": {"$gte": imin, "$lte": imax}}, "label"):
            n += 1
            load, url = self.abstract_group(label)
            if load is None:
                errors.append(url)
            res.append((load, url))
        if errors:
            print(f"Tested {n} pages ({N}.{imin} to {N}.{imax}) with {len(errors)} errors occurring on the following pages:")
            for url in errors:
                print(url)
        else:
            print(f"No errors while running {n} tests ({N}.{imin} to {N}.{imax})!")
        return res

    def all_small_groups(self, maxord=None, chunksize=1000):
        inputs = []
        if maxord is None:
            # We want to be able to use NrSmallGroups
            maxord = 511
        for n in range(1, maxord+1):
            numgps = ZZ(libgap.NrSmallGroups(n))
            numchunks = ceil(numgps / chunksize)
            for i in range(numchunks):
                inputs.append((n, 1 + floor(i / numchunks * numgps), floor((i+1) / numchunks * numgps)))
        res = sum((outp for inp, outp in self.abstract_groups_of_order(inputs)), [])
        errors = [url for t, url in res if t is None]
        errors
        working_urls = sorted([(t, url) for t, url in res if t is not None])
        times = [t for t, url in working_urls]
        total = len(times)
        if errors:
            print(f"Tested {total + len(errors)} pages with {len(errors)} errors occurring on the following pages:")
            for url in errors[:10]:
                print(url)
            if len(errors) > 10:
                print(f"Plus {len(errors) - 10} more")
        else:
            print("No errors while running the tests!")
        print(f"Average loading time: {sum(times)/total:.2f}")
        print(f"Min: {times[0]:.2f}, Max: {times[-1]:.2f}")
        print("Quartiles: %.2f %.2f %.2f" % tuple(times[max(0, int(total*f) - 1)] for f in [0.25, 0.5, 0.75]))
        print("Slowest pages:")
        for t, u in working_urls[-10:]:
            print(f"{t:.2f} - {u}")
        if total > 2:
            print("Histogram")
        h = 0.5
        nbins = (times[-1] - times[0]) / h
        while nbins < 50:
            h *= 0.5
            nbins = (times[-1] - times[0]) / h
        nbins = ceil(nbins)
        bins = [0]*nbins
        i = 0
        for t in times:
            while t > (i+1)*h + times[0]:
                i += 1
            bins[i] += 1
        for i, b in enumerate(bins):
            d = 100*float(b)/total
            print('%.2f\t|' % ((i + 0.5)*h + times[0]) + '-'*(int(d)-1) + '| - %.2f%%' % d)
