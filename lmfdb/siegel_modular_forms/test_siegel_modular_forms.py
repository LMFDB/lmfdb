"""
Tests for the rewritten Siegel modular forms pages (smf_* tables).

The data on devmirror is provisional and only partially loaded, so tests
that depend on database content use runtime skip guards rather than
failing when a table or label has not been loaded yet.

Recovered content from the pre-rewrite tests
--------------------------------------------
The old test_siegel_modular_forms.py exercised the smf_samples-based pages
(families Sp4Z, Sp4Z_2, Sp4Z_j, Gamma0_N, Kp, Sp6Z, Sp8Z).  Wherever the
same mathematical object exists in the new smf_* tables, its assertions
have been ported below with values re-verified against the database and
against the classical formulas (see test_igusa_cusp_forms,
test_eisenstein_series, test_klingen_eisenstein, test_maass_spezialschar,
test_paramodular_277, test_sp4z_dimension_tables, test_gamma0_2_dimensions).
The old Sp4Z scalar dimension table (Igusa's numbers) and the old
M_{k,2}(Gamma_0(2)) table agree exactly with the new smf_newspaces data.

Content of the old tests that is NOT recoverable on the new pages
(re-add if/when the data or features return):
 * Sample pages driven by db.smf_samples (129 samples: Sp4Z 97, Sp4Z_2 12,
   Sp8Z 10, Sp6Z 2, Kp 8).  The rewrite has no sample routes; smf_samples,
   smf_ev and smf_fc still exist on devmirror but are unused by the code.
 * Sp4Z.24_E (weight 24 Siegel Eisenstein): eigenvalue 35184384671745
   (= 1 + 2^22 + 2^23 + 2^45), the ev_index=19/fc_det UI, Fourier
   coefficients such as (0, 0, 25), and mod-p reduction (1000000007 ->
   384425457).  Scalar level-1 data now stops at weight 20; the same
   eigenvalue formula is asserted at weight 12 in test_eisenstein_series.
 * Sp4Z.18_Maass eigenvalue "-144a + 135840" (= 135768 - b with
   b = 72*sqrt(2356201)): the newform 2.S.1.18.0.a.c exists (its defining
   polynomial x^2 - x - 589050 is asserted below), but smf_hecke_nf stores
   its lambda_2 as 135768 + 196607*b, i.e. the Eisenstein summand
   2^16 + 2^17 = 196608 was added to BOTH coordinates instead of only the
   rational one, so the displayed eigenvalue disagrees with the classical
   value and is not asserted.  Its Fourier coefficients ("10a - 8340",
   dets (1,1,1), (2,2,2)) and the modulus-reduction UI are also gone.
 * Sp4Z.56_Ups ("interesting cusp form", "6085 bytes", "7912968 bytes"):
   no weight-56 data.
 * Kp weight-2 Poor--Yuen samples 2_PY2_{277,349,353,389,461,523,587+-}:
   the new paramodular (K) data starts at weight (3, 0).
 * Sp6Z (Miyawaki lifts, "Miyawaki (1)") and Sp8Z (Ikeda/Miyawaki lifts,
   "Other_II (2)"): no degree > 2 data in smf_newforms/smf_newspaces.
 * Old dimension-table families with no new counterpart: Gamma1_2 (no
   Gamma_1(N) family), Gamma0_4 (dim M_20 = 192), Gamma0_4_psi_4
   (dim M_40 = 495) and Gamma0_4_half (non-cusp 129 at k = 20): level 4,
   characters and half-integral weight are absent; Gamma0_3_psi_3
   (dim M_19 = 68): no nontrivial character orbits at level 3.
 * Gamma0_3 totals (e.g. dim M_20(Gamma_0(3)) = 74): the new
   2.S.3.20.0.a space has total_dim 71; the new tables are smaller by
   exactly 3 at every even weight (Eisenstein series beyond the F/Q types
   are not counted), so the old numbers are not asserted.
 * Gamma_2 tables decomposed by Sp(4,F_2) = S_6 irreps (columns 111111,
   3111, ...): the new principal-family (P) level-2 dimensions come from a
   different construction (total_dim in the tens of thousands) and do not
   match dim M_{k,j}(Gamma(2)); nothing asserted.
Additionally, the deleted lmfdb/siegel_modular_forms/test_smf.py was a
byte-identical stray copy (commit c0fdb6f551, Aug 2022) of
classical_modular_forms/test_cmf.py; all of its GL(2) assertions live on
in lmfdb/classical_modular_forms/, so nothing Siegel was lost with it.
"""

import re

from lmfdb.tests import LmfdbTest
from lmfdb import db


class SmfTest(LmfdbTest):
    def check(self, url, text):
        data = self.tc.get("/ModularForm/GSp/Q/" + url, follow_redirects=True).get_data(as_text=True)
        # Match against both the raw page (for links) and a tag-stripped
        # version (for text that is interrupted by knowl links or line breaks)
        html = re.sub(r"\s+", " ", data)
        stripped = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", data))
        if not isinstance(text, list):
            text = [text]
        for t in text:
            t = re.sub(r"\s+", " ", t)
            assert t in html or t in stripped, (
                "expected string '%s' not found in page /ModularForm/GSp/Q/%s"
                % (t, url)
            )
        return data

    def need_forms(self, label=None):
        if not db.smf_newforms.count():
            self.skipTest("smf_newforms not yet loaded on devmirror")
        if label is not None and not db.smf_newforms.label_exists(label):
            self.skipTest("%s not in smf_newforms on devmirror" % label)

    def need_spaces(self, label=None):
        if not db.smf_newspaces.count():
            self.skipTest("smf_newspaces not yet loaded on devmirror")
        if label is not None and not db.smf_newspaces.label_exists(label):
            self.skipTest("%s not in smf_newspaces on devmirror" % label)

    def test_browse_page(self):
        r"""
        Check the top-level browse page for Siegel modular forms
        """
        self.need_forms()
        self.check("", [
            "Siegel modular forms",
            "The database currently contains",
            "Browse newforms",
            "Browse newspaces",
            "By weight",
            "By level",
            "Some interesting newforms",
            "random newform",
            "paramodular",
            "/ModularForm/GSp/Q/stats",
            "provisional",
        ])

    def test_random_page(self):
        """
        Test 3 random newform pages
        """
        self.need_forms()
        for _ in range(3):
            self.check("random/", ["Newform orbit", "Newspace parameters", "Automorphic type"])

    def test_random_space(self):
        """
        Test a random newspace page
        """
        self.need_spaces()
        self.check("random_space/", "Space of Siegel modular forms")

    def test_newform_pages(self):
        """
        Test some specific newform pages, including scalar and vector-valued
        weights, all three families, and dimension larger than 1
        """
        # Siegel family (Sp(4,Z)), scalar weight 12
        self.need_forms("2.S.1.12.0.a.a")
        self.check("2/S/1/12.0/a/a/", [
            "Newform orbit 2.S.1.12.0.a.a",
            "Newspace parameters",
            "Newform invariants",
            "(12, 0)",
        ])
        # principal family, vector-valued weight (2,12), Yoshida lift
        self.need_forms("2.P.2.2.12.a.a")
        self.check("2/P/2/2.12/a/a/", [
            "Newform orbit 2.P.2.2.12.a.a",
            "principal",
            "(2, 12)",
            "Automorphic type",
            "Dirichlet series",
            "53460",  # coefficient of 5^{-s} in the spin L-series
        ])
        # paramodular family
        self.need_forms("2.K.568.3.0.a.c")
        self.check("2/K/568/3.0/a/c/", [
            "Newform orbit 2.K.568.3.0.a.c",
            "paramodular",
            "568 = 2^{3} \\cdot 71",
            "General type (G)",
        ])
        # dimension 2 form
        self.need_forms("2.K.1.4.20.a.a")
        self.check("2/K/1/4.20/a/a/", ["Newform orbit 2.K.1.4.20.a.a", "Dimension"])
        # vector-valued Siegel family form
        self.need_forms("2.S.1.4.8.a.a")
        self.check("2/S/1/4.8/a/a/", "Newform orbit 2.S.1.4.8.a.a")

    def test_space_pages(self):
        """
        Test newspace pages, including the dimension and decomposition tables
        """
        self.need_spaces("2.K.568.3.0.a")
        self.check("2/K/568/3.0/a/", [
            "Space of Siegel modular forms of level 568 and weight (3, 0)",
            "Defining parameters",
            "Cusp forms",
            "Saito-Kurokawa lifts (P)",
            "General type (G)",
            "Atkin-Lehner",
            "newform subspaces",
            "2.K.568.3.0.a.a",
        ])
        self.need_spaces("2.S.1.12.0.a")
        self.check("2/S/1/12.0/a/", [
            "Space of Siegel modular forms of level 1 and weight (12, 0)",
            "M_{12,0}",
        ])

    def test_dimension_tables(self):
        """
        Test the dimension tables for newforms and for spaces
        """
        self.need_forms()
        self.need_spaces()
        self.check("?search_type=Dimensions&degree=2&family=K", [
            "Dimension search results",
            "The dimensions shown below are for the space of newforms",
            "n/a",
        ])
        self.check("?search_type=Dimensions&degree=2&family=K&weight=3&level=1-24", [
            "Dimension search results",
            "(3, 0)",
        ])
        self.check("?search_type=SpaceDimensions&degree=2&family=K", [
            "Dimension search results",
            "The dimensions shown are for spaces of modular forms",
            "All modular forms",
            "New cusp forms",
            "Old Eisenstein series",
        ])

    def test_newform_search(self):
        """
        Test the newform search results
        """
        self.need_forms("2.K.568.3.0.a.c")
        self.check("?search_type=List&family=K&weight=3&level=568", [
            "Siegel newform search results",
            "Results (",
            "2.K.568.3.0.a.c",
        ])
        self.check("2/", ["Siegel newform search results", "Results ("])
        self.check("2/K/", ["Siegel newform search results", "Results ("])

    def test_space_search(self):
        """
        Test the newspace search results
        """
        self.need_spaces()
        self.check("?search_type=Spaces&degree=2&family=K&level=1-100", [
            "Newspace search results",
            "Results (",
            "2.K.",
        ])

    def test_trace_search(self):
        """
        Test the trace search results
        """
        self.need_forms()
        self.check("?search_type=Traces&degree=2&family=K&level=1-20", [
            "search results",
            "Results (",
        ])

    def test_stats(self):
        """
        Test the statistics page
        """
        self.need_forms()
        self.check("stats", [
            "Siegel modular forms: Statistics",
            "Distribution of levels and absolute dimension",
            "newforms",
        ])

    def test_dynamic_stats(self):
        """
        Test the dynamic statistics page
        """
        self.need_forms()
        self.check(
            "dynamic_stats?col1=level&buckets1=1-100%2C101-999&proportions=recurse"
            "&col2=dim&buckets2=1-4%2C5-1000&search_type=DynStats",
            "Dynamic statistics",
        )

    def test_jump(self):
        """
        Test the jump box, including error messages
        """
        self.need_forms("2.S.1.12.0.a.a")
        self.check("?jump=2.S.1.12.0.a.a", "Newform orbit 2.S.1.12.0.a.a")
        self.check("?jump=2.K.568.3.0.a", "Space of Siegel modular forms of level 568")
        self.check("?jump=maria", "is not a valid newform or space label")

    def test_not_found(self):
        """
        Check that missing labels and invalid families give proper errors
        """
        self.check("?jump=2.K.9999.3.0.a.z", "Newform 2.K.9999.3.0.a.z not found")
        self.check("2/K/9999/3.0/a/", "Space 2.K.9999.3.0.a not found")
        page = self.tc.get("/ModularForm/GSp/Q/2/X/", follow_redirects=True)
        assert page.status_code == 404

    def test_downloads(self):
        """
        Test the download links that appear on newform and newspace pages
        """
        self.need_forms("2.P.2.2.12.a.a")
        self.check("download_traces/2.P.2.2.12.a.a", "[0, 1, 0, -600, -4, -53460")
        self.check("download_newform/2.P.2.2.12.a.a", [
            "Stored data for newform 2.P.2.2.12.a.a",
            '"analytic_rank_proved"',
        ])
        self.need_spaces("2.K.568.3.0.a")
        self.check("download_newspace/2.K.568.3.0.a", [
            "Stored data for newspace 2.K.568.3.0.a",
            '"ALdims"',
        ])

    def test_underlying_data(self):
        """
        Test the underlying data pages
        """
        self.need_forms("2.P.2.2.12.a.a")
        self.check("data/2.P.2.2.12.a.a", [
            "Newform data - 2.P.2.2.12.a.a",
            "smf_newforms",
            "smf_hecke_nf",
        ])
        self.need_spaces("2.K.568.3.0.a")
        self.check("data/2.K.568.3.0.a", [
            "Newspace data - 2.K.568.3.0.a",
            "smf_newspaces",
        ])

    def test_interesting(self):
        """
        Test the interesting newforms and newspaces pages
        """
        self.check("interesting_newforms", "Some interesting newforms")
        self.check("interesting_spaces", "Some interesting newspaces")

    def test_sidebar(self):
        """
        Test the learn-more pages
        """
        self.check("Completeness", "Completeness of Siegel modular form data")
        self.check("Source", "Source of Siegel modular form data")
        self.check("Reliability", "Reliability of Siegel modular form data")
        self.check("Labels", "Labels for Siegel modular forms")

    # ------------------------------------------------------------------
    # Mathematical content recovered from the pre-rewrite sample pages
    # (see the module docstring for the items that could not be ported).
    # All eigenvalues below were re-verified against classical formulas:
    # for a Saito-Kurokawa lift of f in S_{2k-2}(1) the spin coefficient
    # is a_p(f) + p^{k-2} + p^{k-1}, for the Klingen-Eisenstein series of
    # f in S_{k+j}(1) it is a_p(f)(1 + p^{k-2}), and for the weight-k
    # Siegel Eisenstein series it is 1 + p^{k-2} + p^{k-1} + p^{2k-3}.
    # ------------------------------------------------------------------

    def test_igusa_cusp_forms(self):
        """
        The Igusa cusp forms chi_10 and chi_12 (the weight-10 and weight-12
        cusp forms for Sp(4,Z)), which are Saito-Kurokawa lifts of the
        elliptic newforms 1.18.a.a and 1.22.a.a
        """
        self.need_forms("2.S.1.10.0.a.b")
        self.check("2/S/1/10.0/a/b/", [
            "Newform orbit 2.S.1.10.0.a.b",
            "Saito-Kurokawa Lift (P)",
            # lambda_2 = -528 + 2^8 + 2^9, lambda_3 = -4284 + 3^8 + 3^9,
            # lambda_5 = -1025850 + 5^8 + 5^9
            "1 + 240 * 2^{-s} + 21960 * 3^{-s}",
            "1317900 * 5^{-s}",
            "Modular form 1.18.a.a",
        ])
        self.need_forms("2.S.1.12.0.a.c")
        self.check("2/S/1/12.0/a/c/", [
            "Newform orbit 2.S.1.12.0.a.c",
            "Saito-Kurokawa Lift (P)",
            # lambda_2 = -288 + 2^10 + 2^11, lambda_3 = -128844 + 3^10 + 3^11,
            # lambda_5 = 21640950 + 5^10 + 5^11
            "1 + 2784 * 2^{-s} + 107352 * 3^{-s}",
            "80234700 * 5^{-s}",
            "Modular form 1.22.a.a",
        ])
        self.check("download_traces/2.S.1.12.0.a.c",
                   "[0, 1, 2784, 107352, -1778648202240, 80234700")

    def test_eisenstein_series(self):
        """
        The Siegel Eisenstein series of weight 12 for Sp(4,Z).  This ports
        the old Sp4Z.24_E eigenvalue test (weight 24 is not in the new
        data): the eigenvalue formula 1 + p^{k-2} + p^{k-1} + p^{2k-3} gave
        35184384671745 for k=24, p=2 and gives 2100225 for k=12, p=2.
        """
        self.need_forms("2.S.1.12.0.a.a")
        self.check("2/S/1/12.0/a/a/", [
            "Newform orbit 2.S.1.12.0.a.a",
            "Siegel-Eisenstein (F)",
            # 1 + 2^10 + 2^11 + 2^21 and 1 + 3^10 + 3^11 + 3^21
            "1 + 2100225 * 2^{-s} + 10460589400 * 3^{-s}",
            "476837216796876 * 5^{-s}",
        ])

    def test_klingen_eisenstein(self):
        """
        Klingen-Eisenstein series in the vector-valued spaces M_{10,2} and
        M_{10,10} for Sp(4,Z), attached to the elliptic newforms 1.12.a.a
        (Delta) and 1.20.a.a; this recovers the old Sp4Z_2/Sp4Z_j browse
        pages with sharper content
        """
        self.need_forms("2.S.1.10.2.a.a")
        self.check("2/S/1/10.2/a/a/", [
            "Newform orbit 2.S.1.10.2.a.a",
            "Klingen-Eisenstein (Q)",
            # tau(2)(1 + 2^8) = -6168, tau(3)(1 + 3^8) = 1653624
            "1 - 6168 * 2^{-s} + 1653624 * 3^{-s}",
            "Modular form 1.12.a.a",
        ])
        self.need_forms("2.S.1.10.10.a.a")
        self.check("2/S/1/10.10/a/a/", [
            "Newform orbit 2.S.1.10.10.a.a",
            "Klingen-Eisenstein (Q)",
            # a_2(1.20.a.a)(1 + 2^8) = 456*257, a_3(1.20.a.a)(1 + 3^8) = 50652*6562
            "1 + 117192 * 2^{-s} + 332378424 * 3^{-s}",
            "Modular form 1.20.a.a",
        ])

    def test_maass_spezialschar(self):
        """
        The old Sp4Z.18_Maass sample: the weight-18 Maass spezialschar
        (Saito-Kurokawa) eigenform with coefficient field
        Q[x]/(x^2 - x - 589050), the lift of the elliptic newform 1.34.a.a.
        (Its stored Hecke eigenvalues are not asserted; see the module
        docstring.)
        """
        self.need_forms("2.S.1.18.0.a.c")
        self.check("2/S/1/18.0/a/c/", [
            "Newform orbit 2.S.1.18.0.a.c",
            "(18, 0)",
            "Saito-Kurokawa Lift (P)",
            "x^{2} - x - 589050",
            "Modular form 1.34.a.a",
        ])

    def test_paramodular_277(self):
        """
        Weight-3 paramodular forms of level 277 (the level emphasized on
        the old Kp browse page): dim S_3(K(277)) = 56 = 33 (Saito-Kurokawa)
        + 23 (general type), with Atkin-Lehner/Fricke split 1/55, and the
        rational general-type eigenform 2.K.277.3.0.a.a
        """
        self.need_spaces("2.K.277.3.0.a")
        self.check("2/K/277/3.0/a/", [
            "S_{3,0}(K(277))",
            "Cusp forms 56 0 56",
            "Saito-Kurokawa lifts (P) 33 0 33",
            "General type (G) 23 0 23",
            r"\(+\) \(1\) \(1\) \(-\) \(55\) \(22\)",
            "2.K.277.3.0.a.a",
        ])
        self.need_forms("2.K.277.3.0.a.a")
        self.check("2/K/277/3.0/a/a/", [
            "Newform orbit 2.K.277.3.0.a.a",
            "General type (G)",
            "1 - 5 * 2^{-s} - 10 * 3^{-s} + 7 * 4^{-s}",
        ])

    def test_sp4z_dimension_tables(self):
        """
        Numeric dimension tables for scalar-valued Siegel modular forms of
        level 1 (Igusa's classical dimensions, as served by the old Sp4Z
        dimension table): dim M_k(Sp(4,Z)) for k = 4..20 is
        1,0,1,0,1,0,2,0,3,0,2,0,4,0,4,0,5 and the newform dimensions
        include dim S_10 = dim S_12 = 1
        """
        self.need_spaces("2.S.1.12.0.a")
        self.need_forms("2.S.1.12.0.a.a")
        # space dimensions (full spaces M_{k,0}(Sp(4,Z)))
        self.check("?search_type=SpaceDimensions&degree=2&family=S&level=1&weight=1-20", [
            "The dimensions shown are for spaces of modular forms",
            "(4, 0) 1 (5, 0) 0 (6, 0) 1 (7, 0) 0 (8, 0) 1 (9, 0) 0 (10, 0) 2 (11, 0) 0 (12, 0) 3",
            "(14, 0) 2 (15, 0) 0 (16, 0) 4 (17, 0) 0 (18, 0) 4 (19, 0) 0 (20, 0) 5",
        ])
        # newform dimensions (including the odd-weight Saito-Kurokawa forms)
        self.check("?search_type=Dimensions&degree=2&family=S&level=1&weight=6-20", [
            "The dimensions shown below are for the space of newforms",
            "(10, 0) 2 (11, 0) 1 (12, 0) 3",
            "(16, 0) 4 (17, 0) 2 (18, 0) 4 (19, 0) 3 (20, 0) 5",
        ])
        # the weight-12 space page: 3 = Eisenstein (F) + Klingen (Q) + Maass (P),
        # with the eigenvalue columns of the decomposition table
        self.check("2/S/1/12.0/a/", [
            "M_{12,0}",
            "2.S.1.12.0.a.a", "2.S.1.12.0.a.b", "2.S.1.12.0.a.c",
            "2100225",  # Siegel Eisenstein lambda_2
            "-24600",   # Klingen-Eisenstein lambda_2 = tau(2)(1 + 2^10)
            "2784",     # chi_12 lambda_2
        ])
        self.check("2/S/1/10.0/a/", [
            "M_{10,0}",
            "131841",   # Siegel Eisenstein lambda_2 = 1 + 2^8 + 2^9 + 2^17
            "240",      # chi_10 lambda_2
        ])
        # old browse pages Sp4Z_2/10/ and Sp4Z_j/10/10/
        self.need_spaces("2.S.1.10.2.a")
        self.check("2/S/1/10.2/a/", "M_{10,2}")
        self.need_spaces("2.S.1.10.10.a")
        self.check("2/S/1/10.10/a/", "M_{10,10}")

    def test_paramodular_dimension_table(self):
        """
        Weight-3 paramodular newform dimensions around level 277
        """
        self.need_spaces("2.K.277.3.0.a")
        self.check("?search_type=Dimensions&degree=2&family=K&weight=3&level=270-280", [
            "Level 270 271 272 273 274 275 276 277 278 279 280",
            "(3, 0) 16 48 19 31 33 30 14 56 25 29 19",
        ])

    def test_gamma0_2_dimensions(self):
        """
        The old Gamma0_2 dimension table M_{k,2}(Gamma_0(2)): the new
        smf_newspaces dimensions agree with the classical generating
        function exactly (e.g. dim S_{14,2}(Gamma_0(2)) = 16)
        """
        self.need_spaces("2.S.2.14.2.a")
        self.check("2/S/2/14.2/a/", [
            "S_{14,2}(\\Gamma_0(2))",
            "Cusp forms 16 0 16",
        ])
