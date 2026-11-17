-- Prove2me | solution 1 for Common.Markov.isRowStochastic_iff_DQBias

import Mathlib
import Definitions.Def_Common_Markov_RowStochastic
import Definitions.Def_MarkovInterference_DQBias_Chain

theorem solution {S : Type} [Fintype S] [DecidableEq S] (P : Matrix S S ℝ) :
    MarkovInterference.DQBias.IsStochastic P ↔ Common.Markov.IsRowStochastic P :=
  Iff.rfl
