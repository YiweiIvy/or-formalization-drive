-- Prove2me | solution 1 for Common.Markov.isRowStochastic_iff_FiniteTD

import Mathlib
import Definitions.Def_Common_Markov_RowStochastic
import Definitions.Def_FiniteTD_Markov_Chain

theorem solution {S : Type} [Fintype S] (P : S → S → ℝ) :
    FiniteTD.Markov.IsStochastic P ↔ Common.Markov.IsRowStochastic (Matrix.of P) :=
  Iff.rfl
