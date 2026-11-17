# Example: one row-stochastic predicate for three works

A small, complete submission. It shows the format and the common-ancestor
approach on a real duplicate; it is not a competitive result.

## Method

"`P` is a stochastic matrix" (nonnegative entries, rows sum to one) is defined
in 23 definition files of the base snapshot under local names. This submission
adds the predicate once and proves that three of the local copies are the same
predicate:

| Local definition | Defined in | Component in `v0` |
|---|---|---:|
| `MarkovMixing.IsStochastic` | `Def_mm_basic` | 11,085 nodes |
| `FiniteTD.Markov.IsStochastic` | `Def_FiniteTD_Markov_Chain` | 10 nodes |
| `MarkovInterference.DQBias.IsStochastic` | `Def_MarkovInterference_DQBias_Chain` | 8 nodes |

1. `Def_Common_Markov_RowStochastic` defines `Common.Markov.IsRowStochastic`.
2. Three bridge theorems, `Common.Markov.isRowStochastic_iff_<work>`, each
   import the common definition and one local definition and state that the
   two predicates are equivalent. Their proofs are in `Solutions/`.

The candidates were found with

    python3 benchmark/or_bench.py probe --pattern 'def IsStochastic'

## What was added

- 1 definition file, 3 theorems, 3 proofs. Nothing is deprecated, so there is
  no `manifest.jsonl`.
- All seven files compile with Lean 4.33.1 and the environment's Mathlib
  (`0df444a`); the proofs contain no `sorry`.

## Result

    python3 benchmark/or_bench.py score --submission submissions/example-row-stochastic

Pair connectivity rises because two small components join the largest one.
`S_reuse` does not move: a bridge imports the original definitions, so it is in
no mission's dependency cone. To move it, a submission would also add a new
proof of an original theorem, for example
`Solutions/Sol_FiniteTD_Markov_lemma_3_2.lean`, that imports the common
definition or a lemma stated on it.
