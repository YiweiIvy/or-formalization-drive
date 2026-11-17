# Graph refinement benchmark

The OR Formalization Drive was formalized paper by paper, so the same objects
(linear programs, Markov chains, queues) are defined many times under local
names, and most of the dependency graph is small islands. This benchmark scores
methods that connect those islands and get missions to build on common ground.

`or_bench.py` is one Python file with no dependencies. It needs no database and
no Lean toolchain.

```sh
# baseline numbers for the dataset (about 4 s)
python3 benchmark/or_bench.py stats

# score a method
python3 benchmark/or_bench.py score --submission submissions/example-row-stochastic

# where to start: components that mention a concept, and what joining them would earn
python3 benchmark/or_bench.py probe --pattern 'markov chain|transition (matrix|kernel)'
```

Add `--json` to any command for machine-readable output. To enter a method,
see [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## The graph

- **Node**: one Formalpedia item, which is one Lean file. A theorem
  (`Theorems/Thm_*.lean`; status Proved, Open or Disproved) or a definition
  file (`Definitions/Def_*.lean`, usually many declarations). Accepted proofs
  (`Solutions/Sol_*.lean`) are not nodes; they belong to their theorem.
- **Edge**: `parent -> child` when the parent's statement file or one of its
  accepted solution files has `import <child>`. This is a file-level import,
  consumer to dependency. It is what `graph-*.jsonl` records.
- **Environment**: edges never cross Mathlib environments. Scores are reported
  on the default environment `0df444a`, which holds 96.5% of the nodes.

## Scores

Published files are immutable, as on Prove2Me. A submission adds new nodes and
new proofs, and it may deprecate original nodes. A new proof of an original
theorem adds import edges that start at that theorem.

The submission is scored on the graph that is left after its deprecations.
A deprecated node is hidden from discovery, so nothing new will be built on it:
it is not counted, and no connecting path or dependency cone runs through it.
New nodes may sit on a connecting path, but only the original nodes that are
not deprecated are counted; below, $V_0$ is that set. A mission whose goal is
deprecated is not scored. The baseline is always the full base snapshot `v0`.

**Benchmark 1, pair connectivity.** Let $\mathcal C(G)$ be the weak components
of $G$, each restricted to $V_0$.

$$P(G)=\frac{\sum_{C\in\mathcal C(G)}|C|\,(|C|-1)}{|V_0|\,(|V_0|-1)},\qquad
S_{\text{pair}}=\frac{P(G_+)-P(G_0)}{1-P(G_0)}$$

$P$ is the chance that two original nodes drawn at random are connected. The
number of components ($\Delta_{\text{conn}}$, $S_{\text{conn}}$) is reported
next to it. It is not the headline because it values every merge equally:
joining all 815 isolated nodes to each other lowers the count by 814 and moves
$P$ from 6.87% to 6.89%, while joining the two largest components lowers the
count by 1 and moves $P$ to 12.71%.

**Benchmark 2, cross-work reuse coverage.** A mission's dependency cone $D(m)$
is its own items plus everything they import, transitively. Its source work
$w(m)$ is the book or paper it is a part of (missions come in series: I, II,
III, ...).

$$R(m)=\mathbb 1\{\exists m':\ w(m')\neq w(m),\ D(m)\cap D(m')\neq\emptyset\},\qquad
S_{\text{reuse}}=\frac{1}{|\mathcal M_0|}\sum_{m\in\mathcal M_0}R(m)$$

A mission counts when it shares at least one dependency with a mission of a
different work. *Direct reuse* is the stricter number: the cone contains an
item that belongs to a mission of another work.

The two benchmarks reward different things. A bridge theorem that imports two
bodies of work connects them (Benchmark 1) but is in nobody's cone. Benchmark 2
moves only when an original theorem gets a new proof, or proof sketch, that
imports something another work also uses.

Deprecation alone earns nothing: it removes the node's edges, and a node that
others still import leaves them cut off. It pays once the nodes that used the
deprecated one have new proofs on its replacement.

The report also lists what the method cost: new definition files, new theorems
(and how many have no proof), new proofs of original theorems, deprecated
nodes, and the net number of definition files (new minus deprecated). There is
no single combined score yet.

## Baseline

Formalpedia snapshot of 2026-11-10, environment `0df444a`. The full output is in
[`baseline.json`](baseline.json).

| | |
|---|---|
| Nodes | 54,944 (43,679 theorems, 11,265 definition files) |
| Import edges | 107,545 |
| **Pair connectivity** | **6.87%** |
| Weak components | 3,103 (815 isolated nodes) |
| Largest components | 11,085 / 7,951 / 4,320 / 1,051 nodes |
| Missions scored | 3,891 of 4,288 (goal is in the snapshot), in 1,906 works |
| **$S_{\text{reuse}}$** | **36.21%** (57.65% if parts of the same work count) |
| Direct reuse | 0.62% (1.75% if parts of the same work count) |
| Mission pair connectivity | 6.51% |

## Submissions

A submission is an overlay in the repository's own layout. It only adds files;
a file that has the name of a file in the base snapshot is rejected.

```
my_method/README.md                             the method
my_method/manifest.jsonl                        nodes the method deprecates (optional)
my_method/envs/0df444a/Definitions/Def_*.lean   new definition files
my_method/envs/0df444a/Theorems/Thm_*.lean      new theorem statements
my_method/envs/0df444a/Solutions/Sol_*.lean     proofs of the new theorems, and new
                                                proofs of original theorems
```

Edges are read from the files' `import` lines. `Sol_<slug>.lean` (or
`Sol_<slug>_<n>.lean`) is a proof of `Thm_<slug>.lean`. To give an original
theorem a new proof or proof sketch, ship `Sol_<slug>_<n>.lean` with an `<n>`
that the snapshot does not use; its imports become new edges from the original
theorem.

Each line of `manifest.jsonl` deprecates one original node:

```json
{"deprecate": "Definitions.Def_FiniteTD_Markov_Chain", "replaced_by": "Definitions.Def_Common_Markov_RowStochastic", "reason": "same predicate"}
```

`replaced_by` and `reason` are optional and are not scored; they record which
node to use instead.

[`CONTRIBUTING.md`](../CONTRIBUTING.md) has the full rules and
[`submissions/example-row-stochastic`](../submissions/example-row-stochastic)
a complete small submission.

For quick experiments without Lean files, an overlay can instead (or also)
carry `index-*.jsonl` and `graph-*.jsonl` rows in the dataset's format; see
[`example/`](example). The report says how many edges came from such rows.

The scorer does not compile anything. For each new node it prints how many
original components that node touches directly, so a result that comes from
one very wide file is easy to see. It exits with an error, and lists what is
wrong, if a submission overwrites a base file, imports a local module that
does not exist, ships a proof for no theorem, or has a bad manifest row.

## Finding a place to start

`probe` matches a regex against the Lean files (definition files by default)
and reports the components touched and the pair connectivity if all of them
were joined. Text matches are an upper bound on the files that really define a
concept.

| Definition files mentioning | Files | Components | Pair connectivity if joined |
|---|---:|---:|---:|
| Linear program, LP | 596 | 248 | 19.15% |
| Queue, queueing | 362 | 116 | 14.93% |
| Mixed-integer or integer program | 85 | 41 | 14.38% |
| Nash equilibrium, game | 735 | 250 | 11.76% |
| Convex function or program, subgradient | 570 | 172 | 9.60% |
| Markov chain, transition matrix or kernel | 404 | 129 | 9.08% |
| Markov decision process | 336 | 96 | 8.02% |

Two approaches to try first:

1. **A common ancestor.** Define one general object (for example a
   parameterized mixed-integer program), instantiate it for each paper's model,
   and prove a bridge between each original model and its instance. This moves
   Benchmark 1. It moves Benchmark 2 once original theorems have new proofs
   that derive them from the standardized ones.
2. **Decompose long proofs.** 5,131 accepted solutions are over 500 lines.
   Extract an argument as a standalone lemma, or match it to an existing node,
   and give the original theorems new proofs that import it. This moves both
   benchmarks when proofs from two different components import the same lemma.

## Limits

- `seeds.json` records only each mission's goal, so a mission's cone is its
  goal's cone (median 4 nodes). `--members FILE` with
  `{mission_id: [theorem ids]}` makes the cone cover every item of the mission.
- A mission's work is derived from its name: the text before the first colon,
  without the trailing part number. A `"work"` field on a mission in
  `seeds.json` overrides it.
- Mathlib imports are not in the graph. Two components that build on the same
  Mathlib structure count as disconnected; the benchmark measures connection
  through this repository's own files.
- Import edges say a file can see another, not that it uses it.
