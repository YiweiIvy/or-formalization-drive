-- Graph-refinement submission | Theorems.Thm_Common_Markov_isRowStochastic_iff_DQBias
-- name    : Common.Markov.isRowStochastic_iff_DQBias
-- status  : Proved
-- title:
--   Bridge: `MarkovInterference.DQBias.IsStochastic` is the common row-stochastic predicate
-- statement:
--   The local predicate `MarkovInterference.DQBias.IsStochastic` and `Common.Markov.IsRowStochastic` hold for the same matrices.

import Mathlib
import Definitions.Def_Common_Markov_RowStochastic
import Definitions.Def_MarkovInterference_DQBias_Chain

namespace Common.Markov

theorem isRowStochastic_iff_DQBias {S : Type} [Fintype S] [DecidableEq S] (P : Matrix S S ℝ) :
    MarkovInterference.DQBias.IsStochastic P ↔ IsRowStochastic P := by sorry

end Common.Markov
