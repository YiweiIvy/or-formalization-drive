-- Prove2me | solution 1 for ORCore.Lemma.sum_sub_succ_065b73de
-- Graph-refinement submission: the proof is the helper lemma `sum_sub_succ` of Sol_BnBPEP_WeakCvx_corollary_1.lean (@sometik179), unchanged.

import Mathlib
import Definitions.Def_SAGA_Convex_IsProxPoint
import Definitions.Def_BnBPEP_WeakCvx_IsWeakSubgrad
import Definitions.Def_BnBPEP_WeakCvx_InWeakClass
import Definitions.Def_BnBPEP_WeakCvx_moreauEnv

open scoped BigOperators
open Filter Set
open BnBPEP.WeakCvx
open Set
open BnBPEP.WeakCvx
open Filter Set
open scoped BigOperators

theorem solution (a : ℕ → ℝ) (n : ℕ) :
    (∑ k ∈ Finset.range n, (a k - a (k + 1))) = a 0 - a n := by
  induction n with
  | zero => simp
  | succ n ih => rw [Finset.sum_range_succ, ih]; ring
