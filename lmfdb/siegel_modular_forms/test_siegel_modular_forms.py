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

    def test_space_search_aldims(self):
        """
        The Atkin-Lehner dimensions of the new subspace, in the sign-vector
        order of the space page: in S_{3,0}^new(K(161)), of dimension 17, the
        classes (w_7, w_23) = (+,+), (+,-), (-,+), (-,-) have dimensions
        0, 11, 6, 0, of which 0, 3, 1, 0 are of general type (the old
        Saito-Kurokawa lifts are not counted).  The space page puts each
        dimension under its signs.
        """
        self.need_spaces("2.K.161.3.0.a")
        self.check("?search_type=Spaces&degree=2&family=K&level=161&weight=3", [
            "AL-dims.",
            r"\(0\)+\(11\)+\(6\)+\(0\)",
        ])
        self.check("2/K/161/3.0/a/", [
            r"\(+\) \(-\) $-$ \(11\) \(3\)",
            r"\(-\) \(+\) $-$ \(6\) \(1\)",
            r"Minus space \(-\) \(17\) \(4\)",
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
        self.check("download_traces/2.P.2.2.12.a.a", "[0, 1, null, -600, null, -53460")
        self.check("download_newform/2.P.2.2.12.a.a", [
            "Stored data for newform 2.P.2.2.12.a.a",
            '"analytic_rank_proved"',
        ])
        self.need_spaces("2.K.568.3.0.a")
        self.check("download_newspace/2.K.568.3.0.a", [
            "Stored data for newspace 2.K.568.3.0.a",
            '"ALdims"',
        ])

    def test_fourier_coefficients(self):
        """
        Fourier coefficients of paramodular newforms of levels 31 (weight 4) and 101 (weight 3,
        dimension 9), on the newform page and in the Sage download
        """
        self.need_forms("2.K.101.3.0.a.b")
        if not db.smf_qexp_coeffs.exists({"hecke_orbit_code": db.smf_newforms.lookup("2.K.101.3.0.a.b", "hecke_orbit_code")}):
            self.skipTest("Fourier coefficients of 2.K.101.3.0.a.b not loaded on devmirror")
        self.check("2/K/31/4.0/a/a/", ["Fourier coefficients", "[1, -11, 31]", "Fourier coefficients to Sage"])
        self.check("2/K/101/3.0/a/b/", r"20 + 5 \beta_{1} - 2 \beta_{2} - 7 \beta_{3}")
        self.check("download_qexp/2.K.101.3.0.a.b", [
            "fourier_data = [[[1, -20, 101], [20, 5, -2, -7, 5, 4, -3, 2, -2]]",
            "a(T') = (alpha delta - beta gamma)^k a(T), here with k = 3",
        ])
        # an orbit whose Fourier coefficients cannot generate the coefficient ring: they are
        # written in the basis 1, gamma of the larger order O'
        self.need_forms("2.K.69.3.0.a.b")
        self.check("2/K/69/3.0/a/b/", [r"contains \(\mathcal{O}\) with index \(2\)", r"\frac{1}{2} + \frac{1}{2} \beta", r"1 - \gamma"])
        # an orbit whose Fourier coefficients generate a non-principal ideal of O'
        self.need_forms("2.K.109.3.0.a.b")
        self.check("2/K/109/3.0/a/b/", [r"not a principal ideal", r"\([\mathcal{O}' : J] = 8\)"])
        self.check("download_qexp/2.K.109.3.0.a.b", ["least index [O' : J] = 8", "ideal_data = "])

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
                   "[0, 1, 2784, 107352, 4441088, 80234700")

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
        # newform dimensions (there are no scalar-valued forms of odd weight below 35)
        self.check("?search_type=Dimensions&degree=2&family=S&level=1&weight=6-20", [
            "The dimensions shown below are for the space of newforms",
            "(10, 0) 2 (11, 0) 0 (12, 0) 3",
            "(16, 0) 4 (17, 0) 0 (18, 0) 4 (19, 0) 0 (20, 0) 5",
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

    def test_weight2_yoshida_scaling(self):
        """
        The Yoshida lifts of weight k = 2 store p T_{p^2,0} and p T_{p^2,1},
        and the eigenvalue table labels those rows accordingly; other forms
        are unchanged
        """
        self.need_forms("2.P.2.2.12.a.a")
        self.check("2/P/2/2.12/a/a/", [
            "p T_{ p^2, 0 }",
            "p T_{ p^2, 1 }",
            "T_{ p^2, 2 }",
            "so the table gives those of",
        ])
        self.need_forms("2.P.2.3.6.a.a")
        data = self.check("2/P/2/3.6/a/a/", "T_{ p^2, 0 }")
        assert "so the table gives those of" not in data and "p T_{" not in data

    def test_coefficient_ring(self):
        """
        The coefficient ring is shown as Z[lambda_1, ..., lambda_n], n the
        hecke_ring_generator_nbound of the form
        """
        self.need_forms("2.K.992.3.0.a.t")
        self.check("2/K/992/3.0/a/t/", r"\Z[\lambda_1, \ldots, \lambda_{9}]")
        data = self.check("2/K/992/3.0/a/t/", "Coefficient ring")
        assert r"\Z[a_1" not in data

    def test_saito_kurokawa_lfunction(self):
        r"""
        A Saito-Kurokawa lift F of weight k of a classical newform f (of
        weight 2k-2) has no L-function row of its own; its page states
        L(F,s) = L(f,s) zeta(s-k+2) zeta(s-k+1) and links to L(f,s) and zeta.
        2.K.13.3.0.a.a lifts 13.4.a.a, and 2.S.1.18.0.a.c lifts 1.34.a.a.
        """
        self.need_forms("2.K.13.3.0.a.a")
        self.check("2/K/13/3.0/a/a/", [
            "Saito-Kurokawa lift",
            '<a href="/ModularForm/GL2/Q/holomorphic/13/4/a/a/">13.4.a.a</a>',
            r"L(F,s) = L(f,s)\,\zeta(s-1)\,\zeta(s-2)",
            '<a href="/L/Riemann/">',
        ])
        if db.lfunc_instances.exists({'url': 'ModularForm/GL2/Q/holomorphic/13/4/a/a'}):
            self.check("2/K/13/3.0/a/a/", '<a href="/L/ModularForm/GL2/Q/holomorphic/13/4/a/a/">')
        self.need_forms("2.S.1.18.0.a.c")
        self.check("2/S/1/18.0/a/c/", [
            '<a href="/ModularForm/GL2/Q/holomorphic/1/34/a/a/">1.34.a.a</a>',
            r"L(F,s) = L(f,s)\,\zeta(s-16)\,\zeta(s-17)",
        ])
        # a form of general type gets no such factorization
        self.need_forms("2.K.277.3.0.a.a")
        data = self.check("2/K/277/3.0/a/a/", "General type (G)")
        assert "spinor \\(L\\)-function factors" not in data

    def test_lfunction_link(self):
        """
        A newform with a row in lfunc_instances links to its L-function,
        and the L-function page names the Siegel modular form as its origin.
        Skipped until the SMF L-functions are loaded.
        """
        inst = db.lfunc_instances.lucky({'type': 'SMF'}, ['url', 'label'])
        if inst is None:
            self.skipTest("no SMF rows in lfunc_instances")
        url, label = inst['url'], inst['label']
        smf_label = '.'.join(url.split('/')[3:])
        self.check(url[len('ModularForm/GSp/Q/'):] + '/', [
            'L-function ',
            'href="/L/%s/"' % url,
        ])
        page = self.tc.get('/L/%s/' % url, follow_redirects=True).get_data(as_text=True)
        assert label in page
        assert 'Siegel modular form ' + smf_label in page

    # ------------------------------------------------------------------
    # Consistency of the stored data.  These read the tables directly,
    # with small projections, so that they stay fast on devmirror.
    # ------------------------------------------------------------------

    def test_hecke_ring_basis_starts_with_one(self):
        """
        The first element of every stored basis of a Hecke ring is 1:
        the pages print the first coordinate of an eigenvalue as its
        constant term
        """
        if not db.smf_hecke_nf.count():
            self.skipTest("smf_hecke_nf not yet loaded on devmirror")
        bad = []
        for r in db.smf_hecke_nf.search(
                {"hecke_ring_numerators": {"$exists": True}},
                ["label", "field_poly", "hecke_ring_numerators", "hecke_ring_denominators"]):
            d = len(r["field_poly"]) - 1
            if (list(r["hecke_ring_numerators"][0]) != [1] + [0] * (d - 1)
                    or r["hecke_ring_denominators"][0] != 1):
                bad.append(r["label"])
        assert not bad, "Hecke ring basis does not start with 1: %s" % bad[:10]

    def test_eisenstein_traces(self):
        """
        The Siegel Eisenstein series of weight k (type F) has spin
        coefficient 1 + p^{k-2} + p^{k-1} + p^{2k-3} at every prime p not
        dividing the level, including the level-2 series; at level 2 and
        weight 4 the page shows the coefficients of the stored traces
        """
        self.need_forms()
        bad = []
        n = 0
        for r in db.smf_newforms.search({"aut_rep_type": "F"}, ["label", "level", "weight", "traces"]):
            k = r["weight"][0]
            for p in [3, 5, 7, 11, 13, 17, 19, 23, 29, 31]:
                if r["level"] % p == 0:
                    continue
                n += 1
                if r["traces"][p - 1] != 1 + p**(k - 2) + p**(k - 1) + p**(2 * k - 3):
                    bad.append((r["label"], p))
        assert n > 0 and not bad, "wrong Eisenstein traces: %s" % bad[:10]
        self.need_forms("2.P.2.4.0.a.a")
        self.check("2/P/2/4.0/a/a/", [
            "Siegel-Eisenstein (F)",
            # 1 + 3^2 + 3^3 + 3^5 = 280, 1 + 5^2 + 5^3 + 5^5 = 3276
            "1 + 45 * 2^{-s} + 280 * 3^{-s}",
            "3276 * 5^{-s}",
        ])

    def test_traces_match_eigenvalues(self):
        """
        At a prime p not dividing the level, the trace of the spin
        coefficient a_p is the trace of lambda_p
        """
        self.need_forms()
        bad = []
        n = 0
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        for r in db.smf_newforms.search(
                {"level": {"$lte": 40}, "trace_lambda_p": {"$exists": True}},
                ["label", "level", "traces", "trace_lambda_p"]):
            tr, tl = r.get("traces"), r["trace_lambda_p"]
            if not tr:
                continue
            for i, p in enumerate(primes):
                if i >= len(tl) or p > len(tr) or tl[i] is None or tr[p - 1] is None:
                    continue
                n += 1
                if tr[p - 1] != tl[i]:
                    bad.append((r["label"], p))
        assert n > 0 and not bad, "traces differ from trace_lambda_p: %s" % bad[:10]

    def test_saito_kurokawa_atkin_lehner(self):
        """
        A paramodular Saito-Kurokawa lift has the Atkin-Lehner signs of the
        elliptic newform it lifts, as stored in mf_newforms
        """
        self.need_forms()
        lifts = {}
        for r in db.smf_newforms.search(
                {"family": "K", "aut_rep_type": "P", "level": {"$lte": 100}},
                ["label", "atkin_lehner_eigenvals", "related_objects"]):
            cmf = [x for x in (r.get("related_objects") or []) if x.startswith("ModularForm/GL2/Q/holomorphic/")]
            if len(cmf) == 1 and r.get("atkin_lehner_eigenvals"):
                lifts[".".join(cmf[0].strip("/").split("/")[-4:])] = r
        if not lifts:
            self.skipTest("no paramodular Saito-Kurokawa lifts on devmirror")
        sources = {f["label"]: dict(f["atkin_lehner_eigenvals"])
                   for f in db.mf_newforms.search({"label": {"$in": list(lifts)}},
                                                  ["label", "atkin_lehner_eigenvals"])
                   if f.get("atkin_lehner_eigenvals")}
        bad = []
        for lab, r in lifts.items():
            if lab not in sources:
                continue
            for p, e in r["atkin_lehner_eigenvals"]:
                if sources[lab].get(p) != e:
                    bad.append((r["label"], lab, p))
        assert sources and not bad, "Atkin-Lehner signs differ from the lifted form: %s" % bad[:10]

    def test_level2_paramodular_saito_kurokawa(self):
        """
        The Saito-Kurokawa lift 2.K.2.8.0.a.a of the newform in
        S_{14}(Gamma_0(2)): its spin coefficient at 3 is
        a_3(f) + 3^6 + 3^7 = -1836 + 729 + 2187 = 1080, and the coefficients
        at the bad prime 2 are not known
        """
        self.need_spaces("2.K.2.8.0.a")
        self.check("2/K/2/8.0/a/", [
            "S_{8,0}^{\\mathrm{new}}(K(2))",
            "Saito-Kurokawa lifts (P) 1 0 1",
            "2.K.2.8.0.a.a",
        ])
        self.need_forms("2.K.2.8.0.a.a")
        self.check("2/K/2/8.0/a/a/", [
            "Saito-Kurokawa Lift (P)",
            "1 + ? * 2^{-s} + 1080 * 3^{-s}",
            "97740 * 5^{-s}",
        ])
