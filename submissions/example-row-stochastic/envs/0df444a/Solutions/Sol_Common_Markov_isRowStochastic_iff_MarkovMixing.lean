-- Prove2me | solution 1 for Common.Markov.isRowStochastic_iff_MarkovMixing

import Mathlib
import Definitions.Def_Common_Markov_RowStochastic
import Definitions.Def_mm_basic

theorem solution {V : Type*} [Fintype V] [DecidableEq V] (P : Matrix V V ℝ) :
    MarkovMixing.IsStochastic P ↔ Common.Markov.IsRowStochastic P :=
  Iff.rfl
