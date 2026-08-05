
import re
from datetime import timedelta
from unittest.mock import patch

from lmfdb.tests import LmfdbTest
from lmfdb.knowledge.knowl import Knowl, knowldb, description_metadata, make_keywords
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


NOW = utc_now_naive()
OLDER = NOW - timedelta(days=2)
NEWER = NOW - timedelta(days=1)
KNOWL_COLUMNS = ["id"] + knowldb._default_fields + ["_keywords"]


def query_text(query):
    """
    The text of a composed query, whichever psycopg psycodict is built on.
    """
    try:
        return query.as_string()  # psycopg3
    except TypeError:
        return query.as_string(knowldb.conn)  # psycopg2 wants a connection


def description_row(kid, content, timestamp, status=0, authors=None, links=None):
    """
    A row of kwl_knowls holding one version of a table or column description,
    with the metadata that knowldb.save would have stored alongside it.
    """
    meta = description_metadata(kid)
    return {"id": kid,
            "authors": ["editor"] if authors is None else authors,
            "cat": meta["cat"],
            "content": content,
            "last_author": "editor",
            "timestamp": timestamp,
            "title": meta["title"],
            "status": status,
            "type": meta["type"],
            "links": links or [],
            "defines": meta["defines"],
            "source": meta["source"],
            "source_name": meta["source_name"],
            "_keywords": make_keywords(content, kid, meta["title"])}


def normal_row(kid, content, timestamp, links=None):
    """
    A row of kwl_knowls holding a normal knowl, used to check that references
    to a renamed description follow it.
    """
    return {"id": kid, "authors": ["editor"], "cat": kid.split(".")[0],
            "content": content, "last_author": "editor", "timestamp": timestamp,
            "title": kid, "status": 0, "type": 0, "links": links or [],
            "defines": [], "source": None, "source_name": None,
            "_keywords": make_keywords(content, kid, kid)}


class FakeKnowlTable:
    """
    Enough of the kwl_knowls table to run port_column_knowls in memory.

    The database the tests connect to is read only, so a description with
    several versions cannot be created there.  This stands in for
    KnowlBackend._execute instead, holding the rows in a list.

    Selects are answered using the ordering of the query they are given rather
    than an assumed one, so a query asking for the version a description was
    created with gets that version.
    """

    def __init__(self, rows):
        self.rows = [dict(row) for row in rows]
        # the depth of the surrounding transaction at each write
        self.write_depths = []

    def execute(self, query, values=None, **kwds):
        sql = query_text(query)
        values = list(values) if values else []
        if sql.startswith("SELECT"):
            return self.select(sql, values)
        self.write_depths.append(knowldb._db._nocommit_stack)
        if sql.startswith("INSERT INTO kwl_knowls"):
            self.rows.append(dict(zip(KNOWL_COLUMNS, values)))
            return []
        if sql.startswith("UPDATE kwl_knowls"):
            return self.update(sql, values)
        raise AssertionError("unexpected query: %s" % sql)

    def select(self, sql, values):
        if sql.startswith("SELECT 1 FROM kwl_knowls WHERE id = %s"):
            return [(1,) for row in self.rows if row["id"] == values[0]][:1]
        if sql.startswith("SELECT id, timestamp, content, title FROM kwl_knowls WHERE id = ANY(%s)"):
            return [(row["id"], row["timestamp"], row["content"], row["title"])
                    for row in self.rows if row["id"] in values[0]]
        if "links @> %s" in sql:  # ids_referencing
            status, typ, links = values
            return sorted({(row["id"],) for row in self.rows
                           if row["status"] >= status and row["type"] != typ
                           and all(link in row["links"] for link in links)})
        if "id LIKE %s AND type = %s AND status >= %s" in sql:  # get_column_descriptions
            pattern, typ, status = values
            matches = [row for row in self.rows if row["id"].startswith(pattern[:-1])
                       and row["type"] == typ and row["status"] >= status]
        elif "id = %s AND type = %s AND status >= %s" in sql:  # get_table_description
            kid, typ, status = values
            matches = [row for row in self.rows if row["id"] == kid
                       and row["type"] == typ and row["status"] >= status]
        else:
            raise AssertionError("unexpected query: %s" % sql)
        # DISTINCT ON keeps the first row for each id in the order asked for
        matches.sort(key=lambda row: (row["id"], row["timestamp"]),
                     reverse="ORDER BY id, timestamp DESC" in sql)
        chosen = {}
        for row in matches:
            chosen.setdefault(row["id"], row)
        fields = [field.strip('"') for field in re.match(r"SELECT (.*?) FROM", sql).group(1).split(", ")]
        return [tuple(row[field] for field in fields)
                for row in sorted(chosen.values(), key=lambda row: row["id"])]

    def update(self, sql, values):
        if "SET (id, cat, type, source, source_name, title, defines)" in sql:
            new_id, cat, typ, source, source_name, title, defines, old_id = values
            for row in self.rows:
                if row["id"] == old_id:
                    row.update(id=new_id, cat=cat, type=typ, source=source,
                               source_name=source_name, title=title, defines=defines)
        elif "SET _keywords = %s WHERE id = %s AND timestamp = %s" in sql:
            keywords, kid, timestamp = values
            for row in self.rows:
                if row["id"] == kid and row["timestamp"] == timestamp:
                    row["_keywords"] = keywords
        elif "SET (content, links) = (regexp_replace" in sql:
            pattern, replacement, _, old_id, new_id, ids = values
            for row in self.rows:
                if row["id"] in ids:
                    row["content"] = re.sub(pattern, replacement, row["content"])
                    row["links"] = [new_id if link == old_id else link for link in row["links"]]
        elif "SET status=%s WHERE id=%s" in sql:
            status, kid = values
            for row in self.rows:
                if row["id"] == kid:
                    row["status"] = status
        else:
            raise AssertionError("unexpected query: %s" % sql)
        return []


class PortColumnKnowlsTest(LmfdbTest):
    """
    These tests check that db.<table>.port_column_knowls moves the column
    description knowls of another table onto this one.
    """

    def port(self, rows, keep_old=True, other_table="old_nf_fields"):
        r"""
        Run db.nf_fields.port_column_knowls against an in-memory kwl_knowls
        holding ``rows``, and return the table it acted on.
        """
        table = FakeKnowlTable(rows)
        with patch.object(knowldb, "_execute", side_effect=table.execute), \
             patch.object(self.db, "login", return_value="tester"):
            self.db.nf_fields.port_column_knowls(other_table, keep_old=keep_old)
        return table

    def test_descriptions_of_the_other_table_are_requested(self):
        with patch.object(knowldb, "get_column_descriptions", return_value={}) as get_descriptions:
            self.db.nf_fields.port_column_knowls("old_nf_fields")
        get_descriptions.assert_called_once_with("old_nf_fields")

    def test_current_version_of_a_column_description_is_read(self):
        # Every version of a knowl is kept, so selecting the description of a
        # column has to say which one it wants.
        table = FakeKnowlTable([
            description_row("columns.old_nf_fields.degree", "The first draft", OLDER),
            description_row("columns.old_nf_fields.degree", "The current text", NEWER)])
        with patch.object(knowldb, "_execute", side_effect=table.execute):
            knowls = knowldb.get_column_descriptions("old_nf_fields")

        assert list(knowls) == ["degree"]
        assert knowls["degree"].content == "The current text"

    def test_current_version_of_a_table_description_is_read(self):
        table = FakeKnowlTable([
            description_row("tables.old_nf_fields", "The first draft", OLDER),
            description_row("tables.old_nf_fields", "The current text", NEWER)])
        with patch.object(knowldb, "_execute", side_effect=table.execute):
            knowl = knowldb.get_table_description("old_nf_fields")

        assert knowl.content == "The current text"

    def test_copies_current_descriptions_of_shared_columns(self):
        table = self.port([
            description_row("columns.old_nf_fields.degree", "The first draft", OLDER),
            description_row("columns.old_nf_fields.degree", "The current text", NEWER),
            description_row("columns.old_nf_fields.not_a_column", "Not a column here", NEWER)])

        # only a column that nf_fields actually has is ported, and keep_old
        # leaves the knowls of the other table exactly as they were
        new = [row for row in table.rows if row["id"].startswith("columns.nf_fields.")]
        assert len(table.rows) == 4 and len(new) == 1
        row = new[0]
        assert row["id"] == "columns.nf_fields.degree"
        assert row["content"] == "The current text"
        assert row["title"] == "Column degree of table nf_fields"
        assert row["cat"] == "columns" and row["type"] == 2
        assert row["source"] == "nf_fields" and row["source_name"] == "degree"
        assert row["defines"] == ["degree"]
        # the authors of the old knowl are carried over, and the person running
        # the port is recorded only as the last author (minor=True)
        assert row["authors"] == ["editor"] and row["last_author"] == "tester"
        assert "nf_fields" in row["_keywords"] and "old_nf_fields" not in row["_keywords"]

    def test_renames_shared_columns_when_not_keeping_old(self):
        table = self.port([
            description_row("columns.old_nf_fields.degree", "The reviewed text", OLDER, status=1),
            description_row("columns.old_nf_fields.degree", "The current text", NEWER),
            description_row("columns.old_nf_fields.not_a_column", "Not a column here", NEWER),
            normal_row("nf.degree", "See {{KNOWL('columns.old_nf_fields.degree')}}", NEWER,
                       links=["columns.old_nf_fields.degree"])],
            keep_old=False)

        # the history is moved rather than copied or trimmed
        degree = [row for row in table.rows if row["id"] == "columns.nf_fields.degree"]
        assert len(table.rows) == 4 and len(degree) == 2
        assert sorted(row["content"] for row in degree) == ["The current text", "The reviewed text"]
        assert sorted(row["status"] for row in degree) == [0, 1]
        assert sorted(row["timestamp"] for row in degree) == [OLDER, NEWER]
        for row in degree:
            # every version describes the column of its new table
            assert row["title"] == "Column degree of table nf_fields"
            assert row["cat"] == "columns" and row["type"] == 2
            assert row["source"] == "nf_fields" and row["source_name"] == "degree"
            assert row["defines"] == ["degree"]
            # and is found by searching for the new table, not the old one
            assert "nf_fields" in row["_keywords"] and "old_nf_fields" not in row["_keywords"]

        # the edit page describes the column of the new table (see the title
        # built for type 2 knowls in lmfdb.knowledge.main.edit)
        knowl = Knowl("columns.nf_fields.degree", data=degree[0])
        assert knowl.title == degree[0]["title"]
        assert (f"Edit column information for '{knowl.source_name}' in '{knowl.source}'"
                == "Edit column information for 'degree' in 'nf_fields'")

        # a knowl for a column this table does not have is deleted
        dropped = [row for row in table.rows if row["id"] == "columns.old_nf_fields.not_a_column"]
        assert [row["status"] for row in dropped] == [-2]

        # knowls referring to the old id follow it, and are reindexed
        referring = [row for row in table.rows if row["id"] == "nf.degree"][0]
        assert referring["content"] == "See {{KNOWL('columns.nf_fields.degree')}}"
        assert referring["links"] == ["columns.nf_fields.degree"]
        assert referring["_keywords"] == make_keywords(referring["content"], referring["id"],
                                                       referring["title"])

    def test_a_reference_to_a_renamed_description_is_reindexed(self):
        # knowl search matches against the keywords, so rewriting a reference
        # has to rewrite the keywords of the knowl holding it
        table = self.port([
            description_row("columns.oldtable.degree", "The degree of the field", NEWER),
            normal_row("nf.degree", "See {{KNOWL('columns.oldtable.degree')}}", NEWER,
                       links=["columns.oldtable.degree"])],
            keep_old=False, other_table="oldtable")

        referring = [row for row in table.rows if row["id"] == "nf.degree"][0]
        assert referring["content"] == "See {{KNOWL('columns.nf_fields.degree')}}"
        assert referring["links"] == ["columns.nf_fields.degree"]
        assert referring["_keywords"] == make_keywords(referring["content"], referring["id"],
                                                       referring["title"])
        assert "oldtable" not in referring["_keywords"]

    def test_a_description_referring_to_itself_is_reindexed(self):
        # the keywords have to be redone after the content is rewritten, not before
        table = self.port([
            description_row("columns.oldtable.degree", "See {{KNOWL('columns.oldtable.degree')}}",
                            NEWER, links=["columns.oldtable.degree"])],
            keep_old=False, other_table="oldtable")

        row = [row for row in table.rows if row["id"] == "columns.nf_fields.degree"][0]
        assert row["content"] == "See {{KNOWL('columns.nf_fields.degree')}}"
        assert row["links"] == ["columns.nf_fields.degree"]
        assert row["_keywords"] == make_keywords(row["content"], row["id"], row["title"])
        assert "oldtable" not in row["_keywords"]

    def test_a_description_referring_to_another_is_reindexed(self):
        # class_number is ported first, so the reference in it is rewritten
        # after it has already been moved and indexed
        table = self.port([
            description_row("columns.oldtable.class_number",
                            "Divides {{KNOWL('columns.oldtable.degree')}}", NEWER,
                            links=["columns.oldtable.degree"]),
            description_row("columns.oldtable.degree", "The degree of the field", NEWER)],
            keep_old=False, other_table="oldtable")

        row = [row for row in table.rows if row["id"] == "columns.nf_fields.class_number"][0]
        assert row["content"] == "Divides {{KNOWL('columns.nf_fields.degree')}}"
        assert row["links"] == ["columns.nf_fields.degree"]
        assert row["_keywords"] == make_keywords(row["content"], row["id"], row["title"])
        assert "oldtable" not in row["_keywords"]

    def test_a_rename_will_not_merge_two_histories(self):
        # nf_fields already describes r2, so moving the other table's
        # description onto it would interleave two sets of versions.
        table = FakeKnowlTable([
            description_row("columns.old_nf_fields.degree", "The degree text", NEWER),
            description_row("columns.old_nf_fields.r2", "The other r2 text", NEWER),
            description_row("columns.nf_fields.r2", "The r2 text", NEWER)])
        with self.assertRaises(ValueError), \
             patch.object(knowldb, "_execute", side_effect=table.execute), \
             patch.object(self.db, "login", return_value="tester"):
            self.db.nf_fields.port_column_knowls("old_nf_fields", keep_old=False)

        # degree was moved before the failure, but every write was made inside
        # the transaction that port_column_knowls then rolls back
        assert table.write_depths and all(depth > 0 for depth in table.write_depths)

    def test_descriptions_are_not_renamed_as_normal_knowls(self):
        # actually_rename leaves the metadata of a description inconsistent
        knowl = Knowl("columns.old_nf_fields.degree",
                      data=description_row("columns.old_nf_fields.degree", "The degree text", NEWER))
        with self.assertRaises(ValueError):
            knowldb.actually_rename(knowl, "columns.nf_fields.degree")

    def test_stored_title_matches_the_displayed_one(self):
        # rename_description_knowl stores the title that Knowl computes for display
        for kid in ["columns.nf_fields.degree", "tables.nf_fields"]:
            assert description_metadata(kid)["title"] == Knowl(kid, data={}).title
