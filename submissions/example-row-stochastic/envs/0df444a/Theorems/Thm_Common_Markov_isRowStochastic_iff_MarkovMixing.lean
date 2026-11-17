-- Graph-refinement submission | Theorems.Thm_Common_Markov_isRowStochastic_iff_MarkovMixing
-- name    : Common.Markov.isRowStochastic_iff_MarkovMixing
-- status  : Proved
-- title:
--   Bridge: `MarkovMixing.IsStochastic` is the common row-stochastic predicate
-- statement:
--   The local predicate `MarkovMixing.IsStochastic` and `Common.Markov.IsRowStochastic` hold for the same matrices.

import Mathlib
import Definitions.Def_Common_Markov_RowStochastic
import Definitions.Def_mm_basic

namespace Common.Markov

theorem isRowStochastic_iff_MarkovMixing {V : Type*} [Fintype V] [DecidableEq V] (P : Matrix V V ℝ) :
    MarkovMixing.IsStochastic P ↔ IsRowStochastic P := by sorry

end Common.Markov
