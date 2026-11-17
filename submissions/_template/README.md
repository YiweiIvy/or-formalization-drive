# <Name of the method>

<One or two sentences: what the method does and which concept or part of the
graph it was applied to.>

## Method

<How it works, step by step, in enough detail that someone else could apply it
to another concept. Say what was done by hand and what was automated (scripts,
agents, prompts), and how the candidates were found.>

## What was added

- Definition files: <n>. <What each one defines.>
- Theorems: <n>. <What they state: bridges, general theorems, shared lemmas.
  Say how many have no proof yet.>
- New proofs of theorems of the snapshot: <n>. <Which theorems, and what the
  new proofs import.>

## Deprecations

<Which nodes `manifest.jsonl` deprecates and why, or "None".>

## Verification

<How the Lean files were checked: toolchain, Mathlib revision, and whether
every file compiles without `sorry`.>

## Result

<Paste the output of
`python3 benchmark/or_bench.py score --submission submissions/<name>`.>

## Notes

<Optional: what did not work, what you would try next, how far the method
could scale.>
