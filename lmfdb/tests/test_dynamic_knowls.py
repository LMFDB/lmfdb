
from lmfdb.tests import LmfdbTest

class DynamicKnowlTest(LmfdbTest):
    """
    These tests check the functioning of some dynamic knowls.
    """

    def test_Galois_group_knowl(self):
        L = self.tc.get('/knowledge/show/nf.galois_group.data?n=5&t=5', follow_redirects=True)
        assert 'Prime degree' in L.get_data(as_text=True)

    def test_conjugacy_classes_knowl(self):
        L = self.tc.get('/knowledge/show/gg.conjugacy_classes.data?n=5&t=5', follow_redirects=True)
        assert '1,3,4,5' in L.get_data(as_text=True)

    def test_character_table_knowl(self):
        L = self.tc.get('/knowledge/show/gg.character_table.data?n=5&t=5', follow_redirects=True)
        # character values now complicated text in mathml, so look for labels
        assert '120.34.5a' in L.get_data(as_text=True)
        assert '5A' in L.get_data(as_text=True)

    def test_abstract_group_knowl(self):
        L = self.tc.get('/knowledge/show/lmfdb.object_information?func=group_data&args=16.5', follow_redirects=True)
        assert '11 subgroups' in L.get_data(as_text=True)

    def test_number_field_knowl(self):
        L = self.tc.get('/knowledge/show/nf.field.data?label=6.0.21296.1', follow_redirects=True)
        assert '-21296' in L.get_data(as_text=True)

    def test_local_field_knowl(self):
        L = self.tc.get('/knowledge/show/lf.field.data?label=2.2.3.4', follow_redirects=True)
        assert 'Residue field degree' in L.get_data(as_text=True)

    def test_galois_module_knowl(self):
        L = self.tc.get('/knowledge/show/nf.galois_group.gmodule?ind=3&n=6&t=2', follow_redirects=True)
        assert 'Action' in L.get_data(as_text=True)

    def test_galois_alias_knowl(self):
        L = self.tc.get('/knowledge/show/nf.galois_group.name', follow_redirects=True)
        assert '11T6' in L.get_data(as_text=True)

    def test_prod_knowl_sync(self):
        # This test checks that the script at https://github.com/edgarcosta/lmfdb-gce/blob/master/server_scripts/update_knowls_and_userdb.sh is successully syncing the knowl databases on beta.lmfdb.org and www.lmfdb.org
        # It will be run as part of the CI for PRs against dev or prod.

        from lmfdb import db
        if db.config.postgresql_options["host"] == "proddb.lmfdb.xyz":
            # Create a different connection to devmirror to compare timestamps
            from lmfdb.utils.config import Configuration
            from psycopg2.sql import SQL
            from datetime import timedelta, datetime
            dev_config = Configuration()
            # Modify configuration to connect to devmirror
            for D in [dev_config.default_args["postgresql"], dev_config.postgresql_options, dev_config.options["postgresql"]]:
                D["host"] = "devmirror.lmfdb.xyz"
                D["port"] = 5432
                D["dbname"] = "lmfdb"
                D["user"] = "lmfdb"
                D["password"] = "lmfdb"
            from psycodict.database import PostgresDatabase
            dev_db = PostgresDatabase(dev_config)

            # Updates happen every 20 minutes, so we only compare knowls older than that (plus a buffer).
            cutoff = datetime.utcnow() - timedelta(minutes=30)

            t_query = SQL("SELECT timestamp FROM kwl_knowls WHERE timestamp < %s LIMIT 1")
            dev_t = dev_db._execute(t_query, [cutoff]).fetchone()[0]
            prod_t = db._execute(t_query, [cutoff]).fetchone()[0]

            cnt_query = SQL("SELECT COUNT(*) FROM kwl_knowls WHERE timestamp < %s")
            dev_cnt = dev_db._execute(cnt_query, [cutoff]).fetchone()[0]
            prod_cnt = db._execute(cnt_query, [cutoff]).fetchone()[0]

            # The timestamps and counts should be the same
            assert dev_cnt == prod_cnt and dev_t == prod_t
