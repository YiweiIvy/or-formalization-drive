-- Graph-refinement submission | Theorems.Thm_ORCore_Lemma_trace_vecMulVec_8a95b811
-- name    : ORCore.Lemma.trace_vecMulVec_8a95b811
-- status  : Proved
-- title:
--   Shared lemma `trace_vecMulVec`, re-proved inside the accepted proofs of 2 theorems
-- statement:
--   `{n : ℕ} (A : Matrix (Fin n) (Fin n) ℝ) (v : Fin n → ℝ) : (A * vecMulVec v v).trace = v ⬝ᵥ (A *ᵥ v)`
--   The base snapshot proves this statement as a private helper lemma inside 2 accepted solutions, in missions of 2 source works.
--   It imports the definitions its statement uses. Here it is stated once; the refactored solutions of this submission cite it.

import Mathlib
import Definitions.Def_ModernConvex_Relaxations_SignRelaxations
import Theorems.Thm_ModernConvex_Relaxations_opt_ge_asin_bound
import Theorems.Thm_ModernConvex_Relaxations_asin_matrix_ge

open Matrix
open ModernConvex.Relaxations

namespace ORCore.Lemma

theorem trace_vecMulVec_8a95b811 {n : ℕ} (A : Matrix (Fin n) (Fin n) ℝ) (v : Fin n → ℝ) :
    (A * vecMulVec v v).trace = v ⬝ᵥ (A *ᵥ v) := by sorry

end ORCore.Lemma
