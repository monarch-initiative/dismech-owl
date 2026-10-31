"""Tests for release packaging (manifest and notes)."""

from __future__ import annotations

import gzip
import json
import re

from dismech_owl.release import build_manifest, render_notes

DM = "a" * 40
OW = "b" * 40


def _files(tmp_path):
    out = []
    for name in ("dismech-pathograph.ofn.gz", "dismech-pathograph-reasoned.ofn.gz"):
        p = tmp_path / name
        p.write_bytes(gzip.compress(b"Ontology()"))
        out.append(p)
    return out


def test_manifest_records_commits_and_checksums(tmp_path):
    stats = {"counts": {"nodes_pathophysiology": 3}, "unresolved_edges": 1}
    m = build_manifest(stats, _files(tmp_path), dismech_commit=DM, owl_commit=OW, built_at="2026-10-05T10:41:00Z")
    assert m["dismech_commit"] == DM and m["dismech_owl_commit"] == OW
    assert [f["name"] for f in m["files"]] == ["dismech-pathograph-reasoned.ofn.gz", "dismech-pathograph.ofn.gz"]
    assert all(re.fullmatch(r"[0-9a-f]{64}", f["sha256"]) for f in m["files"])
    assert all(f["description"] for f in m["files"])
    json.dumps(m)  # serialisable


def test_notes_carry_the_lines_the_workflow_greps_for(tmp_path):
    stats = {"counts": {"nodes_pathophysiology": 23853, "disease_link_axioms": 64144}, "unresolved_edges": 122}
    m = build_manifest(stats, _files(tmp_path), dismech_commit=DM, owl_commit=OW, built_at="2026-10-05T10:41:00Z")
    notes = render_notes(m)
    # .github/workflows/release.yaml skips a release when the latest one has both lines
    assert f"\ndismech: {DM}\n" in notes
    assert f"\ndismech-owl: {OW}\n" in notes
    assert "23,853 pathophysiology nodes" in notes
    assert "122 graph edges whose target did not resolve" in notes
    assert "2026-10-05" in notes


def test_notes_list_tree_examples_that_no_longer_match(tmp_path):
    stats = {
        "counts": {},
        "unresolved_edges": 0,
        "unresolved_tree_examples": 1,
        "unresolved_tree_example_list": [["Fanconi_Anemia", "Old Node Name"]],
    }
    m = build_manifest(stats, _files(tmp_path), dismech_commit=DM, owl_commit=OW, built_at="2026-10-05T10:41:00Z")
    notes = render_notes(m)
    assert "- 1 node-class tree examples that no longer match a node" in notes
    assert "- `[Fanconi_Anemia] Old Node Name`" in notes
    assert "github.com/monarch-initiative/dismech-owl/" in notes
    assert "cmungall" not in notes


def test_notes_omit_the_section_when_every_example_matches(tmp_path):
    stats = {"counts": {}, "unresolved_edges": 0, "unresolved_tree_examples": 0, "unresolved_tree_example_list": []}
    m = build_manifest(stats, _files(tmp_path), dismech_commit=DM, owl_commit=OW, built_at="2026-10-05T10:41:00Z")
    assert "## Tree examples that no longer match a node" not in render_notes(m)
