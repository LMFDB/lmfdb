function ConvertHeckeEigenvalues(K_old, eigenvals, K_new, basis)
	// Input: The Hecke eigenvalues, eigenvals, in terms of a field generator (usually the eigenvalue for T_2) for the field K_old
	// Output: The Hecke eigenvalues in terms of the integral basis, basis, for the field K_new

	printf "Converting eigenvalues...";
	bool, iota := IsIsomorphic(K_old, K_new);
	if not bool then
		return "Error! Fields not isomorphic!";
	end if;

	// make change of basis matrix
	chg_basis_entries := [];
	for i in [1..#basis] do
		Append(~chg_basis_entries, Eltseq(basis[i]));
	end for;
	chg_basis_mat := Matrix(chg_basis_entries); // changes from basis to 1, a, a^2, ..., a^(n-1)
	chg_basis_mat := chg_basis_mat^(-1); // changes from 1, a, a^2, ..., a^(n-1) to basis

	// convert entries
	eigenvals_new := [];
	for i in [1..#eigenvals] do
		v := Vector(Eltseq(iota(eigenvals[i])));
		Append(~eigenvals_new, v*chg_basis_mat);
	end for;
	printf "completed!\n";

	printf "Verifying correctness...";
	// verify correctness of normalized eigenvalues
	eigenvals_old := [iota(el) : el in eigenvals];
	for j in [1..#eigenvals_old] do
		new_val := 0;
		for i in [1..#basis] do
			new_val +:= eigenvals_new[j][i]*basis[i];
		end for;
		assert new_val eq eigenvals_old[j];
	end for;
	printf "verified!\n";

	return eigenvals_new;
end function;