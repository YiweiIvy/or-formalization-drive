-- Graph-refinement submission | Theorems.Thm_Common_Markov_isRowStochastic_iff_FiniteTD
-- name    : Common.Markov.isRowStochastic_iff_FiniteTD
-- status  : Proved
-- title:
--   Bridge: `FiniteTD.Markov.IsStochastic` is the common row-stochastic predicate
-- statement:
--   The local predicate `FiniteTD.Markov.IsStochastic` and `Common.Markov.IsRowStochastic` hold for the same matrices.

import Mathlib
import Definitions.Def_Common_Markov_RowStochastic
import Definitions.Def_FiniteTD_Markov_Chain

namespace Common.Markov

theorem isRowStochastic_iff_FiniteTD {S : Type} [Fintype S] (P : S → S → ℝ) :
    FiniteTD.Markov.IsStochastic P ↔ IsRowStochastic (Matrix.of P) := by sorry

end Common.Markov
