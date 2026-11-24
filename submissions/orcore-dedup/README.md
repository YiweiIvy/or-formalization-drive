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
| new proof shipped (`Sol_<slug>_<n>.lean`) | 62 | the theorem is Open (29 are), or joins a component, or links two works |
| report only | 1,381 | a new proof would add nothing |

**Deprecation is proposed, not applied.** 115 of the duplicates are imported by nothing and are not
mission goals, so deprecating them in favour of their root would disconnect nothing. They are listed
in `reports/deprecation_candidates.jsonl`, in the row format of `manifest.jsonl`, for maintainers to
review. All 115 are mission members or milestones in `seeds.json`. On Prove2Me, deprecation hides a
node from discovery but keeps it importable, so it is reversible archiving, not deletion. Applying
them (renaming the file to `manifest.jsonl`) gave pair connectivity 40.96% instead of 40.92%
(measured before section 5 was added).

### 5. Shared lemmas

Many accepted solutions prove the same helper lemma privately, in papers from different works.

1. Collect the helper lemmas declared inside accepted solutions of theorems in mission cones
   (182,399 lemmas), normalise their statements as in section 1, and keep the statements that
   reach missions of two or more works (3,732 clusters).
2. Check one member's proof of each cluster standalone: with Mathlib alone, or with the local
   definition files its statement uses. 923 clusters pass.
3. Choose clusters greedily by the number of missions newly connected to another work. Each chosen
   cluster becomes a theorem `ORCore.Lemma.<name>_<hash>` (`Theorems/Thm_ORCore_Lemma_*.lean`)
   whose solution is the original helper proof, unchanged and credited to its author.
4. For each original theorem involved, write a new solution (`Sol_<slug>_<n>.lean`): the accepted
   solution, unchanged, except that the helper's proof is replaced by a citation
   `@ORCore.Lemma.<name> args`, and the lemma is imported.

273 solutions were rewritten; 267 pass and are shipped, with 123 shared lemmas. The 6 that fail
cite a lemma whose statement uses a same-named definition from another paper; they are dropped.
`reports/shared_lemmas.jsonl` lists each lemma and the solutions that cite it.

## Result

`python3 benchmark/or_bench.py score --submission submissions/orcore-dedup`

| | base | submission |
|---|---:|---:|
| Pair connectivity | 6.87% | 44.31% |
| `S_reuse` | 36.21% | 42.25% |
| Mission pair connectivity | 6.51% | 29.92% |
| Weak components | 3,103 | 2,297 |
| Largest component | 11,085 | 36,571 |
| Isolated nodes | 815 | 766 |

Cost: 321 new definition files, 1,353 new theorems (all proved: 1,230 bridges and links, 123 shared
lemmas), 329 new proofs of original theorems (62 citation proofs, 267 refactored solutions), no
deprecations. Most new theorems are one-line `rfl` bridges.

Sections 1–4 leave `S_reuse` unchanged: bridges import the originals, so they are in no mission's
cone. Section 5 moves it: a refactored solution puts the shared lemma into the cone of every mission
above that theorem, so missions of different works now share a node.

## Reports

- `reports/duplicate_definitions.jsonl`: every verified duplicate-definition cluster, its copies
  and its common definition (or `null` when it was not needed for connectivity).
- `reports/common_definitions.jsonl`: each common definition file, with the local copies it replaces.
- `reports/near_duplicate_bridges.jsonl`: each near-duplicate pair and the proof used.
- `reports/duplicate_theorems.jsonl`: every duplicate theorem, its root and the action taken.
- `reports/deprecation_candidates.jsonl`: the 115 proposed deprecations (not applied).
- `reports/shared_lemmas.jsonl`: each shared lemma, its imports, and the refactored solutions citing it.

These are the deprecation candidates for a later cleanup: once the theorems that import a local
copy are re-proved on the common definition, the local copy can be deprecated without cutting
anything off.

## Verification

Lean 4.33.1, Mathlib `0df444a`. A batch checker (`Checker.lean` in the tooling) imports Mathlib once,
then elaborates each file together with its real local import closure, from source, and reports
every error. All 3,294 Lean files of this submission pass. Proofs contain no `sorry`. A citation
proof imports the cited theorem's statement file, which ends in `sorry` like every statement file
in the snapshot.

Still to do before submitting: compile each file standalone with `lean -o` against built `.olean`s,
and `#print axioms` for every proof.

## Reproducing

The tooling (mining, checking and emitting scripts) is kept outside this repository. Its README
lists every stage. `assemble.sh` regenerates this folder from the checked results.
