"""Tests for the pathograph TBox builder."""

from __future__ import annotations

import re
from pathlib import Path

import pyhornedowl
import pytest

from dismech_owl.tbox import BASE, TREE_PATH, build, default_dismech_dir, main, node_class_iri

TREE = """\
CELLULAR EFFECT
  cell death -- the cell is lost
    = biological_processes some GO:0008219 'cell death'
    [Toy_Disease] Neuronal Death
TISSUE / ORGAN EFFECT
  inflammation
    = biological_processes some GO:0006954 'inflammatory response' modifier INCREASED and locations some UBERON
"""

MODULE = """\
name: toy_module
pathophysiology:
- name: Cell Loss
"""

DISEASE = """\
name: Toy Disease
disease_term:
  term:
    id: MONDO:0000001
    label: disease
pathophysiology:
- name: Neuronal Death
  conforms_to: "toy_module#Cell Loss"
  biological_processes:
  - preferred_term: cell death
    term:
      id: GO:0008219
      label: cell death
    modifier: INCREASED
  downstream:
  - target: Seizures
  - target: Nothing By This Name
phenotypes:
- name: Seizures
  phenotype_term:
    term:
      id: HP:0001250
      label: Seizure
"""


TREATMENT = """\
treatments:
- name: Antiseizure Medication
  treatment_term:
    preferred_term: Pharmacotherapy
    term:
      id: NCIT:C15986
      label: Pharmacotherapy
  target_phenotypes:
  - preferred_term: Seizure
    term:
      id: HP:0001250
      label: Seizure
"""


@pytest.fixture
def toy_kb(tmp_path: Path) -> tuple[Path, Path]:
    disorders = tmp_path / "disorders"
    modules = tmp_path / "modules"
    disorders.mkdir()
    modules.mkdir()
    (disorders / "Toy_Disease.yaml").write_text(DISEASE)
    (modules / "toy_module.yaml").write_text(MODULE)
    tree = tmp_path / "tree.txt"
    tree.write_text(TREE)
    return tree, tmp_path


def expand(ofn: str) -> str:
    """Rewrite every prefixed name as a full ``<IRI>``.

    Which IRIs the OFN writer abbreviates is a writer decision that changed
    between py-horned-owl 1.4 and 2.0, so assertions compare full IRIs.
    """
    prefixes = dict(re.findall(r"^Prefix\((\w*):=<([^>]*)>\)", ofn, re.MULTILINE))
    pattern = re.compile(r"(?<![<\w\"])(" + "|".join(map(re.escape, prefixes)) + r"):([^\s()\"]+)")
    return pattern.sub(lambda m: f"<{prefixes[m.group(1)]}{m.group(2)}>", ofn)


def _ofn(tree: Path, root: Path):
    builder = build(tree, [root / "disorders", root / "modules"])
    return builder, expand(builder.onto.save_to_string("ofn"))


D = "https://w3id.org/monarch-initiative/dismech/"
OBO = "http://purl.obolibrary.org/obo/"


def test_every_node_gets_its_own_iri(toy_kb):
    tree, root = toy_kb
    builder, _ = _ofn(tree, root)
    classes = {str(c) for c in builder.onto.get_classes()}
    assert f"{BASE}node/Toy_Disease/pathophysiology/Neuronal_Death" in classes
    assert f"{BASE}node/Toy_Disease/phenotype/Seizures" in classes
    assert f"{BASE}node/toy_module/pathophysiology/Cell_Loss" in classes


def test_node_axioms(toy_kb):
    tree, root = toy_kb
    builder, ofn = _ofn(tree, root)
    death = f"{BASE}node/Toy_Disease/pathophysiology/Neuronal_Death"
    # descriptor existential, narrowed by the modifier individual
    assert (
        f"SubClassOf(<{D}node/Toy_Disease/pathophysiology/Neuronal_Death> "
        f"ObjectSomeValuesFrom(<{D}biological_processes> ObjectIntersectionOf(<{OBO}GO_0008219> "
        f"ObjectHasValue(<{D}modifier> <{D}ModifierEnum/INCREASED>))))"
    ) in ofn
    supers = {str(s) for s in builder.onto.get_superclasses(death)}
    assert f"{BASE}node/toy_module/pathophysiology/Cell_Loss" in supers  # conforms_to
    assert node_class_iri("CELLULAR_EFFECT__CELL_DEATH") in supers  # tree example
    assert f"{BASE}PathophysiologyNode" in supers
    assert f"{BASE}PhenotypeNode" in {str(s) for s in builder.onto.get_superclasses(f"{BASE}node/Toy_Disease/phenotype/Seizures")}
    seizures = f"{BASE}node/Toy_Disease/phenotype/Seizures"
    assert "http://purl.obolibrary.org/obo/HP_0001250" in {
        str(s) for s in builder.onto.get_superclasses(seizures)
    }
    assert f"ObjectSomeValuesFrom(<{D}causes> <{D}node/Toy_Disease/phenotype/Seizures>)" in ofn
    assert builder.stats.unresolved_targets == [("Toy_Disease", "Neuronal Death", "Nothing By This Name")]


def test_other_node_kinds_and_edges(toy_kb):
    tree, root = toy_kb
    path = root / "disorders" / "Toy_Disease.yaml"
    path.write_text(path.read_text() + TREATMENT)
    builder, ofn = _ofn(tree, root)
    drug = f"{BASE}node/Toy_Disease/treatment/Antiseizure_Medication"
    assert drug in {str(c) for c in builder.onto.get_classes()}
    supers = {str(s) for s in builder.onto.get_superclasses(drug)}
    assert f"{BASE}TreatmentNode" in supers
    assert "http://purl.obolibrary.org/obo/NCIT_C15986" in supers
    assert f"ObjectSomeValuesFrom(<{D}treats> <{D}node/Toy_Disease/phenotype/Seizures>)" in ofn


def test_tree_definitions_become_gcis(toy_kb):
    tree, root = toy_kb
    builder, ofn = _ofn(tree, root)
    assert builder.stats.counts["tree_definitions"] == 2
    assert f"ObjectSomeValuesFrom(<{D}locations> <{D}AnyTerm/UBERON>)" in ofn
    assert f"ObjectHasValue(<{D}modifier>" in ofn


def test_cli_writes_a_loadable_file(toy_kb, tmp_path):
    tree, root = toy_kb
    out = tmp_path / "out.owx"
    assert main(["-o", str(out), "--tree", str(tree),
                 "--kb-dir", str(root / "disorders"), "--kb-dir", str(root / "modules")]) == 0
    reloaded = pyhornedowl.open_ontology_from_file(str(out))
    assert f"{BASE}node/Toy_Disease/phenotype/Seizures" in {str(c) for c in reloaded.get_classes()}


def test_functional_syntax_handles_quote_then_multibyte(toy_kb, tmp_path):
    """horned-owl 1.4's OFN writer panicked on this shape of literal; 2.0 does not."""
    tree, root = toy_kb
    path = root / "disorders" / "Toy_Disease.yaml"
    text = path.read_text().replace(
        "- name: Neuronal Death\n",
        '- name: Neuronal Death\n  description: \'Domain-switch ("zipping") model \u2014 "unzipping" \u2014 opens it.\'\n',
    )
    path.write_text(text)
    out = tmp_path / "out.ofn"
    assert main(["-o", str(out), "--tree", str(tree),
                 "--kb-dir", str(root / "disorders"), "--kb-dir", str(root / "modules")]) == 0
    assert "\u2014" in out.read_text(encoding="utf-8")


def test_entry_filter_keeps_modules(toy_kb, tmp_path):
    tree, root = toy_kb
    (root / "disorders" / "Other_Disease.yaml").write_text("name: Other\npathophysiology:\n- name: Something\n")
    builder = build(tree, [root / "disorders", root / "modules"], entry_globs=["Toy_*"])
    classes = {str(c) for c in builder.onto.get_classes()}
    assert f"{BASE}node/Toy_Disease/phenotype/Seizures" in classes
    assert f"{BASE}node/toy_module/pathophysiology/Cell_Loss" in classes
    assert not any("/Other_Disease/" in c for c in classes)


def test_version_iri_records_source_commit(toy_kb):
    tree, root = toy_kb
    builder = build(tree, [root / "disorders", root / "modules"], source_commit="abc123")
    ofn = builder.onto.save_to_string("ofn")
    assert f"{BASE}pathograph-tbox/abc123/pathograph-tbox.owl" in ofn
    assert "https://github.com/monarch-initiative/dismech/tree/abc123" in ofn


@pytest.mark.skipif(not (default_dismech_dir() / TREE_PATH).is_file(), reason="no dismech checkout")
def test_real_tree_parses_into_owl(tmp_path):
    """The committed tree (no KB walk) translates without error."""
    empty = tmp_path / "empty"
    empty.mkdir()
    builder = build(default_dismech_dir() / TREE_PATH, [empty])
    assert builder.stats.counts["tree_classes"] > 50
    assert builder.stats.counts["tree_definitions"] > 30


def test_nodes_link_to_their_disease(toy_kb):
    tree, root = toy_kb
    _, ofn = _ofn(tree, root)
    mondo = f"<{OBO}MONDO_0000001>"
    assert (
        f"SubClassOf(<{D}node/Toy_Disease/pathophysiology/Neuronal_Death> "
        f"ObjectSomeValuesFrom(<{OBO}RO_0003302> {mondo}))"
    ) in ofn
    assert (
        f"SubClassOf(<{D}node/Toy_Disease/phenotype/Seizures> "
        f"ObjectSomeValuesFrom(<{OBO}RO_0002201> {mondo}))"
    ) in ofn
    # modules carry no disease term, so their nodes get no link
    assert f"<{D}node/toy_module/pathophysiology/Cell_Loss> ObjectSomeValuesFrom(<{OBO}RO_0003302>" not in ofn


def test_causal_predicates_are_ro_causally_upstream_of(toy_kb):
    tree, root = toy_kb
    _, ofn = _ofn(tree, root)
    assert f"SubObjectPropertyOf(<{D}causes> <{OBO}RO_0002411>)" in ofn
