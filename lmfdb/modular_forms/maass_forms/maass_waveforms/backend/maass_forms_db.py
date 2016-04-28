# -*- coding: utf-8 -*-
### Class for computing and storing Maass waveforms.
### Use either mongodd or SQL

import pymongo
import gridfs
import bson
from sage.symbolic.expression import Expression
import datetime
from lmfdb import base
from sage.all import Integer, DirichletGroup, is_even, loads, dumps, cached_method
from lmfdb.modular_forms.maass_forms.maass_waveforms import mwf_logger
import math
logger = mwf_logger
try:
    from dirichlet_conrey import *
except:
    logger.critical("dirichlet_conrey.pyx cython file is not available ...")
import cython


class MaassDB(object):
    r"""
    Compute and store Maass forms
    """
    def __init__(self, host='localhost', port=27017, show_collection='all', insert_collection='FS', db_type='mongo', verbose=0):
        r"""
        Use a mongodb database to store and show Maass forms
        INPUT:

        - host -- host
        - port -- port
        - show_collection -- the collection to show (use 'all' to show all collections)
        - insert_collection -- the collection to insert computed data into
        db_type = the preferred database type
        """
        self._host = host
        self._port = port
        # self._author=author
        self._show_collection_name = show_collection
        self._collection_name = insert_collection
        self._db_type = db_type
        if db_type == 'mongo':
            if not self.setup_mongodb(host, port):
                self._db_type = 'file'
        else:
            raise NotImplementedError("Only mongodb implemented!")
        # if self._db_type=='file':
        #    if not self.setup_file(dir,file):
        #        raise ValueError,"Could not setup Maass form storage on file!"
        self._levels = {}
        self._ongoing_work_id = None
        self._list_of_jobs = {}
        self._verbose = verbose
        self.table = {}

    def __repr__(self):
        s = "Maass waveforms database at {0}:{1}".format(self._host, self._port)
        return s

    def setup_mongodb(self, host='localhost', port=27017):

        try:
            constr = "{0}:{1}".format(host, port)
            Con = base.getDBConnection()
            self._Con = Con
        except:  # AutoReconnect:
            logger.critical("No database found at {0}".format(constr))
            logger.critical("Please specifiy other host/port")
            return False
        D = Con['MaassWaveForms']
        self._mongo_db = D
        self._collection = D[self._collection_name]
        if True: # .collection_names() is not supported -- self._show_collection_name in D.collection_names():
            self._show_collection = [self._show_collection_name]
        if self._show_collection_name == 'all':
            self._show_collection = []
            ## We currently merged both collections.
            for cn in ['FS']:  # ,'HT']: #D.collection_names():
                if True: # no support for collection_names any more# cn in D.collection_names():
                    self._show_collection.append(D[cn])

        # Stores a large amount of coefficients at two cusps (to be able to estimate error)
        self._collection_coeff = D['Coefficients']
        # Stores a small amount of coefficients in each cusp
        # self._collection_funs_coeff = D['Function_Coefficients']
        self._collection_problems = D['Problems']
        self._collection_progress = D['Progress']
        self._collection_coeff_progress = D['CoeffProgress']
        self._job_history = D['job_history']
        self._maassform_plots = D['maassform_plots']
        return True

    # def setup_file(self,dir='',filename='maassforms_db'):
    #     fname = dir+filename+".txt"
    #     # Test if we can write to this file.
    #     try:
    #         fp = open(fname,'w')
    #     except IOError:
    #         raise ValueError,"Could not write file {0}".format(fname)
    #     self._fname=fname
    #     self._lock_fname=dir+"."+filename+".lock"
    #     # Used to assure no simultaneous reading or writing occur

    def put_maass_form(self, data):
        r"""
        Write the maass form G to the database of self
        """
        try:
            self.check_data(data)
            if self._db_type == 'mongo':
                self.put_maass_form_mongo(data)
            else:
                mwf_logger.info('Form not stored. Storing to file not set up.')
                #self.put_maass_form_file(data)
        except KeyError as ex:
            mwf_logger.info(str(ex.args))

    def check_data(self, data):
        r"""
        Check that the format is what we want...
        data = dict with keys [level,weight,character,Symmetry,Eigenvalue,
        error,M0, Conrey (True/false), Cusp_evs
        Y,F,dim]
        where G is an optional MaassWaveForm object
        Y and M are the parameters used to compute the Maass form in question
        Raises a KeyError if a key is missing or data is not a dict
        """
        if not isinstance(data, dict):
            raise KeyError('Data not a dictionary')
        if 'level' not in data:
            raise KeyError('level not in data keys')
        if 'Eigenvalue' not in data:
            raise KeyError('Eigenvalue not in data keys')
        if 'error' not in data:
            raise KeyError('err not in data keys')
        ## The rest have default values
        # weight=0,ch=1,sym_type,M0,Y,G=data

    def put_maass_form_mongo(self, data):
        R = float(data.get('Eigenvalue', 0))
        level = int(data.get('Level', 0))
        err = float(data.get('Error', 0))
        weight = int(data.get('Weight', 0))
        dim = int(data.get('Dim', 1))
        ch = int(data.get('Character', 0))
        sym_type = int(data.get('Symmetry', -1))
        Y = float(data.get('Y', 0))
        M0 = int(data.get("M0", 0))
        F = data.get("F")
        cn_evs = data.get("Cusp_evs", [])
        # Check if this record already exists
        isin, numc0, errin, idd0 = self.is_data_in_table_mongo(level,
                                                weight, ch, sym_type, R, err)
        mwf_logger.debug("Is in database:".format(isin))
        if not data.get('Conrey', False):
            # Then we have to convert the character to Conrey's label
            ch = db.getDircharConrey(level, ch)
        insert_data = {'Level': level, 'Weight': weight,
                       'Character': ch, 'Symmetry': sym_type,
                       'Error': err,
                       'Conrey': int(1),  # we leave this indicator here until the convention is more widespread
                       'Dim': dim,
                       'Eigenvalue': R, 'M0': M0, 'Y': Y,
                       'date': bson.datetime.datetime.utcnow(),
                       'Cusp_evs': cn_evs
                       }
        ## If data is already there with equal or better error estimate
        ## Then we leave it be.
        idd = 0
        if isin == 0:
            mwf_logger.debug("inserting:".format(insert_data))
            idd = self._collection.insert(insert_data)
        else:
            if (isin == 1 and (errin == 0 or errin > err)):
                key = {'_id': idd0}
                idd = self._collection.update(key, insert_data, upsert=True)
            else:
                idd = idd0
        # See if we have coefficients to insert as well.
        if F is None:
            coeffs = []
            numc = 0
        else:
            if hasattr(F, "is_automorphic_form"):
                C = F._coeffs[0]  # Dictionary of coefficients of all cusps
                numc = len(C[0])

            elif isinstance(F, dict):  # F is just the coefficients.
                if level == 1 and len(F[0]) == 1:
                    C = F[0]
                elif level > 1 and len(F) == 1:
                    C = F[0]
                else:
                    C = F
                numc = len(C[0])
            # For now we assume we have contigous coefficients
            # so if we now have more than before we replace the old ones.
            if numc > numc0:
                key = {'_id': idd}
                inserts = {"$set": {"Coefficients": C}}
                self._collection_coeff.update(key, inserts, upsert=True)
                logger.debug("Inserted coeficients")

    def has_level_weight_char(self, level, weight, ch):
        find_data = {'Level': int(level),
                     'Weight': int(weight),
                     'Character': int(ch)}
        return self._collection.find(find_data).count()

    def collection_names(self):
        return self._show_collection_name

    def metadata(self):
        return self._mongo_db.metadata

    def is_data_in_table_mongo(self, level, weight, ch, sym_type, R, err=0):
        ep0 = max(1.0E-8, 2 * RR(err))

        find_data = {'Level': level,
                     'Weight': weight,
                     'Character': ch,
                     'Symmetry': sym_type,
                     'Eigenvalue': {"$gte": float(R) - float(ep0), "$lt": float(R) + float(ep0)}
                     }
        mwf_logger.debug("find_Data:{0}".format(find_data))
        if self._collection.find(find_data).count() == 0:
            return 0, 0, 0, 0
        x = self._collection.find(find_data)[0]
        mwf_logger.debug("x={0}".format(x))
        numc = x.get('Numc', 0)
        err = x.get('Error', 0)
        idd = x.get('_id', 0)
        return 1, numc, err, idd

    def register_work(self, level, ch, weight, R1, R2, dim, verbose=0, tol=0, force=False):
        r"""
        Make an entry in the database before starting a job.
        """
        data = {'Level': int(level),
                'Weight': int(weight),
                'Character': int(ch)}
        if verbose > 0:
            mwf_logger.debug(
                "Register work: N,weight,ch={0},{1},{2},{3} in {4}, {5}".format(level, weight, ch, R1, R2))
        try:
            t0 = self._collection_progress.find(data)
            if t0.count() > 0:  # Check more detail
                ep0 = float(max(1.0E-8, 2 * RR(tol)))
                data['R1'] = {"$gte": float(R1) - ep0}
                data['R2'] = {"$lte": float(R2) + ep0}
                t1 = self._collection_progress.find(data)
                if t1.count() > 0:
                    if verbose > 0:
                        print "Already have work going on in this range!"
                    if not force:
                        return 0
            # Else no ongoing work. registering new work
            data['R1'] = float(R1)
            data['R2'] = float(R2)
            data['date'] = bson.datetime.datetime.utcnow()
            idd = self._collection_progress.insert(data)
            self._ongoing_work_id = idd
        except Exception as er:
            print "Couldnt register progress!"
            print "er=", er
            pass

    def deregister_work(self, jobid=None):  # ,level=None,ch=None,weight=None,R1=None,R2=None,dim=None,verbose=0,tol=0):
        if self._ongoing_work_id:
            idd1 = self._ongoing_work_id
        elif isinstance(jobid, bson.objectid.ObjectId):
            idd1 = jobid
        else:
            ## If we try to deregister a nonexistent work
            print "self._ongoing_work_id=", self._ongoing_work_id
            print "jobid=", jobid, type(jobid)
            return
        # Now we should have a unique id
        f = self._collection_progress.find({'_id': idd1})
        if f.count() > 0:
            ff = f.next()
            date_begun = ff['date']
            now = bson.datetime.datetime.utcnow()
            elapsed = now - date_begun
            date_beguns = ff['date'].strftime("%d:%m:%y %H:%M:%s")
            if self._verbose > 0:
                print "Removing N,weight,ch,R1,R2".format(ff.get('Level'), ff.get('Weight'), ff.get('Character'), ff.get('R1'), ff.get('R2'))
                print "Work took time:".format(elapsed)
            data = {'Level': ff.get('Level'), 'Weight': ff.get('Weight'), 'Character': ff.get('Character'), 'R1': ff.get('R1'), 'R2': ff.get('R2'),
                    'start_time': ff.get('date'), 'stop_time': now, 'elapsed': str(elapsed).split(".")[0]}
            self._job_history.insert(data)
            self._collection_progress.remove({'_id': idd1})
            if idd1 in self._list_of_jobs.values():
                j = self._list_of_jobs.values().index(idd1)
                self._list_of_jobs.pop(j)
        self._ongoing_work_id = None
        self._ongoing_coeff_work_id = None

    def register_coeff_work(self, data, verbose=0, tol=0):
        r"""
        Make an entry in the database before starting a job.
        """
        data = mongify_dict(data)
        find_data = {'Level': data.get('Level', 0),
                     'Weight': data.get('Weight', 0),
                     'Character': data.get('Character', 0),
                     'NA': data.get('NA', 0),
                     'NB': data.get('NB', 0),
                     'Eigenvalue': data.get('Eigenvalue', 0)}
        if verbose > 0:
            s = "Register coefficient computation:"
            s += "N,weight,ch,R=", level, weight, ch, R
            s += " in range NA,NB=", NA, NB
            print s
        try:
            t0 = self._collection_progress.find(data)
            if t0.count() > 0:  # Check more detail
                if verbose > 0:
                    print "Already have work going on in this range!"
                return 0
            # Else no ongoing work. registering new work
            insert_data = find_data
            insert_data['date'] = bson.datetime.datetime.utcnow()
            idd = self._collection_coeff_progress.insert(insert_data)
            self._ongoing_coeff_work_id = idd
        except Exception as ex:
            print "Couldnt register coefficient work!"
            print "ex=", ex
            pass
        return 1

    def deregister_coeff_work(self, data={}):
        idd = self._ongoing_coeff_work_id
        if self._ongoing_coeff_work_id is not None:
            self._collection_coeff_progress.remove({'_id': idd})
        elif data != {}:
            data = mongify_dict(data)
            idd = self._collection_coeff_progress.remove(data)
        else:
            print "Did not find a job to remove!"

    def find_Maass_form_id(self, data={}, **kwds):
        r"""
        Find a Maass form matching the information in the dictionary data
        """
        find_data = arg_to_search_parameters(data, **kwds)
        # print "find_data",find_data
        res = []
        for collection in self._show_collection:
            f = collection.find(find_data)
            if f.count() > 0:
                for x in f:
                    xid = x.get('_id', None)
                    if not xid:
                        if self._verbose > 0:
                            mwf_logger.debug("Error: got record without id:{0}".format(x))
                            mwf_logger.debug("coeffid={0}".format(coeff_id))
                    res.append(x['_id'])
        return res

    def get_Maass_forms(self, data={}, fields = None, **kwds):
        verbose = kwds.get('verbose', 0)
        collection = kwds.get('collection', 'all')
        do_sort = kwds.get('do_sort', True)
        if verbose > 0:
            print "get_Maass_forms for data=", data
        if isinstance(data, bson.objectid.ObjectId):
            find_data = {'_id': data}
        elif isinstance(data, str):
            find_data = {'_id': bson.objectid.ObjectId(data)}
        else:
            if verbose > 0:
                print "get search parameters!"
            find_data = arg_to_search_parameters(data, **kwds)
        if isinstance(data, dict):
            format_data = arg_to_format_parameters(data, **kwds)
        else:
            format_data = arg_to_format_parameters({}, **kwds)
        sorting = [('Weight', pymongo.ASCENDING), ('Level', pymongo.ASCENDING),
             ('Character', pymongo.ASCENDING), ('Eigenvalue', pymongo.ASCENDING)]
        if verbose > 0:
            print "find_data=", find_data
            print "format_data=", format_data

        res = []
        skip0 = format_data['skip']
        skip = skip0
        limit0 = format_data['limit']
        limit = limit0

        # print "SHow collection:",self._show_collection
        if fields is not None: # make sure that fields is a list 
            fields = list(fields)
        for collection in self._show_collection:
            if verbose > 0:
                print "skip=", skip
                print "limit=", limit
            cname = format_data.get('collection_name', '')
            if cname != '' and cname != collection.name:
                continue
            if limit <= 0:
                continue
            if do_sort:
                finds = collection.find(find_data, fields,
                                    sort=sorting).skip(skip).limit(limit)
            else:
                finds = collection.find(find_data, fields)
                
            skip = 0
            if verbose > 0:
                print "find[", collection.name, "]=", finds.count()
            limit = limit - finds.count(True)
            for x in finds:
                res.append(x)
        return res

    def get_next_maassform_id(self, level, character, weight,
                              eigenvalue, maass_id):
        if isinstance(maass_id, bson.objectid.ObjectId):
            _id = maass_id
        else:
            _id = bson.objectid.ObjectId(maass_id)

        limit = 10
        search = {'level': level, 'char': character,
              'R1': eigenvalue, 'Newform' : None, 'weight' : weight}
        fields = {'_id': True}
        forms = self.get_Maass_forms(search, fields, 
                               do_sort = True, limit = limit)
        if len(forms) == 0 or (
            len(forms) == 1 and _id == forms[0]['_id'] ):
            return None
        
        i = 0
        while _id != forms[i]['_id']:
            i += 1
            if i == len(forms) - 1:
                return forms[0]['_id']
        return forms[i+1]['_id']
    
    def get_prev_maassform_id(self, level, character, weight,
                              eigenvalue, maass_id):
        if isinstance(maass_id, bson.objectid.ObjectId):
            _id = maass_id
        else:
            _id = bson.objectid.ObjectId(maass_id)

        limit = 10000
        search = {'level': level, 'char': character,
              'R2': eigenvalue, 'Newform' : None, 'weight' : weight}
        fields = {'_id': True}
        forms = self.get_Maass_forms(search, fields, 
                               do_sort = True, limit = limit)
        if len(forms) == 0 or (
            len(forms) == 1 and _id == forms[0]['_id'] ):
            return None
        
        i = len(forms) - 1
        while _id != forms[i]['_id']:
            i -= 1
            if i == 0:
                return forms[len(forms) - 1]['_id']
        return forms[i-1]['_id']
    

    def get_maassform_plot_by_id(self, maass_id):
        r"""
        """
        coll = self._maassform_plots
        if isinstance(maass_id, bson.objectid.ObjectId):
            find_data = {'maass_id': maass_id}
        else:
            find_data = {'maass_id': bson.objectid.ObjectId(maass_id)}
        data = coll.find_one(find_data)
        return data

    def maassform_has_plot(self, maass_id):
        coll = self._maassform_plots
        if isinstance(maass_id, bson.objectid.ObjectId):
            find_data = {'maass_id': maass_id}
        else:
            find_data = {'maass_id': bson.objectid.ObjectId(maass_id)}
        data = coll.find(find_data, {'eigenvalue': True})
        if data.count()>0:
            return True
        else:
            return False


    def get_coefficients(self, data={}, verbose=0, **kwds):
        if verbose > 0:
            print "data=", data
        if '_id' in data:
            idd = [data['_id']]
        else:
            idd = self.find_Maass_form_id(data=data, **kwds)
        res = []
        get_filename = kwds.get('get_filename', '')
        for maassid in idd:
            if verbose > 0:
                print "id=", idd
            f = self._collection.find({'_id': maassid})
            if f.count() > 0:
                fn = f.next()
                nc = fn.get('Numc', 0)
                if verbose > 0:
                    print "fn=", fn
                if nc == 0:
                    continue
                cid = fn.get('coeff_id', None)
                if cid is None:
                    C1 = fn.get('Coefficients', [])
                    if C1 != []:
                        if get_filename != '':
                            Rst = str(R).split(".")
                            Rst = (Rst[0] + "." + Rst[1][0:10])[0:12]
                            fname = '{0}-{1}-{2}-{3}-{4}'.format(
                                f.get('Level'), f.get('Weight'),
                                f.get('Character'), f.get('Symmetry'), Rst)
                            return C1, fname
                        else:
                            return C1

                    continue
                f1 = gridfs.GridFS(self._mongo_db, 'Coefficients')
                if f1.exists(cid):
                    ff = f1.get(cid)
                    C = loads(ff.read())
                    if get_filename != '':
                        res.append((C, f1.name))
                    else:
                        res.append(C)
        return res

    def count(self, data={}, **kwds):
        filtered = kwds.get('filtered', False)
        find_data = arg_to_search_parameters(data, **kwds)
        num = 0
        if self._verbose > 0:
            print "find_data(count)=", find_data
        for c in self._show_collection:
            num += c.find(find_data).count(with_limit_and_skip=filtered)
        return num

    def levels(self):
        levels = []
        for c in self._show_collection:
            levels.extend(c.distinct('Level'))
        return list(set(levels))

    def weights(self, Level=0):
        weights = []
        for c in self._show_collection:
            if Level > 0:
                weights.extend(c.find({'Level': int(Level)}).distinct('Weight'))
            else:
                weights.extend(c.distinct('Weight'))
        return list(set(weights))

    def convert_db_to_Conrey(self, verbose=0):
        r"""
        Convert any non-conrey character labels
        """
        if verbose > 0:
            i = 0
        for coll in self._show_collection:
            n1 = coll.find().count()
            n2 = coll.find({'Conrey': {"$exists": True}}).count()
            if n2 < n1:
                ## Have to get in there...
                finds = coll.find({'Conrey': {"$exists": False}})
                for f in finds:
                    ## Defaults to trivial character
                    ch = f.get('Character', 0)
                    N = f.get('Level', 0)
                    if N == 0:
                        continue
                    cnr = self.getDircharConrey(N, ch)
                    key = {'_id': f.get('_id')}
                    values = {"$set": {'Conrey': int(1), 'Character': cnr}}
                    coll.update(key, values, upsert=False)
                    if verbose > 0:
                        i += 1
        if verbose > 0:
            print "Corrected {0} records!".format(i)

    def characters(self, Level=0, Weight=0):
        characters = []
        for c in self._show_collection:
            if Level > 0:
                finds = c.find({'Level': int(Level), 'Weight': int(Weight)}).distinct('Character')
                characters.extend(finds)
            else:
                characters.extend(c.distinct('Character'))
        return list(set(characters))

    def show_history(self, sort=[]):
        if sort != []:
            sorting = []
            for t in sort:
                if isinstance(t, str):
                    sorting.append((t, pymongo.ASCENDING))
                elif isinstance(t, tuple):
                    if isinstance(t[1], (int, Integer)):
                        sorting.append((t[0], int(t[1])))
        else:
            sorting = [(
                'Level', pymongo.ASCENDING), ('Weight', pymongo.ASCENDING), ('Character', pymongo.ASCENDING)]
        prog = self._job_history.find({}, sort=sorting)
        s = "========================================================================================= \n"
        s += "-------------- Job history for computations of Maass forms -------------------------- \n"
        s += "Nr.\tLevel \tWeight \tChar\tR1 \tR2 \tStart time \tStop time \tTotal time\n"
        j = 0
        for f in prog:
            date_begun = f['start_time']
            # elapsed_t = bson.datetime.datetime.utcnow() - date_begun
            elapsed_t = f['elapsed']
            s += str(j) + "\t" + self.display_one_job_record(f)
# s+="{0}\t{1}\t{2}\t{3}\t{4}\t{6}\t{7}
# \n".format(j,f['Level'],f['Weight'],f['Char'],f['R1'],f['R2'],f['date'],elapsed_t)
            self._list_of_jobs[j] = f['_id']
            j += 1
        s += "========================================================================================= \n"
        if j == 0:
            s = "No history of jobs in database!"
        print s

    def display_one_job_record(self, f):
        if not f:
            return ""
        elapsed_t = f.get('elapsed')
        elapsed_t = str(elapsed_t).split(".")[0]
        # date_beguns=date_begun.strftime("%d:%m:%y %H:%M:%s")
        date_beguns = f.get('start_time').strftime("%d.%m.%y %R")
        date_stops = f.get('stop_time').strftime("%d.%m.%y %R")
        s = "{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\n".format(f.get('Level'), f.get(
            'Weight', 0), f.get('ch', 0), f.get('R1', 0), f.get('R2', 0), date_beguns, date_stops, elapsed_t)
        return s

    def show_progress(self):
        prog = self._collection_progress.find({}, sort=[('Level', pymongo.ASCENDING)])
        s = "========================================================================================= \n"
        s += "-------------- Progress / Ongoing computations of Maass forms -------------------------- \n"
        s += "Nr.\tLevel \tWeight \tChar\tR1 \tR2 \tStart date \tTime elapsed \n"
        j = 0
        ## Reset and repopulate in case we want to remove one of these
        self._list_of_jobs = {}
        for f in prog:
            date_begun = f['date']
            elapsed_t = bson.datetime.datetime.utcnow() - date_begun

            s += str(j) + "\t" + self.display_one_progress_record(f)
# s+="{0}\t{1}\t{2}\t{3}\t{4}\t{6}\t{7}
# \n".format(j,f['Level'],f['Weight'],f['Char'],f['R1'],f['R2'],f['date'],elapsed_t)
            self._list_of_jobs[j] = f['_id']
            j += 1

        s += "========================================================================================= \n"
        if j == 0:
            s = "No ongoing jobs in database!"
        print s

    def display_one_progress_record(self, f):
        date_begun = f.get('date', bson.datetime.datetime.utcnow())
        elapsed_t = bson.datetime.datetime.utcnow() - date_begun
        elapsed_t = str(elapsed_t).split(".")[0]
        # date_beguns=date_begun.strftime("%d:%m:%y %H:%M:%s")
        date_beguns = date_begun.strftime("%d.%m.%y %R")
        s = "{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\n".format(f.get('Level'), f.get(
            'Weight', 0), f.get('Character', 0), f.get('R1', 0), f.get('R2', 0), date_beguns, elapsed_t)
        return s

    def remove_job(self, jobnr):
        if isinstance(jobnr, bson.objectid.ObjectId):
            self._collection_progress.deregister_work({'_id': jobnr})
        elif isinstance(jobnr, dict):  # treat job as a search pattern
            f = self._collection_progress.find(job)
            for x in f:
                print "Removing: \n"
                print self.display_one_progress_record(x)
                j = self._list_of_jobs.values().index(x['_id'])
                self._list_of_jobs.pop(j)
            self._collection_progress.deregister_work(x['_id'])

        elif isinstance(jobnr, (int, Integer)):
            jobid = self._list_of_jobs.get(int(jobnr), -1)
            if jobid < 0:
                f = list(self._collection_progress.find())
                if len(f) > 0:
                    jobid = f[jobnr]['_id']
            self.de
            (jobid)
            if self._verbose > 0:
                print "removed job nr. ", jobnr
        # update the self._list_of_jobs??

    def Dirchars(self, N, parity=0, conrey=True, verbose=0, refresh=False):
        r"""
        Returns a list of (Conrey) indices of representatives of
        even or odd  Dirichlet characters mod N
        """
        if conrey:
            f = self._mongo_db.DirChars.find_one({'Modulus': int(N), 'Parity': int(parity), 'Conrey': int(1)})
        else:
            f = self._mongo_db.DirChars.find_one(
                {'Modulus': int(N), 'Parity': int(parity), 'Conrey': {"$exists": False}})
        if verbose > 0:

            print "f=", f
        if f is not None:
            return f.get('Chars')
        D = DirichletGroup(N)
        DG = D.galois_orbits()
        if parity == 0:
            DGG = filter(lambda x: x[0].is_even(), DG)
        else:
            DGG = filter(lambda x: x[0].is_odd(), DG)
        l = []
        if verbose > 0:
            print "DG=", DGG
        for x in DGG:
            xi = D.list().index(x[0])
            if conrey:
                xi = self.getDircharConrey(N, xi)
            l.append(int(xi))
        if conrey:
            f = self._mongo_db.DirChars.insert(
                {'Modulus': int(N), 'Chars': l, 'Parity': int(parity), 'Conrey': int(1)})
        else:
            f = self._mongo_db.DirChars.insert({'Modulus': int(N), 'Chars': l, 'Parity': int(parity)})
        return l

    @cached_method
    def getDircharConrey(self, N, j):
        f = self._mongo_db.DirCharsConrey.find_one({'Modulus': int(N)})
        if not f:
            Dl = DirichletGroup(N).list()
            res = range(len(Dl))
            for k in range(len(Dl)):
                x = Dl[k]
                res[k] = self.getDircharConreyFromSageChar(x)
            self._mongo_db.DirCharsConrey.insert({'Modulus': int(N), 'chars': res})
            return res[j]
        else:
            res = f.get('chars')[j]
            return res

    def getDircharConreyFromSageChar(self, x):
        N = x.modulus()
        DC = DirichletGroup_conrey(N)
        for c in DC:
            if c.sage_character() == x:
                return c.number()
    from sage.all import euler_phi

    @cached_method
    def getDircharSageFromConrey(self, N, j):
        f = self._mongo_db.DirCharsSage.find_one({'Modulus': int(N)})
        if not f:
            DC = DirichletGroup_conrey(N)
            maxn = 0
            for c in DC:
                if c.number() > maxn:
                    maxn = c.number()
            res = range(maxn + 1)
            for c in DC:
                k = c.number()
                res[k] = self.getOneDircharSageFromConreyChar(c)
            self._mongo_db.DirCharsSage.insert({'Modulus': int(N), 'chars': res})
            return res[j]
        else:
            res = f.get('chars')[j]
            return res

    def getOneDircharSageFromConreyChar(self, x):
        N = x.modulus()
        DC = DirichletGroup(N)
        for j in range(len(DC.list())):
            c = DC.list()[j]
            if x.sage_character() == c:
                return j

    def show_data(self, also_empty=0, merge_collections=0, html=0, do_not_print=0, conrey=True):
        r"""
        Show which levels, characters and weights are in the database
        If merge_collections is set to 0 we display the collections separately
        """
        # print "levels=",levels
        res = {}
        for coll in self._show_collection:
            res[coll.name] = {}
            # print "name=",coll.name
            # print "res=",res
            weights = coll.distinct('Weight')
            for k in weights:
                res[coll.name][k] = {}
                levels = coll.find({'Weight': k}).distinct('Level')
                # print "levels=",levels
                for N in levels:
                    res[coll.name][k][N] = {}
                    if also_empty == 1:
                        if is_even(int(k)):
                            lc = self.Dirchars(N, parity=0, conrey=conrey)
                        else:
                            lc = self.Dirchars(N, parity=1, conrey=conrey)
                    else:
                        lc = coll.find({'Level': N, 'Weight': k}).distinct('Character')
                    for x in lc:
                        numr = coll.find({'Level': N, 'Weight': k, 'Character': x}).count()
                        num_wc = coll.find(
                            {'Level': N, 'Weight': k, 'Character': x, 'Numc': {"$gt": int(0)}}).count()
                        res[coll.name][k][N][x] = numr, num_wc
        if merge_collections == 1:
            resm = {}
            for col in res.keys():
                for k in res[col].keys():
                    if k not in resm:
                        resm[k] = {}
                    for N in res[col][k].keys():
                        if N not in resm[k]:
                            resm[k][N] = {}
                        for x in res[col][k][N].keys():
                            if x not in resm[k][N]:
                                resm[k][N][x] = res[col][k][N][x]
                            else:
                                numrm, num_wcm = resm[k][N][x]
                                numr, num_wc = res[col][k][N][x]
                                numrm += numr
                                num_wcm += num_wc
                                resm[k][N][x] = numrm, num_wcm
            res = resm

        if do_not_print == 1:
            return res
        # print "res=",res.keys()
        if html == 1:
            tr0 = "<tr>"
            tr1 = "</tr>"
            td0 = "<td>"
            td1 = "</td>"
            th0 = "<th>"
            th1 = "</th>"
            tstart = "<table>"
            tstop = "</table>"
        else:
            tr0 = ""
            tr1 = ""
            td0 = ""
            td1 = ""
            th0 = ""
            th1 = ""
            tstart = ""
            tstop = "=============================================== \n"
        if merge_collections == 0:
            s = ""
            for name in res.keys():
                s += tstart
                s += "Collection: {0}\n".format(name)
                for k in res[name].keys():
                    s += tr0
                    s += th0 + "Weight " + str(k) + th1 + tr1 + "\n"
                    if html:
                        s += "<tr><th>Level</th><th>Character<\th><th>Number of Maass forms</th></tr> \n"
                    else:
                        s += "Level \t Character \t Number of Maass forms \n"
                        s += "---------------------------------------------- \n"
                    lN = res[name][k].keys()
                    lN.sort()
                    for N in lN:
                        s += str(N) + "\t"
                        lx = res[name][k][N].keys()
                        lx.sort()
                        for x in lx:
                            if also_empty != 1:
                                s += "\t " + str(x) + ":" + str(res[name][k][N][x][0])
                            else:
                                if res[name][k][N][x][1] > 0:
                                    s += "\t " + str(x) + ":" + str(
                                        res[name][k][N][x][0]) + "(" + str(res[name][k][N][x][1]) + ")"
                                else:
                                    s += "\t " + str(x) + ":" + str(res[name][k][N][x][0])
                        s += "\n"
                    s += tstop

        print s

    def set_table(self, refresh=False):
        # if self.table!={}:
        #    return self.table
        f = gridfs.GridFS(self._mongo_db, 'Table')
        if refresh == False:
            if len(f.list()) > 0:
                fname = f.list()[0]
                ff = f.get_version(filename=fname)
                table = loads(ff.read())
                if ff.length > 0 and isinstance(table, dict):
                    self.table = table
                    return
        data = self.show_data(do_not_print=1, merge_collections=1, also_empty=1)
        table = {}
        table['collections'] = self._show_collection_name
        table['weights'] = data.keys()
        table['levels'] = self.levels()
        res = {}
        nrows = 0
        keylist = []
        for k in table['weights']:
            for N in table['levels']:
                r = (data.get(k, {})).get(N, {}).keys()
                if len(r) > nrows:
                    nrows = len(r)
                for x in (data.get(k, {})).get(N, {}).keys():
                    res[(k, N, x)] = data[k][N][x]
                    keylist.append((k, N, x))
        table['characters'] = range(nrows)
        table['data'] = res
        table['keylist'] = keylist
        table['nrows'] = 20
        table['ncols'] = 20  # =len(table['levels'])
        self.table = table
        f.put(dumps(table), filename='table')
        # self._mongo_db['Table'].insert({'Table':table})

    def show_problems(self):
        r"""
        Show which levels, characters and weights are in the database
        """
        res = {}
        weights = self._collection_problems.distinct('Weight')
        # print "levels=",levels
        i = 0
        self._problems = {}
        for k in weights:
            s = "Weight " + str(k) + "\n"
            s += "Level \t Character \t R1 \t R2 \t Date mber of Maass forms \n"
            s += "---------------------------------------------- \n"
            res[k] = {}
            levels = self._collection_problems.find({'Weight': k}).distinct('Level')
            for N in levels:
                res[k][N] = {}
                ch = self._collection_problems.find({'Level': N, 'Weight': k}).distinct('Character')
                for x in ch:
                    for prob in self._collection_problems.find({'Level': N, 'Weight': k, 'Character': x}):
                        self._problems[i] = x['_id']
                        i += 1
                        R1 = prob.get("R1", "")
                        R2 = prob.get("R2", "")
                        date = prob.get("date", "")
                        message = prob.get("Message", "")
                        s = "{0} \ t {1} \t {2} \t {3} \t {4} \t {5}".format(N, x, R1, R2, date, message)
                        level = x.get('Level', '')

                    res[k][N][x] = numr

            lN = res[k].keys()
            lN.sort()
            for N in lN:
                s += str(N) + "\t"
                lx = res[k][N].keys()
                lx.sort()
                for x in lx:
                    s += "\t " + str(x) + ":" + str(res[k][N][x])
                s += "\n"
            s += "=============================================== \n"
            print s

        # pri#nt N

    def show_eigenvalues(self, data={}, **kwds):
        verbose = kwds.get('verbose', 0)
        find_data = arg_to_search_parameters(data, **kwds)
        format_data = arg_to_format_parameters(data, **kwds)
        sorting = [('Weight', pymongo.ASCENDING), (
            'Level', pymongo.ASCENDING), ('Character', pymongo.ASCENDING), ('Eigenvalue', pymongo.ASCENDING)]
        s = self.display_header()
        if verbose > 0:
            print "find_data=", find_data
            print "format_data=", format_data
        finds = self._collection.find(
            find_data, sort=sorting).skip(format_data['skip']).limit(format_data['limit'])
        for f in finds:
            s += self.display_one_record(f, header=0)
        print s

    def display_header(self, date=0):
        if date == 1:
            s = "{0:^7}{1:^7}{2:^7}{3:^20}{4:^10}{5:^7}{6:^7}{7:^15}{8:^20}{9:^15} \n".format('Level', 'Weight', 'Char', 'R', 'Even/Odd', 'Dim', 'Error', 'Num. coeff.', 'Cusp symmetries', 'Date')
        else:
            s = "{0:^7}{1:^7}{2:^7}{3:^20}{4:^10}{5:^7}{6:^7}{7:^15}{8:^20} \n".format(
                'Level', 'Weight', 'Char', 'R', 'Even/Odd', 'Dim', 'Error', 'Num. coeff.', 'Cusp symmetries')
        return s

    def display_one_record(self, x, header=1, date=0):
        N = x.get('Level', 0)
        R = x.get('Eigenvalue', 0)
        k = x.get('Weight', 0)
        ch = x.get('Character', 0)
        st = x.get('Symmetry', -1)
        evs = x.get('Cusp_evs', [])
        err = x.get('Error', 0)
        nc = x.get('Numc', 0)
        dim = x.get('Dim', 0)
        rdate = x.get('date', '')
        sdate = str(rdate).split(".")[0]
        if header == 1:
            s = self.display_header(date=1)
        else:
            s = ""
        if date == 1:
            print "rdate=", rdate
            s += "{0:^7}{1:^7}{2:^7}{3:^20.15f}{4:^10}{5:^7}{6:^3.1e}{7:^15}{8:^20}{9} \n".format(
                N, k, ch, R, st, dim, err, nc, evs, sdate)
        else:
            s += "{0:^7}{1:^7}{2:^7}{3:^20.15f}{4:^10}{5:^7}{6:^3.1e}{7:^15}{8:^20}\n".format(
                N, k, ch, R, st, dim, err, nc, evs)
        return s

    def show_last(self):
        f = self._collection.find(sort=[('date', pymongo.DESCENDING)])
        x = f.next()
        print self.display_one_record(x, date=1)

    def put_problem_mongo(self, data):
        r"""
        Register a problem region where the algorithm
        could have gotten stuck and we need to look 'by hand'.
        """
        R1 = float(data.get('R1', 0))
        R2 = float(data.get('R2', 0))
        level = int(data.get('Level', 0))
        weight = int(data.get('Weight', 0))
        dim = int(data.get('Dim', 1))
        ch = int(data.get('Character', 0))
        sym_type = int(data.get('Symmetry', -1))
        Y = float(data.get('Y', 0))
        M0 = int(data.get("M0", 0))
        cn_evs = []
        err = data.get('Error', 0)
        for x in data.get("Cusp_evs", []):
            cn_evs.append((float(real(x)), float(imag(x))))

        message = str(data.get("message", ""))
        # Check if this record already exists
#        isin,numc0,errin,idd0 =  self.is_data_in_table_mongo(level,weight,ch,sym_type,R,err)
        # print "Is in database:",isin

        insert_data = {'Level': level, 'Weight': weight,
                       'Character': ch, 'Symmetry': sym_type,
                       'Error': err,
                       'Dim': dim,
                       'R1': R1, 'R2': R2, 'M0': M0, 'Y': Y,
                       'date': bson.datetime.datetime.utcnow(),
                       'Cusp_evs': cn_evs,
                       'Message': message
                       }
        mwf_logger.debug("inserting:", insert_data)
        idd = self._collection_problems.insert(insert_data)

    def sync_dbs(self, other, search={}, update=False, verbose=0):
        r"""
        Copy the data from self to other (of type MaassDB)
        """
        i = 0
        # # Get eigenvalues and
        maassids = self.find_Maass_form_id(search)
        # self.convert_db_to_Conrey()
        # other.convert_db_to_Conrey()
        for idd in maassids:
            if i > 2:
                return
            # Check if this record is already in other.
            data = {}
            xx = self.get_Maass_forms(idd)
            if len(xx) > 1:
                raise ValueError("Did not get a unique Maass form for this id:{0}".format(idd))
            x = xx[0]
            N = x.get('Level', 0)
            data['Level'] = N
            R = x.get('Eigenvalue', 0)
            Contributor = x.get('Contributor', '')
            k = x.get('Weight', 0)
            data['Weight'] = k
            ch = x.get('Character', 0)
            conrey = x.get('Conrey', 0)
            data['Character'] = ch

            st = x.get('Symmetry', -1)
            if not isinstance(st, int):
                if st == 'even':
                    st = 0
                elif st == 'odd':
                    st = 1
                else:
                    st = -1
            data['Symmetry'] = int(st)
            evs = x.get('Cusp_evs', [])
            err = x.get('Error', 0)
            nc = x.get('Numc', 0)
            dim = x.get('Dim', 0)
            M0 = x.get('M0', 0)
            Y = x.get('Y', 0)
            rdate = x.get('date', '')
            ep0 = max(1.0E-7, 2 * RR(err))
            # data['Eigenvalue'] = {"$gte": float(R)-float(ep0),
            #"$lt":float(R)+float(ep0)}
            # If
            if verbose > 0:
                print "Local data:", N, k, ch, st, R, err
            if math.isnan(R):
                print "x=", x
                continue
            find_data = copy(data)
            find_data['r1'] = float(R) - float(ep0)
            find_data['r2'] = float(R) + float(ep0)
            data['Eigenvalue'] = float(R)
            data['Error'] = err
            data['Numc'] = nc
            data['M0'] = M0
            data['Y'] = Y
            data['date'] = rdate
            data['Cusp_evs'] = evs
            data['Conrey'] = conrey
            data['Dim'] = dim
            data['_id'] = idd
            data['Contributor'] = Contr
            coeff_id = None
            f = None
            ff = other.find_Maass_form_id({'_id': idd})  # find_data)
            if len(ff) == 0:  # f.count()==0:
                if verbose > 1:
                    print "find_data=", find_data
                if verbose > 0:
                    print "Record did not exist in other db!"
                # key={'_id':idd}
                ins = other._collection.insert(data, upsert=True)
                if ins is not None and verbose > 0:
                    print "Insertion successful! rec:{0}".format(data)
                    # print "newrec=",other._collection.find_one(key)
                else:
                    # if other._collection.find(key).count()==0:
                    raise ArithmeticError(
                        "Insertion unsuccessful!\n key={0}, inserts={1}, ind:{2}".format(key, data, ins))
                        # print "Insertion unsuccessful! ins:{0}".format(ins)
                ncnew = 0
                idnew = ins
            else:  # See if it is still worth to update the record
                # f = ff[0]
                f = other.get_Maass_forms(ff[0])
                if len(f) == 0:
                    if verbose > 0:
                        print "Record did and did not exits? id={0}".format(ff[0])
                    continue
                f = f[0]
                if verbose > 0:
                    print "Record exist in other db!"
                    print "Remote data:{0},{1},{2},{3},{4},{5}".format(f.get('Level', 0), f.get('Weight', 0),
                                                                       f.get('Character',
                                                                             0), f.get('Symmetry', 0),
                                                                       f.get('Eigenvalue', 0), f.get('Error', 0))
                errf = f.get('Error', 1)
                idnew = f.get('_id')
                if err < errf or update:
                    data['_id'] = idnew
                    other._collection.insert(data)
                    dsets = {"Eigenvalue": float(R),
                             "Error": float(err),
                             "Cusp_evs": evs,
                             "dim": dim,
                             "Symmetry": st,
                             'M0': int(M0),
                             'Y': Y}
                    inserts = {"$set": dsets}
                    key = {"_id": idnew}
                    if verbose > 0:
                        print "Error in self is better than error in other!"
                        print "key:{0}".format(key)
                        print "inserts:{0}".format(inserts)
                    try:
                        ins = other._collection.update(key, inserts)
                    #                                                   upsert=True)
                    except:
                        # f = other._collection.find(key)
                        raise ArithmeticError(
                            "Update unsuccessful!\n key={0}, inserts={1}".format(key, inserts))

                    if verbose > 0:
                        print "Update successful!"
                ncnew = f.get("Numc", 0)
                coeff_id = f.get("coeff_id", None)
                if verbose > 0:
                    print "coeff_id:", coeff_id
            if nc > ncnew or not coeff_id:  # Update the coefficients
                if verbose > 0:
                    print "self has more Fourier coefficients!: id={0}".format(idd)
                C = self.get_coefficients({'_id': idd}, verbose=verbose)
                Rst = str(R).split(".")
                print "Rst=", Rst
                Rst = (Rst[0] + "." + Rst[1][0:12])[0:12]  # Shou
                fname = '{0}-{1}-{2}-{3}-{4}'.format(N, k, ch, st, Rst)
                if ff:
                    if len(ff) > 0:
                        f = other.get_Maass_forms(ff[0])[0]
                    if f:
                        k = f.get('Weight', k)
                        N = f.get('Level', N)
                        R = f.get('Eigenvalue', R)
                    #    #print "ff=",ff[0]
                #    f = other.get_Maass_forms(ff[0])[0]
                fs = gridfs.GridFS(other._mongo_db, 'Coefficients')
                fid = fs.put(dumps(C), filename='c-' + fname,
                             maass_id=idnew, level=N,
                             weight=k,
                             eigenvalue=R,
                             numc=int(nc))
                inserts = {"$set": {"Numc": int(nc), "coeff_id": fid}}
                key = {"_id": idnew}
                try:
                    other._collection.update(key,
                                             inserts, upsert=True)
                    if verbose > 0:
                        print "Insertion of coefficients successful!"
                except:
                    raise ArithmeticError("Update unsuccessful!\n key={0}, inserts={1}".format(key, inserts))

#### Setup a SQLDatabase.
## Default to this if we don't have a mongodb connection?
# DB=None


def setup_sqldb():
    table_skeleton = {
        'R': {'sql': 'REAL', 'index': True},
        'ch': {'sql': 'INTEGER', 'index': True},
        'level': {'sql': 'INTEGER', 'index': True, 'primary_key': False},
        'id': {'sql': 'INTEGER', 'index': True, 'primary_key': True},
        'file': {'sql': 'TEXT'}
    }

    if not DB:
        DB = SQLDatabase()  # filename="maasstable.db")
        DB.create_table('maass_forms', table_skeleton)
    DB.show('maass_forms')
    Q = SQLQuery(
        DB, {'table_name': 'maass_forms', 'display_cols': ['level'], 'expression': ['level', '=', 1]})


def get_Maass(N, R1, R2, verbose=0):
    G = MySubgroup(Gamma0(N))
    find_Maass_for_one_N(G, R1, R2, char='all', verbose=verbose, db=DB)
    DB.save("maasstable.db")


def mongify_dict(data, lowercase=False):
    r"""
    Make sure that data we have can be stored in a Mongo DB

    """
    if not isinstance(data, dict):
        return data
    res = {}
    for k in data.keys():
        if isinstance(k, (int, float, str, unicode)):
            if isinstance(k, str) and lowercase:
                key = k.lower()
            else:
                key = k
        elif isinstance(k, (Integer)):
            key = int(k)
        else:
            print "key=", k, type(k)
            key = k
        x = data[k]
        if isinstance(x, list):
            y = mongify_list(x)
        elif isinstance(x, dict):
            y = mongify_dict(x)
        else:
            y = mongify(x)
        res[key] = y
    return res


def mongify_list(data):
    res = []
    for x in data:
        if isinstance(x, list):
            y = mongify_list(x)
        elif isinstance(x, dict):
            y = mongify_dict(x)
        else:
            y = mongify(x)
        res.append(y)
    return res


def mongify(data):
    if isinstance(data, list):
        return mongify_list(data)
    if isinstance(data, dict):
        return mongify_dict(data)
    return mongify_elt(data)

import sage
from sage.rings.real_mpfr import RealLiteral
# from sage.rings.complex_number import ComplexNumber
try:
    from sage.rings.complex_mpc import MPComplexNumber
except:
    MPComplexNumber = None
    pass


def mongify_elt(x):
    if isinstance(x, (int, float, str, unicode, datetime.datetime, bson.objectid.ObjectId)):
        return x
    if isinstance(x, Integer):
        return int(x)
    if isinstance(x, (RealLiteral, sage.rings.real_mpfr.RealNumber, Expression)):
        return float(x)
    if isinstance(x, (complex, sage.rings.complex_number.ComplexNumber, Expression)):
        return float(real(x)), float(imag(x))
    elif isinstance(x, MPComplexNumber):
        return float(x.real()), float(x.imag())
    elif x is None:
        return x
    else:
        raise TypeError(
            "Could not coerce {0} to mongodb-compatible format. Consider using gridfs instead!".format(x))


def arg_to_format_parameters(data={}, **kwds):
    res = {}
    if not isinstance(data, dict):
        res['skip'] = 0
        res['limit'] = 3000
        res['collection_name'] = ''
    else:
        res['skip'] = int(data.get('skip', kwds.get('skip', 0)))
        res['limit'] = int(data.get('limit', kwds.get('limit', 50)))
        res['collection_name'] = data.get('collection_name', kwds.get('collection_name', ''))
    return res


def arg_to_search_parameters(data={}, **kwds):
    r"""
    Try to extract any search parameters we can think of.
    """
    if isinstance(data, (int, Integer)):
        data = {'Level': data}
    data = mongify_dict(data, True)
    kwds = mongify_dict(kwds, True)
    tol = data.get('tol', kwds.get('tol', 1e-6))
    R = data.get('eigenvalue', data.get('r', kwds.get('eigenvalue', kwds.get('r', None))))
    R1 = data.get('eigenvalue1', data.get('r1', kwds.get('eigenvalue1', kwds.get('r1', R))))
    R2 = data.get('eigenvalue2', data.get('r2', kwds.get('eigenvalue2', kwds.get('r2', R))))
    level = data.get('level', data.get('N', kwds.get('level', kwds.get('N', None))))
    level1 = data.get('l1', data.get('level1', kwds.get('l1', kwds.get('level1', None))))
    level2 = data.get('l2', data.get('level2', kwds.get('l2', kwds.get('level2', None))))
    ch = data.get('char', data.get('ch', kwds.get('char', kwds.get('ch', None))))
    ch1 = data.get('ch1', data.get('char1', kwds.get('ch1', kwds.get('char1', ch))))
    ch2 = data.get('ch2', data.get('char2', kwds.get('ch2', kwds.get('char2', ch))))
    wt = data.get('wt', data.get('weight', kwds.get('wt', kwds.get('weight', None))))
    wt1 = data.get('wt1', data.get('weight1', kwds.get('wt1', kwds.get('weight1', wt))))
    wt2 = data.get('wt2', data.get('weight2', kwds.get('wt2', kwds.get('weight2', wt))))
    dim = data.get('d', data.get('dim', kwds.get('d', kwds.get('dim', None))))
    d1 = data.get('d1', data.get('dim1', kwds.get('d1', kwds.get('dim1', dim))))
    d2 = data.get('d2', data.get('dim2', kwds.get('d2', kwds.get('dim2', dim))))
    numc = data.get('nc', data.get('numc', kwds.get('nc', kwds.get('numc', None))))
    nc1 = data.get('nc1', data.get('numc1', kwds.get('nc1', kwds.get('numc1', numc))))
    nc2 = data.get('nc2', data.get('numc2', kwds.get('nc2', kwds.get('numc2', numc))))
    newf = data.get('newform', data.get('newf', kwds.get('newform', kwds.get('newf', 'notset'))))  #Allow None

    idd = data.get('id', data.get('_id', kwds.get('id', kwds.get('_id', None))))
    if idd is not None:
        idd = bson.objectid.ObjectId(idd)
    find = {}
    if level is not None:
        find['Level'] = level
    elif level1 is not None or level2 is not None:
        if level1 is not None and level1 != '':
            level1 = int(level1)
            if 'Level' not in find:
                find['Level'] = {}
            find['Level']["$gte"] = level1
        if level2 is not None and level2 != '':
            level2 = int(level2)
            if 'Level' not in find:
                find['Level'] = {}
            find['Level']["$lte"] = level2
    if R1 is not None or R2 is not None:
        if R1 is not None and R1 != '':
            R1 = float(R1)
            find['Eigenvalue'] = {}
            find['Eigenvalue']["$gte"] = R1 - tol
        if R2 is not None and R2 != '':
            R2 = float(R2)
            if 'Eigenvalue' not in find:
                find['Eigenvalue'] = {}
            find['Eigenvalue']["$lte"] = R2 + tol
    if wt is not None:
        find['Weight'] = wt
    elif wt1 is not None or wt2 is not None:
        if wt1 is not None and wt1 != '':
            find['Weight'] = {}
            wt1 = float(wt1)
            find['Weight']["$gte"] = wt1
        if wt2 is not None and wt2 != '':
            if 'Weight' not in find:
                find['Weight'] = {}
            wt2 = float(wt2)
            find['Weight']["$lte"] = wt2
    if idd is not None:
        find['_id'] = idd

    if ch is not None:
        find['Character'] = ch
    elif ch1 is not None or ch2 is not None:
        if ch1 is not None:
            ch1 = int(ch1)
            find['Character'] = {}
            find['Character']["$gte"] = ch1
        if ch2 is not None:
            ch2 = int(ch2)
            if 'Character' not in find:
                find['Character'] = {}
            find['Character']["$lte"] = ch2

    if dim is not None:
        find['Dim'] = dim
    elif d1 is not None or d2 is not None:
        find['Dim'] = {}
        if d1 is not None and d1 != '':
            d1 = int(d1)
            find['Dim']["$gte"] = d1
        if d2 is not None and d2 != '':
            d2 = int(d2)
            find['Dim']["$lte"] = d2

    if numc is not None:
        find['Numc'] = numc
    elif nc1 is not None or nc2 is not None:
        find['Numc'] = {}
        if nc1 is not None:
            find['Numc']["$gte"] = nc1
        if nc2 is not None:
            find['Numc']["$lte"] = nc2

    if newf != 'notset':
        find['Newform'] = newf
        
    return find
