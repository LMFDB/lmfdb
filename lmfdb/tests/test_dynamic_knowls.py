
from unittest.mock import patch

from lmfdb.tests import LmfdbTest
from lmfdb.knowledge.knowl import Knowl, knowldb
from lmfdb.utils.datetime_utils import utc_now_naive

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
            from lmfdb.utils.psycopg_compat import SQL
            from datetime import timedelta
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
            cutoff = utc_now_naive() - timedelta(minutes=30)

            t_query = SQL("SELECT timestamp FROM kwl_knowls WHERE timestamp < %s LIMIT 1")
            dev_t = dev_db._execute(t_query, [cutoff]).fetchone()[0]
            prod_t = db._execute(t_query, [cutoff]).fetchone()[0]

            cnt_query = SQL("SELECT COUNT(*) FROM kwl_knowls WHERE timestamp < %s")
            dev_cnt = dev_db._execute(cnt_query, [cutoff]).fetchone()[0]
            prod_cnt = db._execute(cnt_query, [cutoff]).fetchone()[0]

            # The timestamps and counts should be the same
            assert dev_cnt == prod_cnt and dev_t == prod_t


class PortColumnKnowlsTest(LmfdbTest):
    """
    These tests check that db.<table>.port_column_knowls moves the column
    description knowls of another table onto this one.
    """

    def _port(self, other_table, cols, keep_old=True):
        r"""
        Run db.nf_fields.port_column_knowls with the database writes mocked
        out, and return the knowls it would have saved, renamed and deleted.
        """
        old_knowls = {col: Knowl(f"columns.{other_table}.{col}",
                                 data={"content": f"The {col} column",
                                       "authors": ["editor"], "status": 0})
                      for col in cols}
        saved, renamed, deleted = [], [], []

        def fake_save(knowl, who, most_recent=None, minor=False):
            saved.append((knowl, who, most_recent, minor))

        def fake_rename(knowl, new_name=None):
            renamed.append((knowl, new_name))

        with patch.object(knowldb, "get_column_descriptions", return_value=old_knowls), \
             patch.object(knowldb, "save", side_effect=fake_save), \
             patch.object(knowldb, "actually_rename", side_effect=fake_rename), \
             patch.object(knowldb, "delete", side_effect=deleted.append), \
             patch.object(self.db, "login", return_value="tester"):
            self.db.nf_fields.port_column_knowls(other_table, keep_old=keep_old)

        return saved, renamed, deleted

    def test_descriptions_of_the_other_table_are_requested(self):
        with patch.object(knowldb, "get_column_descriptions", return_value={}) as get_descriptions:
            self.db.nf_fields.port_column_knowls("old_nf_fields")
        get_descriptions.assert_called_once_with("old_nf_fields")

    def test_copies_knowls_of_shared_columns(self):
        saved, renamed, deleted = self._port("old_nf_fields", ["degree", "not_a_column"])

        # only a column that this table actually has is ported
        assert len(saved) == 1
        knowl, who, most_recent, minor = saved[0]
        assert knowl.id == "columns.nf_fields.degree"
        assert knowl.content == "The degree column"
        assert knowl.title == "Column degree of table nf_fields"
        # the old knowl is passed along so that its authors are carried over
        assert most_recent.id == "columns.old_nf_fields.degree"
        assert (who, minor) == ("tester", True)
        # keep_old leaves the knowls of the other table in place
        assert renamed == [] and deleted == []

    def test_renames_knowls_when_not_keeping_old(self):
        saved, renamed, deleted = self._port("old_nf_fields", ["degree", "not_a_column"],
                                             keep_old=False)

        assert saved == []
        assert len(renamed) == 1
        knowl, new_name = renamed[0]
        assert knowl.id == "columns.old_nf_fields.degree"
        assert new_name == "columns.nf_fields.degree"
        # a knowl for a column this table does not have is dropped
        assert [k.id for k in deleted] == ["columns.old_nf_fields.not_a_column"]
