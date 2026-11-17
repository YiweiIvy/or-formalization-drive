# Contributing a method

The benchmark asks for methods that connect the dependency graph of the OR
Formalization Drive and get missions to build on shared definitions and
lemmas. [`benchmark/README.md`](benchmark/README.md) defines the graph and the
scores. This page is about entering a method.

A submission is a pull request that adds one folder, `submissions/<name>/`.
[`submissions/example-row-stochastic`](submissions/example-row-stochastic) is a
complete small one and [`submissions/_template`](submissions/_template) is a
skeleton to copy.

## Rules

1. **Every submission is scored against the base snapshot `v0`**, on its own.
   Submissions do not stack: yours cannot import files from another
   submission.
2. **Published files are immutable**, as on Prove2Me. You cannot change or
   replace a file of the snapshot. You can:
   - add definition files, theorems and proofs;
   - add a new proof, or proof sketch, of a theorem that is already in the
     snapshot;
   - deprecate nodes of the snapshot.
3. **Only environment `0df444a`** (Lean 4.33.1) is scored.
4. **The pull request changes `submissions/<name>/` and nothing else.**
5. **The Lean files are yours to verify.** CI does not compile anything. Before
   you open the pull request, check that every file compiles in `0df444a`, that
   the proofs you ship contain no `sorry` and add no axioms, and that each file
   imports only what it uses. See [Compiling locally](#compiling-locally).

Results from maintainers go through pull requests like everyone else's;
nothing is pushed to `main` directly.

## Steps

0. Get a branch to work on. Without write access to this repository, fork it
   on GitHub and clone your fork; with write access, clone this repository and
   create a branch. Either way a partial clone is enough and much faster:

   ```sh
   git clone --filter=blob:none https://github.com/<you>/or-formalization-drive
   cd or-formalization-drive
   git checkout -b <name>
   ```

1. Copy `submissions/_template` to `submissions/<name>` (letters, digits, `-`
   and `_`; not starting with `_`).
2. Put your Lean files under `submissions/<name>/envs/0df444a/`
   ([Files](#files)).
3. If the method deprecates nodes, list them in `manifest.jsonl`
   ([Deprecation](#deprecation)). Otherwise delete that file.
4. Fill in `README.md`: the method, in enough detail that someone else could
   apply it to another concept.
5. Score it:

   ```sh
   python3 benchmark/or_bench.py score --submission submissions/<name>
   ```

   The command exits with an error and lists the problems if the submission
   breaks a rule that it can check.
6. Commit, push the branch (to your fork, if you work on one), and open a pull
   request against `main` of this repository. CI posts the score as a comment
   within a minute and updates it on every push. This works the same for pull
   requests from forks.

## Files

```
submissions/<name>/
├── README.md                     the method (required)
├── manifest.jsonl                deprecated nodes (only if there are any)
└── envs/0df444a/
    ├── Definitions/Def_<Name>.lean
    ├── Theorems/Thm_<slug>.lean
    └── Solutions/Sol_<slug>.lean, Sol_<slug>_<n>.lean
```

The layout and the file formats are the ones of the snapshot and of Prove2Me.
A file name that already exists in `envs/0df444a/` is rejected.

**Definition file**, `Definitions/Def_<Name>.lean`. Imported as
`Definitions.Def_<Name>`. One node of the graph.

**Theorem**, `Theorems/Thm_<slug>.lean`. `<slug>` is the theorem's full name
with `.` replaced by `_`: the theorem `Common.Markov.foo` is in
`Thm_Common_Markov_foo.lean` and is imported as
`Theorems.Thm_Common_Markov_foo`. The file holds the statement and ends in
`:= by sorry`. One node of the graph.

**Proof**, `Solutions/Sol_<slug>.lean`. It proves `theorem solution` with the
same binders and type as the statement, without `sorry`. It may import
definitions and other theorems, but not the theorem it proves. A proof is not
a node; its imports become edges from its theorem. A new theorem with no proof
file is an Open theorem. That is allowed, and the report counts them.

**New proof of a theorem of the snapshot**, `Solutions/Sol_<slug>_<n>.lean`.
This is how an original node gets new edges, and it is the only way to raise
`S_reuse`. Take the smallest `<n>` that the snapshot does not use: if
`envs/0df444a/Solutions/` has `Sol_Foo_bar.lean` and `Sol_Foo_bar_2.lean`, ship
`Sol_Foo_bar_3.lean`. It may be a complete proof or a proof sketch that
imports Open theorems.

Start statement files with the header the snapshot uses, so the report shows
the item's name:

```lean
-- Graph-refinement submission | Theorems.Thm_Common_Markov_foo
-- name    : Common.Markov.foo
```

and proof files with

```lean
-- Prove2me | solution 1 for Common.Markov.foo
```

## Deprecation

`manifest.jsonl` has one JSON object per line. Each line deprecates one node of
the snapshot, a theorem or a definition file:

```json
{"deprecate": "Definitions.Def_FiniteTD_Markov_Chain", "replaced_by": "Definitions.Def_Common_Markov_RowStochastic", "reason": "same predicate as the common definition"}
{"deprecate": "Theorems.Thm_Some_junk_theorem", "reason": "vacuous statement"}
```

| Field | | |
|---|---|---|
| `deprecate` | required | A node of the snapshot, by module (`Definitions.Def_X`, `Theorems.Thm_X`) or by name (`Foo.bar`). |
| `replaced_by` | optional | The node to use instead: one of the snapshot or one you add. It must not be deprecated itself. It is a note for readers and for the later sync to Prove2Me. It is not scored. |
| `reason` | optional | One sentence. |

Deprecation on Prove2Me hides a node from discovery; the node stays importable
and everything that imports it keeps working. The benchmark takes the view of
someone who builds something new: **a deprecated node is removed from the
scored graph**, with all its edges. It is no longer counted, no path runs
through it, and a mission whose goal is deprecated is not scored.

So deprecating a node does not earn anything by itself, and it costs
connectivity when other nodes still import it. The useful order is: add the
replacement, give the theorems that used the old node new proofs on the
replacement, then deprecate the old node.

## What CI checks

The check is one Python command and takes a few seconds. It always uses the
scorer and the snapshot of `main`, and only reads the files of the pull
request:

- the pull request changes only `submissions/<name>/` (one that changes
  anything else is not scored);
- `README.md` exists;
- Lean files are in `envs/0df444a/{Definitions,Theorems,Solutions}` and are
  named `Def_*`, `Thm_*`, `Sol_*`;
- no file has the name of a file of the snapshot;
- every imported `Definitions.*` or `Theorems.*` module exists in the snapshot
  or in the submission;
- every proof file belongs to a theorem and does not import that theorem;
- every `manifest.jsonl` row is valid.

It does not compile Lean, look for `sorry` or axioms, or judge whether a
definition or a bridge is meaningful. Those are left to you and to the
reviewer who merges the pull request.

## Score

CI reports the change against `v0`:

- **pair connectivity**: the chance that two counted nodes are connected;
- **`S_reuse`**: the share of missions that share a dependency with a mission
  of a different work;
- direct reuse, mission pair connectivity, components, isolated nodes, largest
  component;
- the cost: new definition files, new theorems (and how many have no proof),
  new proofs of original theorems, deprecated nodes, and net definition files
  (new minus deprecated).

These are reported side by side. There is no single ranking number yet; it
will be chosen once a few methods have been scored.

## Compiling locally

A Lake project with the environment's toolchain and Mathlib is enough.
`lean-toolchain`:

```
leanprover/lean4:v4.33.1
```

`lakefile.toml`:

```toml
name = "orbench"

[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4"
rev = "0df444a360eaa60ab8c11dca51a86af692955474"

[[lean_lib]]
name = "Definitions"

[[lean_lib]]
name = "Theorems"

[[lean_lib]]
name = "Solutions"
```

Run `lake exe cache get` once. Copy your files into the project's
`Definitions/`, `Theorems/` and `Solutions/` folders, together with the
snapshot files they import (and the files those import), then build your
modules, for example `lake build Solutions.Sol_Common_Markov_foo`. Only the
files you import need to be there, not the whole snapshot.

## After the merge

`main` holds the benchmark: the snapshot, the scorer, the rules, and the merged
submissions. Accepted improvements are synced back to
[Prove2Me](https://prove2.me) separately, in batches. After a batch, a new
snapshot is exported and tagged `v1`, with its own baseline. Scores against
different snapshots are not comparable.
