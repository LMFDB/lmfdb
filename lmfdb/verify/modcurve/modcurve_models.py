"""
    To run this test, do, from the top level of the LMFDB directory:

        sage -python lmfdb/verify/verify_tables.py logs modcurve_models slow

"""

from sage.all import lazy_attribute, Curve, ProjectiveSpace, QQ, magma
from lmfdb.lmfdb_database import db
from lmfdb.modular_curves.upload import VARORDER
import json
from ..verification import TableChecker, slow


def canonical_model_num_pts_modulo_p(plane_model_eqn_list, canonical_model_eqn_list, canonical_model_num_vars, p):
    """
    Calculates the number of points on a curve defined by equations over GF(p) using Magma.

    Args:
        canonical_model_eqn_list: A list of strings, where each string is an
                                  equation defining the curve (using Python string format).
        canonical_model_num_vars: The number of variables used in the equations.
        p: The prime modulus for the finite field GF(p).

    Returns:
        An integer representing the number of rational points on the curve
        defined by the equations over GF(p).

    Raises:
        RuntimeError: If the Magma interface is not available or if magma.eval fails.
        ValueError: If the result from Magma cannot be converted to an integer.
    """

    # 2. Convert Python lists to Magma list-of-strings format
    # *** No replacement needed for plane_model_eqn_list ***
    magma_plane_eqn_list_str = json.dumps(plane_model_eqn_list)
    magma_canonical_eqn_list_str = json.dumps(canonical_model_eqn_list)


    # 3. Construct the full Magma script string (Magma script remains the same)
    magma_script = f"""
        // Set up variables and parameters
        VARORDER := "{VARORDER}";
        canonical_model_num_vars := {canonical_model_num_vars};
        input_from_sage_plane := {magma_plane_eqn_list_str};
        input_from_sage_canonical := {magma_canonical_eqn_list_str};
        p := {p};

        // ========== Process Canonical Model ==========

        // Define the projective space
        W_canonical := ProjectiveSpace(Rationals(), canonical_model_num_vars - 1);
        // Select and assign variable names
        names_canonical := [VARORDER[j] : j in [1..canonical_model_num_vars]];
        AssignNames(~W_canonical, names_canonical);
        // Get the coordinate variables into a list
        W_vars_canonical := [W_canonical.i : i in [1..canonical_model_num_vars]];
        // Create mapping from name character -> string like "W_vars_canonical[1]"
        localDict_canonical := AssociativeArray(names_canonical);
        for i->name in names_canonical do
            localDict_canonical[name] := Sprintf("W_vars_canonical[%o]", i);
        end for;
        // Manually build new equation strings with substitutions
        newEqnList_canonical := [];
        for eqn in input_from_sage_canonical do
            newEqn := "";
            for i in [1..#eqn] do
                if eqn[i] in names_canonical then
                    newEqn cat:= localDict_canonical[eqn[i]];
                else
                    newEqn cat:= eqn[i];
                end if;
            end for;
            Append(~newEqnList_canonical, newEqn);
        end for;
        // Evaluate the newly constructed strings to get Magma polynomial objects
        finalEqns_canonical := [eval(x) : x in newEqnList_canonical];
        // Define the curve using the evaluated equations
        C_canonical := Curve(W_canonical, finalEqns_canonical);
        // Change ring and count points
        Cp_canonical := ChangeRing(C_canonical, GF(p));
        canonical_ans := #RationalPoints(Cp_canonical);

        // ========== Process Plane Model ==========

        // Define the projective plane (P^2)
        W_plane := ProjectiveSpace(Rationals(), 2); // Dim = 3 - 1 = 2
        // Select and assign variable names (x, y, z)
        names_plane := [VARORDER[j] : j in [1..3]];
        AssignNames(~W_plane, names_plane);
        // Get the coordinate variables into a list
        W_vars_plane := [W_plane.i : i in [1..3]];
        // Create mapping from name character -> string like "W_vars_plane[1]"
        localDict_plane := AssociativeArray(names_plane);
        for i->name in names_plane do
            localDict_plane[name] := Sprintf("W_vars_plane[%o]", i);
        end for;
        // Manually build new equation strings with substitutions
        newEqnList_plane := [];
        for eqn in input_from_sage_plane do // Use the original plane equations input
            newEqn := "";
            for i in [1..#eqn] do
                // Check against plane var names ('x', 'y', 'z')
                if eqn[i] in names_plane then
                    newEqn cat:= localDict_plane[eqn[i]];
                else
                    // Keep the original character (including '^')
                    newEqn cat:= eqn[i];
                end if;
            end for;
            Append(~newEqnList_plane, newEqn);
        end for;
        // Evaluate the newly constructed strings to get Magma polynomial objects
        // Magma's eval should understand '^' here.
        finalEqns_plane := [eval(x) : x in newEqnList_plane];
        // Define the curve using the evaluated equations
        C_plane := Curve(W_plane, finalEqns_plane);
        // Change ring and count points
        Cp_plane := ChangeRing(C_plane, GF(p));
        plane_ans := #RationalPoints(Cp_plane);

        // ========== Compare Results ==========
        result := (plane_ans eq canonical_ans);

        // Print the boolean result ("true" or "false")
        print result;
    """

    # 4. Execute the script using magma.eval()
    try:
        magma_output = magma.eval(magma_script, verbose=False)
    except Exception as e:
        print("--- Magma Script ---")
        print(magma_script)
        print("--- End Magma Script ---")
        raise RuntimeError(f"Magma execution failed: {e}") from e

    # 5. Parse the boolean result string
    try:
        result_str = magma_output.strip().lower()
        print(result_str)
        if result_str == 'true':
            result = True
        elif result_str == 'false':
            result = False
        else:
            raise ValueError(f"Unexpected output from Magma: '{magma_output}'")
    except Exception as e:
        print(f"Failed to parse Magma boolean output: '{magma_output}'")
        raise ValueError(f"Could not convert Magma output to boolean: {e}") from e

    return result


def check_point_counts_match(plane_model_eqn_list, canonical_model_eqn_list, canonical_model_num_vars):
    """
    Check that the point counts of the plane model and canonical model match
    at several primes of good reduction.
    """

    ans = canonical_model_num_pts_modulo_p(plane_model_eqn_list, canonical_model_eqn_list, canonical_model_num_vars, 7)
    print ("done a bunch of magma")
    return ans


class modcurve_models(TableChecker):
    table = db.modcurve_models

    # The following column isn't the label column, but it's the
    # closest one we have to it. This gets used for reporting
    # on failed tests.
    label_col = 'equation'

    @lazy_attribute
    def plane_models(self):
        return {rec["modcurve"]: rec for rec in db.modcurve_models.search({"model_type":2}, ['equation', 'modcurve', 'model_type', 'number_variables'])}

    # @slow(ratio=1, projection=['equation', 'modcurve', 'model_type'], constraint={"model_type":0})
    @slow(ratio=1, projection=['equation', 'modcurve', 'model_type', 'number_variables'], constraint={"model_type":0, "modcurve": '9.324.10.b.1'})
    def check_point_counts(self, rec):
        modcurve = rec["modcurve"]
        if modcurve in self.plane_models:
            # in this case the modular curve has both plane and canonical models
            # and we need to check that the point counts match
            plane_model_eqn = self.plane_models[modcurve]['equation']
            assert self.plane_models[modcurve]['number_variables'] == 3, "Plane model should have 3 variables"
            canonical_model_eqn = rec["equation"]
            canonical_model_num_vars = rec["number_variables"]
            return check_point_counts_match(plane_model_eqn, canonical_model_eqn, canonical_model_num_vars)
        else:
            # in this case the modular curve doesn't have
            # both plane and canonical models, so we don't need to check anything
            return True


### MWE: Ignore below this

# VARORDER = "xyzwtuvrsabcdefghiklmnopqj"
# canonical_model_num_vars = 10
# canonical_model_eqn_list = ['z*u+z*v-r*a', 'x*z-z*w-r*s', 'y*r-y*s-u*a', 'x*z+z*t+r*s+s^2', '2*z*u-z*v+s*a', 'x*z+z*w-z*t+r^2+r*s', 'x*a-t*a+v*r-v*s', 'w*a-t*a+u*s+v*r', 'x*a-u*r-u*s+v*r', 'x*a+u*r+v*s', 'x*y-y*t+u*v', 'x*u-y^2+t*v', 'x*r+z^2-w*s', 'y*a-w*s-t*r', 'x*y+y*w-u*v+v^2', '2*y*r+y*s-v*a', 'x*y-y*w+y*t+u^2-u*v', 'x*s+z^2-t*r-t*s', 'z*a+w*u-t*v', 'x*v+y^2+w*u-w*v', 'x*t+y*u+z*s', 'x*w+y*v-z*r', 'x^2+y*u-z*r-w*t', 'x*u-x*v+y^2+w*u-t*u', 'x*r+x*s-z^2-w*r+t*r', 'x^2+x*t+y*v+w*t-t^2', 'x^2+x*w+z*s-w^2+w*t', '3*y*z-a^2']
# relevant_vars = VARORDER[:canonical_model_num_vars]
# W = ProjectiveSpace(QQ, canonical_model_num_vars - 1, names=tuple([x for x in relevant_vars]))
# W_vars = W._first_ngens(canonical_model_num_vars)


# # Make the variables accessible to eval
# local_dict = dict(zip(relevant_vars, W_vars))

# canonical_model_eqn_list = [eval(one_eqn.replace('^','**'), {}, local_dict) for one_eqn in canonical_model_eqn_list]
# canonical_model = Curve(canonical_model_eqn_list, W)

# VARORDER := "xyzwtuvrsabcdefghiklmnopqj";
# canonical_model_num_vars := 10;
# input_from_sage := ["z*u+z*v-r*a", "x*z-z*w-r*s", "y*r-y*s-u*a", "x*z+z*t+r*s+s^2", "2*z*u-z*v+s*a", "x*z+z*w-z*t+r^2+r*s", "x*a-t*a+v*r-v*s", "w*a-t*a+u*s+v*r", "x*a-u*r-u*s+v*r", "x*a+u*r+v*s", "x*y-y*t+u*v", "x*u-y^2+t*v", "x*r+z^2-w*s", "y*a-w*s-t*r", "x*y+y*w-u*v+v^2", "2*y*r+y*s-v*a", "x*y-y*w+y*t+u^2-u*v", "x*s+z^2-t*r-t*s", "z*a+w*u-t*v", "x*v+y^2+w*u-w*v", "x*t+y*u+z*s", "x*w+y*v-z*r", "x^2+y*u-z*r-w*t", "x*u-x*v+y^2+w*u-t*u", "x*r+x*s-z^2-w*r+t*r", "x^2+x*t+y*v+w*t-t^2", "x^2+x*w+z*s-w^2+w*t", "3*y*z-a^2"];

# W := ProjectiveSpace(Rationals(), canonical_model_num_vars-1);
# names := [VARORDER[j] : j in [1..canonical_model_num_vars]];
# AssignNames(~W, names);
# W_vars := [W.i : i in [1..canonical_model_num_vars]];
# localDict := AssociativeArray(names);

# for i->name in names do
#     localDict[name] := Sprintf("W_vars[%o]", i);
# end for;

# newEqnList := [];
# for eqn in input_from_sage do
#     newEqn := "";
#     for i in [1..#eqn] do
#         if eqn[i] in names then
#             newEqn cat:= localDict[eqn[i]];
#         else
#             newEqn cat:= eqn[i];
#         end if;
#     end for;
#     Append(~newEqnList, newEqn);
# end for;

# finalEqns := [eval(x) : x in newEqnList];

# ans := #RationalPoints(ChangeRing(Curve(W, finalEqns), GF(7)));
# # # ans;

# VARORDER := "xyzwtuvrsabcdefghiklmnopqj";
# plane_model_num_vars := 3;
# input_from_sage := ["13824*x^9*y^9-1728*x^9*y^6*z^3-46656*x^6*y^9*z^3-144*x^9*y^3*z^6+3240*x^6*y^6*z^6-104976*x^3*y^9*z^6-x^9*z^9+945*x^6*y^3*z^9+25515*x^3*y^6*z^9-19683*y^9*z^9+9*x^6*z^12-1053*x^3*y^3*z^12+6561*y^6*z^12-27*x^3*z^15-729*y^3*z^15+27*z^18"];

# W := ProjectiveSpace(Rationals(), plane_model_num_vars-1);
# names := [VARORDER[j] : j in [1..plane_model_num_vars]];
# AssignNames(~W, names);
# W_vars := [W.i : i in [1..plane_model_num_vars]];
# localDict := AssociativeArray(names);

# for i->name in names do
#     localDict[name] := Sprintf("W_vars[%o]", i);
# end for;

# newEqnList := [];
# for eqn in input_from_sage do
#     newEqn := "";
#     for i in [1..#eqn] do
#         if eqn[i] in names then
#             newEqn cat:= localDict[eqn[i]];
#         else
#             newEqn cat:= eqn[i];
#         end if;
#     end for;
#     Append(~newEqnList, newEqn);
# end for;

# finalEqns := [eval(x) : x in newEqnList];

# ans := #RationalPoints(ChangeRing(Curve(W, finalEqns), GF(7)));
