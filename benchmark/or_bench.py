#!/usr/bin/env python3
"""Graph-refinement benchmark for the OR Formalization Drive subset.

The graph, as the subset ships it (no database, no Lean toolchain needed):

  node  one Formalpedia item = one Lean file: a theorem (Theorems/Thm_*.lean,
        status Proved / Open / Disproved) or a definition file
        (Definitions/Def_*.lean, which may hold many declarations).
  edge  parent -> child: the parent's statement file or one of its accepted
        solution files has `import <child module>`. File-level imports, not
        constant-level references. Edges never cross environments.

Three commands, run from the repository root (--data defaults to it):

  # baseline numbers for the dataset
  python3 benchmark/or_bench.py stats

  # score a method: what does adding these files / edges change?
  python3 benchmark/or_bench.py score --submission my_method/

  # where to start: which components mention a concept, and what joining them would earn
  python3 benchmark/or_bench.py probe --pattern 'markov chain|transition (matrix|kernel)'

Headline scores:

  pair connectivity  chance that two original nodes drawn at random are weakly
                     connected (new nodes may sit on the path). Unlike the raw
                     component count it weights a merge by the nodes it joins.
  S_reuse            share of missions whose dependency cone meets the cone of a
                     mission from a different source work, i.e. the two are
                     built on at least one common file.

A submission is an overlay in the subset's own layout. Published files are
immutable, as on Prove2Me: a submission only adds files and retires nodes.

  my_method/envs/<env>/Definitions/Def_*.lean   new definition files
  my_method/envs/<env>/Theorems/Thm_*.lean      new theorem statements
  my_method/envs/<env>/Solutions/Sol_*.lean     proofs of the new theorems, and new
                                                proofs or sketches of existing ones
                                                (Sol_<slug>_<n>.lean, a free <n>)
  my_method/manifest.jsonl                      {"deprecate","replaced_by","reason"}
                                                rows: nodes the method retires
  my_method/envs/<env>/graph-*.jsonl            {"parent","child","via"} rows, for
                                                quick experiments without Lean files
  my_method/envs/<env>/index-*.jsonl            {"theorem_name","module"} rows for
                                                nodes named only in graph rows

Edges from .lean files are read from their `import` lines. The submission is
scored on the graph that is left after its deprecations: a retired node is not
counted and no path runs through it. This script does NOT compile anything; a
submission's Lean files must be verified separately before its score means
anything.

A mission's dependency cone is everything its items import, transitively.
seeds.json only records each mission's goal, so by default the cone is the
goal's. Pass --members FILE ({mission_id: [theorem ids]}) to use every item of
the mission. A mission's source work is its "work" field if present, else its
name up to the first colon without the trailing part number ("... XIII").
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOCAL = ("Theorems.", "Definitions.")
IMPORT = re.compile(r"^\s*(?:public\s+|private\s+|meta\s+)*import\s+(?:all\s+)?(\S+)")
SOL_HEADER = re.compile(r"^-- Prove2me \| solution \d+ for (.+?)\s*$")
NAME_HEADER = re.compile(r"^-- name\s*:\s*(\S+)\s*$")
PART = re.compile(r"\s+(?:[IVXLC]+|\d+|Part\s+\S+)\s*$")


def work_of(mission):
    """The source work (book or paper) a mission is a part of."""
    return mission.get("work") or PART.sub("", mission["name"].split(":")[0].strip()).strip().lower()


def pair_conn(sizes, n):
    return sum(s * (s - 1) for s in sizes) / (n * (n - 1)) if n > 1 else 0.0


def shards(env_dir: Path, kind: str):
    for f in sorted(env_dir.glob(f"{kind}-*.jsonl")):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)


def header_name(path: Path):
    """The item name a Lean file's provenance header gives (`-- name    : <name>`), if any."""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for _, line in zip(range(12), fh):
            m = NAME_HEADER.match(line)
            if m:
                return m.group(1)
            if not line.startswith("--"):
                break
    return None


def lean_imports(path: Path):
    """Modules imported by a Lean file (imports precede every other command)."""
    out, depth = [], 0
    # newline="\n": a bare \r inside a header comment is not a line break to Lean
    with path.open(encoding="utf-8", errors="replace", newline="\n") as fh:
        for line in fh:
            s = line.strip()
            if depth:
                depth += s.count("/-") - s.count("-/")
                continue
            if not s or s.startswith("--") or s == "module":
                continue
            if s.startswith("/-"):
                depth = s.count("/-") - s.count("-/")
                continue
            m = IMPORT.match(s)
            if not m:
                break
            out.append(m.group(1))
    return out


class Graph:
    def __init__(self):
        self.nodes = {}                 # (env, module) -> {"name","kind","status","id","original"}
        self.by_name = {}               # (env, theorem_name) -> key
        self.by_id = {}                 # theorem id -> key
        self.edges = {}                 # (parent key, child key) -> {"via": set, "original": bool}
        self.problems = []              # (file or row, what is wrong with it); a submission with any is rejected
        self.default_env = None
        self.base_solutions = set()     # (env, file name) of every solution file in the dataset
        self.dead = {}                  # deprecated node -> the node its manifest row names as replacement, or None
        self.sub_solved = Counter()     # node -> solution files the submission ships for it
        self.row_edges = 0              # submission edges declared in graph rows, not read from Lean files

    # ---- loading -------------------------------------------------------
    def add_node(self, env, module, name=None, original=False, row=None):
        key = (env, module)
        if key not in self.nodes:
            row = row or {}
            self.nodes[key] = {
                "name": name or module.split(".", 1)[-1],
                "kind": "definition" if module.startswith("Definitions.") else "theorem",
                "status": row.get("status"),
                "id": row.get("id"),
                "original": original,
                "sol_lines": [s.get("lean_lines", 0) for s in row.get("solutions", [])],
            }
            self.by_name.setdefault((env, self.nodes[key]["name"]), key)
            if row.get("id"):
                self.by_id[row["id"]] = key
        return key

    def add_edge(self, parent, child, via, original=False):
        if parent == child:
            return
        e = self.edges.setdefault((parent, child), {"via": set(), "original": original})
        e["via"].update(via)

    def resolve(self, env, ref):
        """A graph row names its endpoints by theorem_name; accept a module too."""
        return self.by_name.get((env, ref)) or ((env, ref) if (env, ref) in self.nodes else None)

    def load_base(self, data: Path):
        man = data / "MANIFEST.json"
        if man.is_file():
            for e in json.loads(man.read_text())["environments"]:
                if e.get("is_default"):
                    self.default_env = e["dir"]
        for env_dir in sorted((data / "envs").iterdir()):
            env = env_dir.name
            for r in shards(env_dir, "index"):
                self.add_node(env, r["module"], r["theorem_name"], original=True, row=r)
                self.base_solutions.update((env, Path(x["path"]).name) for x in r.get("solutions", []))
            for e in shards(env_dir, "graph"):
                p, c = self.resolve(env, e["parent"]), self.resolve(env, e["child"])
                if p is None or c is None:
                    sys.exit(f"{env}: graph row {e} names an item with no index row")
                self.add_edge(p, c, e.get("via", []), original=True)
        if self.default_env is None:
            self.default_env = Counter(k[0] for k in self.nodes).most_common(1)[0][0]

    def load_submission(self, sub: Path):
        envs = sub / "envs"
        if not envs.is_dir():
            sys.exit(f"{sub}: expected an envs/<env>/ directory (see --help)")
        bad = self.problems.append
        if not (sub / "README.md").is_file():
            bad((str(sub), "no README.md describing the method"))
        known_envs = {k[0] for k in self.nodes}
        placed = set()
        for env_dir in sorted(p for p in envs.iterdir() if p.is_dir()):
            env = env_dir.name
            if env not in known_envs:
                sys.exit(f"{sub}: environment {env!r} is not in the dataset; "
                         f"edges cannot cross environments (have: {sorted(known_envs)})")
            # pass 1: nodes
            for r in shards(env_dir, "index"):
                self.add_node(env, r.get("module") or r["theorem_name"], r.get("theorem_name"), row=r)
            stmt_files = []
            for d, prefix in (("Theorems", "Thm_"), ("Definitions", "Def_")):
                for f in sorted((env_dir / d).glob("*.lean")):
                    placed.add(f)
                    key = (env, f"{d}.{f.stem}")
                    if not f.stem.startswith(prefix):
                        bad((str(f), f"files in {d}/ are named {prefix}*.lean"))
                    elif key in self.nodes and self.nodes[key]["original"]:
                        bad((str(f), "this file is in the base snapshot; published files are immutable, "
                                     "so add a new node under a new name"))
                    else:
                        self.add_node(env, key[1], header_name(f))
                        stmt_files.append((f, key))
            # pass 2: edges
            for f, key in stmt_files:
                self._imports(env, f, key, "statement")
            for f in sorted((env_dir / "Solutions").glob("*.lean")):
                placed.add(f)
                if (env, f.name) in self.base_solutions:
                    bad((str(f), "this file is in the base snapshot; published solutions are immutable, "
                                 "so ship a new proof as Sol_<slug>_<n>.lean with a free <n>"))
                    continue
                parent = self._solution_parent(env, f) if f.stem.startswith("Sol_") else None
                if parent is None:
                    bad((str(f), "no theorem for this solution file (expected Sol_<slug>.lean or "
                                 "Sol_<slug>_<n>.lean for Theorems/Thm_<slug>.lean)"))
                    continue
                self.sub_solved[parent] += 1
                self._imports(env, f, parent, "solution")
            for e in shards(env_dir, "graph"):
                p, c = self.resolve(env, e["parent"]), self.resolve(env, e["child"])
                if p is None or c is None:
                    bad((f"{env} graph row", f"{e['parent']} -> {e['child']} names an unknown item"))
                    continue
                self.row_edges += (p, c) not in self.edges
                self.add_edge(p, c, e.get("via", ["statement"]))
        for f in sorted(sub.rglob("*.lean")):
            if f not in placed:
                bad((str(f), "Lean files go in envs/<env>/Definitions, Theorems or Solutions"))
        self._manifest(sub / "manifest.jsonl")

    def _manifest(self, path: Path):
        """Deprecations: one JSON object per line, {"deprecate": node, "replaced_by": node, "reason": text}.
        A node is named by its theorem name or its module; "env" defaults to the default environment."""
        if not path.is_file():
            return
        rows = []
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            where = f"{path}:{i}"
            try:
                row = json.loads(line)
            except ValueError as err:
                self.problems.append((where, f"not a JSON object ({err})"))
                continue
            if not isinstance(row, dict) or not isinstance(row.get("deprecate"), str):
                self.problems.append((where, 'expected {"deprecate": "<node>", "replaced_by": "<node>", "reason": "..."}'))
                continue
            env = row.get("env") or self.default_env
            d = self.resolve(env, row["deprecate"])
            if d is None or not self.nodes[d]["original"]:
                self.problems.append((where, f"deprecate: {row['deprecate']!r} is not a node of the base snapshot in {env}"))
                continue
            r = None
            if row.get("replaced_by"):
                r = self.resolve(env, row["replaced_by"])
                if r is None:
                    self.problems.append((where, f"replaced_by: {row['replaced_by']!r} is not a node in {env}"))
                    continue
            self.dead[d] = r
            rows.append((where, row, r))
        for where, row, r in rows:
            if r in self.dead:
                self.problems.append((where, f"replaced_by: {row['replaced_by']!r} is itself deprecated"))

    def _imports(self, env, f, parent, via):
        for mod in lean_imports(f):
            if mod.startswith(LOCAL):
                if (env, mod) == parent:
                    self.problems.append((str(f), f"import {mod}: a proof cannot import the theorem it proves"))
                elif (env, mod) in self.nodes:
                    self.add_edge(parent, (env, mod), [via])
                else:
                    self.problems.append((str(f), f"import {mod}: no such module in the dataset or the submission"))

    def _solution_parent(self, env, f):
        with f.open(encoding="utf-8", errors="replace") as fh:
            m = SOL_HEADER.match(fh.readline())
        if m and (env, m.group(1)) in self.by_name:
            return self.by_name[(env, m.group(1))]
        slug = f.stem[len("Sol_"):] if f.stem.startswith("Sol_") else f.stem
        for s in (slug, re.sub(r"_\d+$", "", slug)):
            if (env, f"Theorems.Thm_{s}") in self.nodes:
                return (env, f"Theorems.Thm_{s}")
        return None

    # ---- metrics -------------------------------------------------------
    def components(self, original_edges_only=False, dead=()):
        """Weak components of the graph without the `dead` nodes. Returns find() over all nodes."""
        par = {k: k for k in self.nodes}

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x

        for (p, c), e in self.edges.items():
            if (original_edges_only and not e["original"]) or p in dead or c in dead:
                continue
            a, b = find(p), find(c)
            if a != b:
                par[a] = b
        return find

    def connectivity(self, find, env=None, dead=()):
        """Component stats counted over ORIGINAL nodes only (new nodes are bridges), minus the `dead` ones."""
        orig = [k for k, n in self.nodes.items()
                if n["original"] and (env is None or k[0] == env) and k not in dead]
        sizes = sorted(Counter(find(k) for k in orig).values(), reverse=True)
        n = len(orig)
        return {
            "original_nodes": n,
            "components": len(sizes),
            "singletons": sum(1 for s in sizes if s == 1),
            "largest": sizes[0] if sizes else 0,
            "largest_share": sizes[0] / n if n else 0.0,
            # chance that two distinct original nodes drawn at random are connected
            "pair_connectivity": pair_conn(sizes, n),
            "top_sizes": sizes[:10],
        }

    def children(self, original_edges_only=False, dead=()):
        ch = defaultdict(list)
        for (p, c), e in self.edges.items():
            if not (original_edges_only and not e["original"]) and p not in dead and c not in dead:
                ch[p].append(c)
        return ch

    def missions(self, seeds, find, ch, members=None, dead=()):
        """Mission metrics. A mission whose goal is `dead` is not scored; nor is a dead member one of its items."""
        ms = seeds["missions"]
        live = {i: k for i, k in self.by_id.items() if k not in dead}
        roots = {}                              # mission id -> its own items (goal, plus members if given)
        for m in ms:
            ks = {live[t] for t in (members or {}).get(m["id"], ()) if t in live}
            if m.get("goal") in live:
                ks.add(live[m["goal"]])
            elif m.get("goal") in self.by_id:
                continue
            if ks:
                roots[m["id"]] = ks
        work = {m["id"]: work_of(m) for m in ms}
        out = {"missions": len(ms), "missions_scored": len(roots),
               "works": len({work[m] for m in roots}), "cone_from": "members" if members else "goal"}
        if not roots:
            return out
        n = len(roots)
        goals = [live[m["goal"]] for m in ms if m.get("goal") in live]
        gcomp = Counter(find(k) for k in goals)
        out["goal_components"] = len(gcomp)
        out["mission_pair_connectivity"] = pair_conn(gcomp.values(), len(goals))

        cones = {}
        for mid, ks in roots.items():
            seen, stack = set(ks), list(ks)
            while stack:
                for c in ch.get(stack.pop(), ()):
                    if c not in seen:
                        seen.add(c)
                        stack.append(c)
            cones[mid] = seen
        owners = defaultdict(set)               # node -> missions it is an item of
        for mid, ks in roots.items():
            for k in ks:
                owners[k].add(mid)
        m_users, w_users = defaultdict(set), defaultdict(set)   # node -> missions / works depending on it
        for mid, cone in cones.items():
            for v in cone:
                m_users[v].add(mid)
                w_users[v].add(work[mid])
        direct = direct_x = shared = shared_x = 0
        for mid, cone in cones.items():
            others = {o for v in cone - roots[mid] for o in owners.get(v, ())}
            direct += bool(others)
            direct_x += any(work[o] != work[mid] for o in others)
            shared += any(len(m_users[v]) > 1 for v in cone)
            shared_x += any(len(w_users[v]) > 1 for v in cone)
        out["direct_reuse"] = direct / n              # depends on another mission's own item
        out["direct_reuse_cross_work"] = direct_x / n
        out["shared_dependency"] = shared / n         # shares a dependency with another mission
        out["S_reuse"] = shared_x / n                 # ... with a mission of a different work
        return out


def pct(x):
    return f"{100 * x:.2f}%"


def cmd_stats(a):
    g = Graph()
    g.load_base(Path(a.data))
    find, ch = g.components(), g.children()
    res = {"default_env": g.default_env, "environments": {}}
    for env in sorted({k[0] for k in g.nodes}):
        ns = [n for k, n in g.nodes.items() if k[0] == env]
        es = [(p, c, e) for (p, c), e in g.edges.items() if p[0] == env]
        res["environments"][env] = {
            "theorems": sum(n["kind"] == "theorem" for n in ns),
            "definitions": sum(n["kind"] == "definition" for n in ns),
            "status": dict(Counter(n["status"] for n in ns)),
            "edges": len(es),
            "edges_by_kind": dict(Counter(
                f"{g.nodes[p]['kind']}->{g.nodes[c]['kind']}" for p, c, _ in es)),
            "edges_by_via": dict(Counter("+".join(sorted(e["via"])) for _, _, e in es)),
            **g.connectivity(find, env),
        }
    indeg = Counter(c for (_, c) in g.edges)
    res["hubs"] = [{"env": k[0], "name": g.nodes[k]["name"], "kind": g.nodes[k]["kind"], "in_degree": d}
                   for k, d in indeg.most_common(a.top)]
    lines = sorted(x for n in g.nodes.values() for x in n["sol_lines"])
    if lines:
        q = lambda p: lines[min(len(lines) - 1, int(p * len(lines)))]
        res["solutions"] = {"count": len(lines), "median_lines": q(.5), "p90": q(.9), "p99": q(.99),
                            "max": lines[-1], "over_500": sum(x > 500 for x in lines),
                            "over_1000": sum(x > 1000 for x in lines)}
    seeds = load_seeds(a)
    if seeds:
        res["missions"] = g.missions(seeds, find, ch, load_members(a))
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return
    for env, r in res["environments"].items():
        tag = "  (default)" if env == g.default_env else ""
        print(f"== env {env}{tag}")
        print(f"   nodes {r['original_nodes']:,} = {r['theorems']:,} theorems + {r['definitions']:,} definition files"
              f"   status {r['status']}")
        print(f"   edges {r['edges']:,}   by kind {r['edges_by_kind']}   by via {r['edges_by_via']}")
        print(f"   weak components k0 = {r['components']:,}   singletons {r['singletons']:,}"
              f"   largest {r['largest']:,} ({pct(r['largest_share'])})   top {r['top_sizes']}")
        print(f"   pair connectivity {pct(r['pair_connectivity'])}")
    print("== hubs (in-degree)")
    for h in res["hubs"]:
        print(f"   {h['in_degree']:>6,}  {h['kind']:<10} {h['name']}  [{h['env']}]")
    if "solutions" in res:
        print(f"== solutions {res['solutions']}")
    if "missions" in res:
        print_missions(res["missions"])


def print_missions(m, prefix="== missions "):
    print(f"{prefix}{m['missions']:,}; scored {m['missions_scored']:,} in {m['works']:,} source works"
          f" (cone from {m['cone_from']})")
    if "S_reuse" not in m:
        return
    print(f"   S_reuse {pct(m['S_reuse'])}  shares a dependency with a mission of another work"
          f"   (with any other mission: {pct(m['shared_dependency'])})")
    print(f"   direct reuse {pct(m['direct_reuse_cross_work'])}  depends on an item of a mission of another work"
          f"   (of any other mission: {pct(m['direct_reuse'])})")
    print(f"   mission pair connectivity {pct(m['mission_pair_connectivity'])}"
          f"   components containing a goal {m['goal_components']:,}")


def load_seeds(a):
    p = Path(a.seeds) if a.seeds else Path(a.data) / "seeds.json"
    return json.loads(p.read_text()) if p.is_file() else None


def load_members(a):
    return json.loads(Path(a.members).read_text()) if a.members else None


def cmd_score(a):
    g = Graph()
    g.load_base(Path(a.data))
    for s in a.submission:
        g.load_submission(Path(s))
    env = a.env or g.default_env
    dead = set(g.dead)
    f0, f1 = g.components(original_edges_only=True), g.components(dead=dead)
    seeds, members = load_seeds(a), load_members(a)

    new_nodes = [k for k, n in g.nodes.items() if not n["original"]]
    new_edges = [(p, c) for (p, c), e in g.edges.items() if not e["original"]]
    kinds = Counter(("orig" if g.nodes[p]["original"] else "new") + "->" +
                    ("orig" if g.nodes[c]["original"] else "new") for p, c in new_edges)
    # how many base components does each new node touch directly? One node that
    # imports a member of every component maximises the score and means nothing.
    touch = defaultdict(set)
    for p, c in new_edges:
        for x, y in ((p, c), (c, p)):
            if not g.nodes[x]["original"] and g.nodes[y]["original"]:
                touch[x].add(f0(y))
    fan = sorted(((len(v), g.nodes[k]["name"], k[0]) for k, v in touch.items()), reverse=True)[:a.top]
    used = {x for e in new_edges for x in e}
    kind = lambda ks, what: sum(g.nodes[k]["kind"] == what for k in ks)

    res = {"env": env, "submission": a.submission, "per_env": {},
           "problems": [{"where": w, "what": x} for w, x in g.problems],
           "added": {"nodes": len(new_nodes), "definitions": kind(new_nodes, "definition"),
                     "theorems": kind(new_nodes, "theorem"),
                     # new theorems the submission ships no proof for: Open problems it leaves behind
                     "theorems_without_solution": sum(g.nodes[k]["kind"] == "theorem" and not g.sub_solved[k]
                                                      for k in new_nodes),
                     "solutions_for_original_theorems": sum(n for k, n in g.sub_solved.items()
                                                            if g.nodes[k]["original"]),
                     "edges": len(new_edges), "edges_by_kind": dict(kinds),
                     "edges_from_graph_rows": g.row_edges,
                     "nodes_without_edges": sum(k not in used for k in new_nodes)},
           "deprecated": {"nodes": len(dead), "definitions": kind(dead, "definition"),
                          "theorems": kind(dead, "theorem"),
                          "with_replacement": sum(r is not None for r in g.dead.values()),
                          "list": [{"env": d[0], "name": g.nodes[d]["name"],
                                    "replaced_by": g.nodes[r]["name"] if r else None}
                                   for d, r in sorted(g.dead.items())]},
           "largest_fan": [{"base_components_touched": n, "name": nm, "env": e} for n, nm, e in fan]}
    res["net_definitions"] = res["added"]["definitions"] - res["deprecated"]["definitions"]
    for e in sorted({k[0] for k in g.nodes}):
        b, s = g.connectivity(f0, e), g.connectivity(f1, e, dead)
        k0, k1 = b["components"], s["components"]
        p0, p1 = b["pair_connectivity"], s["pair_connectivity"]
        res["per_env"][e] = {"base": b, "submission": s, "delta_conn": k0 - k1,
                             "S_conn": (k0 - k1) / (k0 - 1) if k0 > 1 else 0.0,
                             "pair_gain": p1 - p0, "S_pair": (p1 - p0) / (1 - p0) if p0 < 1 else 0.0}
    if seeds:
        res["missions"] = {"base": g.missions(seeds, f0, g.children(True), members),
                           "submission": g.missions(seeds, f1, g.children(dead=dead), members, dead)}
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif a.markdown:
        print(markdown_report(res))
    else:
        r, ad, dp = res["per_env"][env], res["added"], res["deprecated"]
        b, s = r["base"], r["submission"]
        num = lambda v: f"{v:,}"
        print(f"env {env}: {b['original_nodes']:,} original nodes; submission adds {ad['nodes']:,} nodes"
              f" ({ad['definitions']:,} definition files, {ad['theorems']:,} theorems,"
              f" {ad['theorems_without_solution']:,} of them without a proof),"
              f" {ad['solutions_for_original_theorems']:,} new proofs of original theorems,"
              f" {ad['edges']:,} edges {ad['edges_by_kind']}")
        if ad["edges_from_graph_rows"]:
            print(f"  {ad['edges_from_graph_rows']:,} of the edges are declared in graph rows; no Lean file backs them")
        print(f"  deprecates {dp['nodes']:,} nodes ({dp['definitions']:,} definition files, {dp['theorems']:,} theorems;"
              f" {dp['with_replacement']:,} name a replacement); net definition files {res['net_definitions']:+,}")
        print(f"  {'':<27}{'base':>10}{'submission':>12}")

        def row(name, x, y, f=num, note=""):
            print(f"  {name:<27}{f(x):>10}{f(y):>12}   {note}".rstrip())

        row("pair connectivity", b["pair_connectivity"], s["pair_connectivity"], pct,
            f"gain {100 * r['pair_gain']:+.3g} pt, S_pair {r['S_pair']:.4g}")
        if seeds and "S_reuse" in res["missions"]["base"]:
            mb, msub = res["missions"]["base"], res["missions"]["submission"]
            row("S_reuse", mb["S_reuse"], msub["S_reuse"], pct,
                f"{msub['missions_scored']:,} missions in {msub['works']:,} works, cone from {mb['cone_from']}")
            row("direct reuse", mb["direct_reuse_cross_work"], msub["direct_reuse_cross_work"], pct)
            row("mission pair connectivity", mb["mission_pair_connectivity"], msub["mission_pair_connectivity"], pct)
        row("counted nodes", b["original_nodes"], s["original_nodes"], num, "original nodes that are not deprecated")
        row("components", b["components"], s["components"], num,
            f"delta_conn {r['delta_conn']:,}, S_conn {r['S_conn']:.4g}")
        row("isolated nodes", b["singletons"], s["singletons"])
        row("largest component", b["largest"], s["largest"])
        if fan:
            print("  new nodes touching the most base components directly:")
            for n, nm, e in fan:
                print(f"    {n:>5}  {nm}  [{e}]")
    if g.problems and not (a.json or a.markdown):
        for where, what in g.problems[:50]:
            print(f"  PROBLEM {where}: {what}", file=sys.stderr)
    if g.problems:
        sys.exit(f"{len(g.problems)} problem(s) in the submission; fix them before the score counts")


def markdown_report(res):
    """The score as a GitHub comment. Names and paths come from the submission, so they are
    stripped of what could end a code span or notify someone."""
    safe = lambda s: str(s).replace("`", "'").replace("@", "(at)")
    r, ad, dp = res["per_env"][res["env"]], res["added"], res["deprecated"]
    b, s = r["base"], r["submission"]
    out = [f"### Graph-refinement score: `{'`, `'.join(map(safe, res['submission']))}`", ""]
    if res["problems"]:
        out += [f"**{len(res['problems'])} problem(s). The numbers below do not count until they are fixed.**", ""]
        out += [f"- `{safe(p['where'])}`: {safe(p['what'])}" for p in res["problems"][:50]] + [""]
    out += [f"Environment `{res['env']}`, against the base snapshot `v0`.", "",
            "| | base | submission | change |", "|---|---:|---:|---:|"]

    def row(name, x, y, f=pct, change=None):
        d = change if change is not None else (f"{100 * (y - x):+.3f} pt" if f is pct else f"{y - x:+,}")
        out.append(f"| {name} | {f(x)} | {f(y)} | {d} |")

    num = lambda v: f"{v:,}"
    row("**Pair connectivity**", b["pair_connectivity"], s["pair_connectivity"])
    m = res.get("missions")
    if m and "S_reuse" in m["base"] and "S_reuse" in m["submission"]:
        row("**S_reuse** (cross-work reuse)", m["base"]["S_reuse"], m["submission"]["S_reuse"])
        row("Direct reuse", m["base"]["direct_reuse_cross_work"], m["submission"]["direct_reuse_cross_work"])
        row("Mission pair connectivity", m["base"]["mission_pair_connectivity"],
            m["submission"]["mission_pair_connectivity"])
        row("Missions scored", m["base"]["missions_scored"], m["submission"]["missions_scored"], num)
    row("Counted nodes (original, not deprecated)", b["original_nodes"], s["original_nodes"], num)
    row("Weak components", b["components"], s["components"], num)
    row("Isolated nodes", b["singletons"], s["singletons"], num)
    row("Largest component", b["largest"], s["largest"], num)
    out += ["", f"`S_pair` = {r['S_pair']:.4g} (share of the missing pair connectivity that was gained)", "",
            "| Cost | |", "|---|---:|",
            f"| New definition files | {ad['definitions']:,} |",
            f"| New theorems | {ad['theorems']:,} ({ad['theorems_without_solution']:,} without a proof) |",
            f"| New proofs of original theorems | {ad['solutions_for_original_theorems']:,} |",
            f"| New import edges | {ad['edges']:,} |",
            f"| Deprecated nodes | {dp['nodes']:,} ({dp['definitions']:,} definition files, {dp['theorems']:,} theorems) |",
            f"| **Net definition files** (new minus deprecated) | {res['net_definitions']:+,} |"]
    if ad["edges_from_graph_rows"]:
        out += ["", f"{ad['edges_from_graph_rows']:,} of the new edges are declared in graph rows; no Lean file backs them."]
    if res["largest_fan"]:
        out += ["", "New nodes that touch the most base components directly:", ""]
        out += [f"- `{safe(f['name'])}`: {f['base_components_touched']:,}" for f in res["largest_fan"][:5]]
    out += ["", "The scorer reads `import` lines. It does not compile the Lean files."]
    return "\n".join(out)


def cmd_probe(a):
    g = Graph()
    data = Path(a.data)
    g.load_base(data)
    env = a.env or g.default_env
    find = g.components()
    rx = re.compile(a.pattern, re.I)
    want = {"definitions": ("definition",), "theorems": ("theorem",), "all": ("definition", "theorem")}[a.where]
    keys = [k for k in g.nodes if k[0] == env]
    hits = defaultdict(list)                    # component -> matching nodes
    for k in keys:
        if g.nodes[k]["kind"] not in want:
            continue
        f = data / "envs" / env / (k[1].replace(".", "/", 1) + ".lean")
        if f.is_file() and rx.search(f.read_text(encoding="utf-8", errors="replace")):
            hits[find(k)].append(k)
    size = Counter(find(k) for k in keys)
    n, sizes = len(keys), sorted(size.values(), reverse=True)
    merged = sum(size[c] for c in hits)
    after = [merged] + [s for c, s in size.items() if c not in hits] if hits else sizes
    p0, p1 = pair_conn(sizes, n), pair_conn(after, n)
    res = {"env": env, "pattern": a.pattern, "where": a.where,
           "files": sum(map(len, hits.values())), "components_touched": len(hits),
           "if_all_joined": {"delta_conn": max(len(hits) - 1, 0), "nodes_joined": merged,
                             "pair_connectivity": p1, "pair_gain": p1 - p0},
           "components": [{"size": size[c], "matches": len(ks),
                           "examples": [g.nodes[k]["name"] for k in sorted(ks)[:a.examples]]}
                          for c, ks in sorted(hits.items(), key=lambda t: -size[t[0]])[:a.top]]}
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return
    j = res["if_all_joined"]
    print(f"env {env}: /{a.pattern}/ in {a.where}: {res['files']:,} files in {res['components_touched']:,} components")
    print(f"  if all of them were joined: delta_conn {j['delta_conn']:,}, {j['nodes_joined']:,} nodes in one component,"
          f" pair connectivity {pct(p0)} -> {pct(p1)} ({100 * j['pair_gain']:+.2f} pt)")
    print("  largest components touched (size, matching files, examples):")
    for c in res["components"]:
        print(f"    {c['size']:>6,} {c['matches']:>5,}  {', '.join(c['examples'])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("stats", "score", "probe"):
        p = sub.add_parser(name)
        p.add_argument("--data", default=str(REPO), help="the subset directory, holding envs/, MANIFEST.json "
                       "and seeds.json (default: the repository this script is in)")
        p.add_argument("--seeds", help="seeds.json (default: <data>/seeds.json)")
        p.add_argument("--members", help="JSON {mission_id: [theorem ids]} for the real reuse metric")
        p.add_argument("--top", type=int, default=10)
        p.add_argument("--json", action="store_true")
        if name != "stats":
            p.add_argument("--env", help="environment to report (default: the dataset's default)")
        if name == "score":
            p.add_argument("--submission", required=True, nargs="+", help="overlay directory (or several)")
            p.add_argument("--markdown", action="store_true", help="print the score as a GitHub comment")
        if name == "probe":
            p.add_argument("--pattern", required=True, help="case-insensitive regex over the Lean files' text")
            p.add_argument("--where", choices=("definitions", "theorems", "all"), default="definitions")
            p.add_argument("--examples", type=int, default=3)
    a = ap.parse_args()
    if not (Path(a.data) / "envs").is_dir():
        sys.exit(f"{a.data}: no envs/ directory here; pass --data <subset directory>")
    {"stats": cmd_stats, "score": cmd_score, "probe": cmd_probe}[a.cmd](a)
