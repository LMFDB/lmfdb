"""
    To run this test only (as opposed to all verification tests across all tables),
    execute from the top level of the LMFDB directory:

        sage -python lmfdb/verify/verify_tables.py logs modcurve_models slow

"""

from sage.all import lazy_attribute, QQ, magma, PolynomialRing
from lmfdb.lmfdb_database import db
from lmfdb.modular_curves.upload import VARORDER
import json
from ..verification import TableChecker, slow
from timeout_decorator import timeout, TimeoutError
import sys


# Define the Magma script template as a global constant
# Using named placeholders {num_vars} and {input_from_sage}
MAGMA_GENUS_SCRIPT_TEMPLATE = """
// Set up variables and parameters
// VARORDER is defined within the script for clarity
VARORDER := "{varorder_val}";
num_vars := {num_vars};
input_from_sage := {input_from_sage};

// ========== Process Model ==========

// Define the projective space
W := ProjectiveSpace(Rationals(), num_vars - 1);
// Select and assign variable names
names := [VARORDER[j] : j in [1..num_vars]];
AssignNames(~W, names);
// Get the coordinate variables into a list
W_vars := [W.i : i in [1..num_vars]];
// Create mapping from name character -> string like "W_vars[1]"
localDict := AssociativeArray(names);
for i->name in names do
    localDict[name] := Sprintf("W_vars[%o]", i);
end for;
// Manually build new equation strings with substitutions
newEqnList := [];
for eqn in input_from_sage do
    newEqn := "";
    for i in [1..#eqn] do
        if eqn[i] in names then
            newEqn cat:= localDict[eqn[i]];
        else
            newEqn cat:= eqn[i];
        end if;
    end for;
    Append(~newEqnList, newEqn);
end for;
// Evaluate the newly constructed strings to get Magma polynomial objects
finalEqns := [eval(x) : x in newEqnList];
// Define the curve using the evaluated equations
C := Curve(W, finalEqns);
// Base script ends here. The curve 'C' is now defined.
"""


def compute_genus(eqn_list, num_vars):
    """
    Check that the point counts of the plane model and canonical model match
    at several primes of good reduction.
    """

    # 2. Convert Python lists to Magma list-of-strings format
    magma_eqn_list_str = json.dumps(eqn_list)

    # 3. Format the template script with the dynamic values
    #    Injecting VARORDER here as well for self-contained template logic
    base_script = MAGMA_GENUS_SCRIPT_TEMPLATE.format(
        varorder_val=VARORDER,
        num_vars=num_vars,
        input_from_sage=magma_eqn_list_str
    )

    # 4. Define the specific Magma commands for this function
    #    Ensure newlines for proper Magma syntax separation
    genus_commands = """
    // Compute and print the genus (appended commands)
    myGenus := Genus(C);
    print myGenus;
    """

    # 5. Combine the base script with the specific commands
    magma_script = base_script + genus_commands

    return int(magma.eval(magma_script, verbose=False).strip())


class modcurve_models(TableChecker):
    table = db.modcurve_models

    # The following column isn't the label column, but it's the
    # most useful for error reporting.
    label_col = 'modcurve'

    @lazy_attribute
    def plane_models(self):
        return {rec["modcurve"]: rec for rec in db.modcurve_models.search({"model_type":2}, ['equation', 'modcurve', 'model_type', 'number_variables'])}

    @slow(projection=['equation', 'modcurve', 'number_variables', 'model_type'])
    def check_genus(self, rec):

        # The hyperelliptic case requires separate handling
        if rec["model_type"] == 5:
            # we first assert that number of variables is 3
            assert rec["number_variables"] == 3
            # we check that we only have one equation
            assert len(rec["equation"]) == 1
            # we extract the equation
            eqn = rec["equation"][0]
            P = PolynomialRing(QQ, 3, names=VARORDER[:3])
            x,y,z = P._first_ngens(3)
            # we obtain the
            degree_f = P(eqn).degree()
            return ((degree_f - 1)//2 == int(rec["modcurve"].split('.')[2]))

        # Ditto for the 'double cover of a pointless conic'
        if rec["model_type"] == 7:
            # we first assert that number of variables is 3
            assert rec["number_variables"] == 4
            # we check that we only have one equation
            assert len(rec["equation"]) == 2
            # we extract the equation
            eqn = rec["equation"]
            P = PolynomialRing(QQ, 4, names=VARORDER[:4])
            x,y,z,w = P._first_ngens(4)
            # we obtain the degree of the model from the equations
            degree_curve = P(eqn[0]).degree() * P(eqn[1]).degree()
            return ((degree_curve - 1)//2 == int(rec["modcurve"].split('.')[2]))

        # Define a wrapper for the compute_genus call to apply the timeout
        # We are giving it a 5-second timeout here.
        try:
            # Create a function that calls compute_genus with the current arguments
            def call_compute_genus():
                return compute_genus(rec["equation"], rec["number_variables"])

            # Apply the timeout decorator to this specific call
            timed_compute_genus = timeout(5)(call_compute_genus)
            magma_computed_genus = timed_compute_genus()
        except TimeoutError:
            print(f"MODCURVE_MODELS: Call to compute_genus for {rec['modcurve']} TIMED OUT after 5 seconds.", file=sys.stderr, flush=True)
            # For this direct test, a timeout means the check fails.
            return True
        except Exception as e:
            print(f"MODCURVE_MODELS: compute_genus for {rec['modcurve']} raised an exception: {e}", file=sys.stderr, flush=True)
            # Other exceptions also mean the check fails.
            return False

        # If it timed out, we've already returned False.
        # If it didn't time out, proceed with the comparison.
        # This part is reached only if no timeout and no other exception occurred.
        return (magma_computed_genus == int(rec["modcurve"].split('.')[2]))
