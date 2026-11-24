# orcore-dedup: machine-checked deduplication of definitions and theorems

**Status: work in progress, not yet submitted.** Every Lean file below passes the in-process check
described under [Verification](#verification). The standalone per-file compile that
CONTRIBUTING.md asks for has not been run yet.

The snapshot was formalized paper by paper, so many objects are defined again and again under local
names, and many theorems are posted more than once. This submission finds those duplicates
mechanically, proves in Lean that they are the same, and uses the proofs to connect the graph and to
deprecate redundant nodes. Nothing is matched by keyword or by eye: a duplicate counts only when a
Lean proof of the equality is checked.

## Method

### 1. Exact duplicate definitions → common definitions

1. Parse every top-level `def`/`abbrev` in the 11,265 definition files and normalise its text:
   comments removed, whitespace collapsed, bound-variable names replaced by positional names. Two
   declarations whose normalised text agrees are candidates (3,129 clusters in two or more files).
2. Write one copy, the *common definition*, in namespace `ORCore`, depending only on Mathlib
   (or on other common definitions, for definitions that use one another).
3. For every local copy, check `@Local = @ORCore.common := rfl` with the local file's real import
   closure. Only copies that pass are kept: 1,087 clusters, 2,999 local copies.
4. Keep the clusters whose bridges join different components, chosen greedily by the gain in pair
   connectivity. Group definitions that live in the same files into one common definition file.

Each kept cluster becomes `Definitions/Def_ORCore_<name>.lean` plus, per local definition file, a
bridge theorem `ORCore.Bridge.<name>__<file>` stating the equalities, proved by `rfl`.

### 2. Near-duplicate definitions

Definitions with the same name and the same signature but different text (for example `√x` against
`Real.sqrt x`, or a different but equivalent formula) were tested against each other with a fixed
portfolio of proofs (`rfl`, `simp`, `unfold … ; ring`, `propext … tauto`, `grind`). 139 pairs were
proved equal; the 46 that join different components are shipped as `ORCore.Equiv.*` (equal to a
common definition) and `ORCore.Link.*` (equal to another paper's definition).

### 3. Hand-written bridge

`ORCore.ruinTime` is the first time a surplus process is negative. It is defined for an arbitrary
process in `SchmidliRuin.Verif` and for the controlled risk process of a spectrally negative Lévy
process in `AvramDividend.Classical`. The two bridges are proved by `rfl`. They join the
4,320-node AvramDividend component to the main component.

### 4. Duplicate theorems

Theorems whose statements are equal up to bound-variable names were grouped. In each group the
proved theorem with the most importers is the *root*; for every other member, a new proof that only
cites the root was checked (1,443 pass). Then:

| Action | Count | Rule |
|---|---:|---|
| deprecated (`manifest.jsonl`, `replaced_by` = root) | 115 | nothing imports the theorem and it is not a mission goal |
| new proof shipped (`Sol_<slug>_<n>.lean`) | 26 | the theorem is Open (all 26 are), or joins a component, or links two works |
| report only | 1,302 | other theorems import it, so deprecating it would cut them off |

All 115 deprecated theorems are mission members or milestones in `seeds.json`; on Prove2Me,
deprecation would hide them from their missions. That needs a maintainer's decision.

## Result

`python3 benchmark/or_bench.py score --submission submissions/orcore-dedup`

| | base | submission |
|---|---:|---:|
| Pair connectivity | 6.87% | 40.96% |
| `S_reuse` | 36.21% | 36.21% |
| Mission pair connectivity | 6.51% | 26.25% |
| Weak components | 3,103 | 2,399 |
| Largest component | 11,085 | 35,086 |
| Isolated nodes | 815 | 782 |

Cost: 321 new definition files, 1,230 new theorems (all proved), 26 new proofs of original
theorems, 115 deprecated theorems. Most new theorems are one-line `rfl` bridges; no new node
touches more than two original components directly.

`S_reuse` does not move: bridges import the originals, so they are in no mission's cone. Moving it
needs original solutions refactored to cite shared lemmas (planned).

## Reports

- `reports/duplicate_definitions.jsonl`: every verified duplicate-definition cluster, its copies
  and its common definition (or `null` when it was not needed for connectivity).
- `reports/common_definitions.jsonl`: each common definition file, with the local copies it replaces.
- `reports/near_duplicate_bridges.jsonl`: each near-duplicate pair and the proof used.
- `reports/duplicate_theorems.jsonl`: every duplicate theorem, its root and the action taken.

These are the deprecation candidates for a later cleanup: once the theorems that import a local
copy are re-proved on the common definition, the local copy can be deprecated without cutting
anything off.

## Verification

Lean 4.33.1, Mathlib `0df444a`. A batch checker (`Checker.lean` in the tooling) imports Mathlib once,
then elaborates each file together with its real local import closure, from source, and reports
every error. All 2,781 Lean files of this submission pass. Proofs contain no `sorry`. A citation
proof imports the cited theorem's statement file, which ends in `sorry` like every statement file
in the snapshot.

Still to do before submitting: compile each file standalone with `lean -o` against built `.olean`s,
and `#print axioms` for every proof.

## Reproducing

The tooling (mining, checking and emitting scripts) is kept outside this repository. Its README
lists every stage. `assemble.sh` regenerates this folder from the checked results.
