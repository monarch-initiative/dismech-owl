# CLAUDE.md

OWL builds of the dismech knowledge base. Read `README.md` first; it describes
what the TBox contains and how it is built.

- The only input is a dismech checkout (`../dismech`, or `$DISMECH_DIR`) at the
  commit in `DISMECH_REF`. It supplies both the `dismech` package and `kb/`.
  Do not re-implement anything dismech already defines (the graph's node set
  and edges, the node-class tree grammar, the ModifierEnum vocabulary). Import
  it, so this build follows dismech when dismech changes.
- Never write an ontology CURIE from memory. dismech's rule applies here: every
  identifier comes from a lookup, or the axiom is left out. This is why object
  properties are still in the dismech namespace rather than RO.
- Large outputs go in `build/` (gitignored); they are release assets, not
  repository content.
- `just test` and `just lint` before pushing. `just tbox-sample` then
  `just reason` is the fast end-to-end check; `just tbox` is the full build
  (about 3 minutes, about 200 MB).
