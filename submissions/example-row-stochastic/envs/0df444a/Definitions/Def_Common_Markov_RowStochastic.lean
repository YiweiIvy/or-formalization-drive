-- Graph-refinement submission | Definitions.Def_Common_Markov_RowStochastic
-- name    : Common_Markov_RowStochastic
-- status  : Definition
-- title:
--   Row-stochastic matrix on a finite state space
-- statement:
--   A real matrix $P$ indexed by a finite set is row-stochastic when $P_{ij}\ge 0$ for all $i,j$
--   and $\sum_j P_{ij}=1$ for every $i$. This is the transition matrix of a finite Markov chain.
--   Several works in the collection define the same predicate under a local name; the bridge
--   theorems `Common.Markov.isRowStochastic_iff_*` identify each of them with this one.

import Mathlib

namespace Common.Markov

/-- `P` is row-stochastic: nonnegative entries, every row sums to one. -/
def IsRowStochastic {ι : Type*} [Fintype ι] (P : Matrix ι ι ℝ) : Prop :=
  (∀ i j, 0 ≤ P i j) ∧ ∀ i, ∑ j, P i j = 1

end Common.Markov
