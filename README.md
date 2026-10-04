# dismech-owl

OWL builds of the [dismech](https://github.com/monarch-initiative/dismech)
disorder mechanisms knowledge base.

The first build is a **pathograph TBox**. Every node in every dismech causal
graph (pathophysiology, phenotype, treatment, gene, exposure, biomarker and
model nodes) becomes an OWL class with its own IRI. The pathophysiology nodes
are placed under dismech's candidate node-class tree
(`kb/node_classes/pathograph_node_classes.txt`).

## Input: a pinned dismech checkout

The build reads one dismech checkout. That checkout supplies two things: the
`dismech` Python package, which provides the graph builder and the tree
parser, and its `kb/`, which provides the data. Because both come from the same
checkout, the code can never be a different version from the data.

`DISMECH_REF` pins the commit. The ontology's version IRI and its
`dcterms:source` record that commit.

```bash
just fetch-dismech      # clone dismech at DISMECH_REF into ../dismech
just install            # uv sync (dismech is an editable path dependency)
just test
just tbox-sample        # a few entries, seconds
just tbox               # the whole KB, ~1 min, ~200 MB OFN
just reason             # merge GO and MONDO modules and classify with ELK (needs Java)
just example            # the sample docs/exploring.md is written against
just release            # what the weekly workflow runs: tbox + reason + dist
just pin-dismech        # repin DISMECH_REF to ../dismech's HEAD
```

Set `DISMECH_DIR` to use a checkout somewhere other than `../dismech`. The
`[tool.uv.sources]` path in `pyproject.toml` assumes `../dismech` too.

## Releases

A [weekly workflow](.github/workflows/release.yaml) (Mondays, 10:41 UTC)
resolves dismech `main` to an exact commit, runs the tests against it, and runs
`just release`. That builds the full TBox, reasons over it with GO and MONDO
modules, and packages the result into `build/dist/`. Each run publishes a
GitHub release tagged `vYYYY-MM-DD` with:

| Asset | Contents |
|---|---|
| `dismech-pathograph.ofn.gz` | the TBox as built (about 21 MB gzipped, 200 MB unpacked) |
| `dismech-pathograph-reasoned.ofn.gz` | merged with GO and MONDO modules and classified with ELK (about 25 MB / 280 MB) |
| `manifest.json` | the dismech and dismech-owl commits, build counts, file sizes and sha256s |

The same files are kept as a workflow artifact for 90 days. A week in which
neither dismech nor dismech-owl changed publishes no release. A manual run
(Actions → Weekly release → Run workflow) defaults to a dry run that only
uploads the artifact. Its inputs pick a dismech ref, publish for real, or force
a release over an identical one.

Releases track dismech `main`. `DISMECH_REF` pins only what CI tests against.

## What the TBox contains

| Source in dismech | OWL |
|---|---|
| node-class tree class | class under `dismech:PathophysiologyNode`; gloss as `skos:definition` |
| tree `= expression` | `<expression> SubClassOf <tree class>` (a sufficient condition, as the tree grammar defines it) |
| tree worked example `[Entry] Node` | `<node> SubClassOf <tree class>` |
| any graph node | class `…/node/<entry>/<kind>/<slug>`, under `dismech:<Kind>Node`; entry's MONDO term as `dcterms:isPartOf` |
| pathophysiology descriptor | `<node> SubClassOf <slot> some (<term> and modifier value <M>)` |
| `conforms_to: module#Node` | `<node> SubClassOf <module node>` |
| phenotype / exposure / treatment term | `<node> SubClassOf <HP / ECTO / NCIT term>` |
| gene / biomarker term | `<node> SubClassOf gene_term some …` / `biomarker_term some …` |
| graph edge (`causes`, `treats`, `models` …) | `<source> SubClassOf <predicate> some <target>`; `causes` and `leads_to` are sub-properties of RO 'causally upstream of' |
| the entry's MONDO disease term | pathophysiology node `SubClassOf RO:0003302 some <disease>`; phenotype node `SubClassOf RO:0002201 some <disease>` |
| `--scan` (off by default) | the node-class scanner's candidate tier, asserted |

Node IRIs are stable as long as the entry slug and node name are stable.
A slug collision inside one entry gets `_2`, `_3` in file order.

## Browsing it with OAK

OAK is a dependency, and reads the OFN build through its py-horned-owl backed
`funowl:` adapter:

```bash
runoak -i funowl:build/bmf-reasoned.ofn tree -p i,RO:0003302 \
  dismech:node/Fanconi_Anemia/pathophysiology/Homologous_Recombination_Impairment
```

[`docs/exploring.md`](docs/exploring.md) walks through is-a, the non-is-a
edges, causal chains, `viz` and the path from a mechanism back to its disease
and up MONDO's classification, with real output.

## Classification by reasoning

dismech's node-class tree supplies the upper hierarchy, its worked examples are
asserted, and its logical definitions become axioms a reasoner can use. On the
full KB, 2,378 of 23,853 pathophysiology nodes have an asserted tree class;
after `just reason` merges GO and MONDO modules and runs ELK (about 3 minutes),
10,497 (44%) do, and 1,839 land in two or more tiers. Details and limits are in
[`docs/exploring.md`](docs/exploring.md#classification-by-the-tree-definitions).

## Known limitations

- Most object properties are in the dismech namespace. Only the disease links
  and the `causes` / `leads_to` sub-property axioms use RO so far; each RO term
  was looked up with `runoak -i sqlite:obo:ro`.
- External ontologies are referenced, not imported. `just reason` merges GO and
  MONDO BOT modules; HP, CL and UBERON are not merged yet.
- OAK's label search (`l~…`) is very slow on this adapter. Query by CURIE.
- py-horned-owl must be 2.0 or later. The 1.4 functional-syntax writer panics
  on a literal that contains a `"` followed later by a multi-byte character,
  and dismech descriptions contain such literals.
- `some UBERON`-style atoms in tree definitions use a placeholder class
  ("any UBERON term") rather than an ontology root.
