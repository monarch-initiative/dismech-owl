"""Package a build for a GitHub release: a manifest and release notes.

The weekly release workflow runs ``just tbox``, ``just reason`` and then
``just dist``, which gzips the OWL files into ``build/dist/`` and calls this
module. It writes, next to the files:

* ``manifest.json``: the dismech and dismech-owl commits the build came from,
  the build counts, and the size and sha256 of each file;
* ``release-notes.md``: the same, for a person, used as the release body.

Both commits are read from git, so the same command works locally and in CI.
The release notes carry each commit on its own ``dismech: <sha>`` /
``dismech-owl: <sha>`` line; the workflow greps the latest release for those
lines to skip a release when neither repository has changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dismech_owl.tbox import default_dismech_dir, git_commit

DISMECH_REPO = "https://github.com/monarch-initiative/dismech"
OWL_REPO = "https://github.com/cmungall/dismech-owl"

#: Release file name -> what it is. Files not listed here are still shipped,
#: just without a description.
FILE_DESCRIPTIONS = {
    "dismech-pathograph.ofn.gz": (
        "The TBox as built: every pathograph node a class, the node-class tree, disease links. "
        "External terms are referenced, not imported."
    ),
    "dismech-pathograph-reasoned.ofn.gz": (
        "The TBox merged with GO and MONDO BOT modules and classified with ELK "
        "(inferred subclass axioms added)."
    ),
}

#: Counts surfaced in the release notes, in order, with a label.
HEADLINE_COUNTS = [
    ("nodes_pathophysiology", "pathophysiology nodes"),
    ("nodes_phenotype", "phenotype nodes"),
    ("nodes_treatment", "treatment nodes"),
    ("nodes_genetic", "genetic nodes"),
    ("edge_axioms_causes", "`causes` edges"),
    ("disease_link_axioms", "disease links"),
    ("tree_classes", "node-class tree classes"),
    ("example_axioms", "tree worked examples asserted"),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(
    stats: dict[str, Any],
    files: list[Path],
    *,
    dismech_commit: str | None,
    owl_commit: str | None,
    built_at: str,
) -> dict[str, Any]:
    return {
        "built_at": built_at,
        "dismech_commit": dismech_commit,
        "dismech_owl_commit": owl_commit,
        "stats": stats,
        "files": [
            {
                "name": f.name,
                "bytes": f.stat().st_size,
                "sha256": sha256(f),
                "description": FILE_DESCRIPTIONS.get(f.name, ""),
            }
            for f in sorted(files)
        ],
    }


def render_notes(manifest: dict[str, Any]) -> str:
    dm, ow = manifest["dismech_commit"], manifest["dismech_owl_commit"]
    lines = [
        f"Weekly build of the dismech pathograph TBox, {manifest['built_at'][:10]}.",
        "",
        "## Built from",
        "",
        f"dismech: {dm}",
        f"dismech-owl: {ow}",
        "",
    ]
    if dm:
        lines.append(f"- dismech [`{dm[:12]}`]({DISMECH_REPO}/tree/{dm})")
    if ow:
        lines.append(f"- dismech-owl [`{ow[:12]}`]({OWL_REPO}/tree/{ow})")
    lines += ["", "## Files", "", "| File | Size | Contents |", "|---|---:|---|"]
    for f in manifest["files"]:
        lines.append(f"| `{f['name']}` | {f['bytes'] / 1e6:.1f} MB | {f['description']} |")
    lines += [
        "",
        "Checksums are in `manifest.json`. Decompress with `gunzip`, then browse with OAK, e.g.",
        "`runoak -i funowl:dismech-pathograph-reasoned.ofn tree -p i,RO:0003302 <node CURIE>`;",
        f"see [docs/exploring.md]({OWL_REPO}/blob/main/docs/exploring.md).",
        "",
        "## Counts",
        "",
    ]
    counts = manifest["stats"].get("counts", {})
    for key, label in HEADLINE_COUNTS:
        if key in counts:
            lines.append(f"- {counts[key]:,} {label}")
    lines.append(f"- {manifest['stats'].get('unresolved_edges', 0):,} graph edges whose target did not resolve")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dist", type=Path, default=Path("build/dist"), help="directory holding the files to release")
    ap.add_argument("--stats", type=Path, default=Path("build/dismech-pathograph.stats.json"),
                    help="stats JSON written by dismech-owl-tbox --stats-json")
    ap.add_argument("--dismech-dir", type=Path, default=None,
                    help="dismech checkout the build read (default $DISMECH_DIR, else ../dismech)")
    args = ap.parse_args(argv)

    files = sorted(p for p in args.dist.glob("*.gz"))
    if not files:
        ap.error(f"no .gz files in {args.dist}")
    stats = json.loads(args.stats.read_text())
    dismech_commit = git_commit(args.dismech_dir or default_dismech_dir())
    if stats.get("dismech_commit") and stats["dismech_commit"] != dismech_commit:
        ap.error(f"stats were built from dismech {stats['dismech_commit']}, "
                 f"but the checkout is now at {dismech_commit}")
    manifest = build_manifest(
        stats,
        files,
        dismech_commit=dismech_commit,
        owl_commit=git_commit(Path(__file__).resolve().parents[2]),
        built_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    (args.dist / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (args.dist / "release-notes.md").write_text(render_notes(manifest))
    print(f"wrote {args.dist / 'manifest.json'} and {args.dist / 'release-notes.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
