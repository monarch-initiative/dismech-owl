# dismech-owl: OWL builds of the dismech knowledge base.

set shell := ["bash", "-euo", "pipefail", "-c"]
# The dismech checkout is the single input. Override with DISMECH_DIR=...

dismech_dir := env_var_or_default("DISMECH_DIR", "../dismech")
dismech_ref := `cat DISMECH_REF`
robot_version := "1.9.8"
robot := "java -Xmx" + env_var_or_default("ROBOT_MEM", "12G") + " -jar tools/robot.jar"
build := "build"

default:
    @just --list

# Clone dismech at the pinned commit (DISMECH_REF) next to this repo
fetch-dismech:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -d "{{dismech_dir}}/.git" ]; then
      git clone --filter=blob:none --no-checkout https://github.com/monarch-initiative/dismech "{{dismech_dir}}"
    fi
    git -C "{{dismech_dir}}" fetch --depth 1 origin {{dismech_ref}}
    git -C "{{dismech_dir}}" checkout --detach {{dismech_ref}}

# Repin DISMECH_REF to the dismech checkout's current HEAD
pin-dismech:
    git -C "{{dismech_dir}}" rev-parse HEAD > DISMECH_REF
    @echo "DISMECH_REF -> $(cat DISMECH_REF)"

install:
    uv sync

test:
    uv run pytest -q

lint:
    uv run ruff check src tests

# The TBox: every pathograph node a class, under the node-class tree
tbox *args:
    mkdir -p {{build}}
    uv run dismech-owl-tbox --dismech-dir {{dismech_dir}} -o {{build}}/dismech-pathograph.ofn {{args}}

# Quick build over a few entries, for development
tbox-sample pattern="Fanconi*":
    mkdir -p {{build}}
    uv run dismech-owl-tbox --dismech-dir {{dismech_dir}} --entry '{{pattern}}' -o {{build}}/sample.ofn

# The sample docs/exploring.md is written against: five inherited bone marrow
# failure entries (plus all modules), GO and MONDO modules merged, reasoned.
example:
    mkdir -p {{build}}
    uv run dismech-owl-tbox --dismech-dir {{dismech_dir}} --entry 'Fanconi_Anemia' --entry 'Diamond-Blackfan*' \
        --entry 'Dyskeratosis*' --entry '*Shwachman*' --entry 'Inherited_Aplastic_Anemia' -o {{build}}/bmf.ofn
    just reason {{build}}/bmf.ofn {{build}}/bmf-reasoned.ofn

# Download ROBOT (once) into tools/
robot:
    @test -f tools/robot.jar || (mkdir -p tools && curl -fsSL -o tools/robot.jar \
        https://github.com/ontodev/robot/releases/download/v{{robot_version}}/robot.jar)

# Download GO (once) into build/
go:
    @test -f {{build}}/go.owl || (mkdir -p {{build}} && curl -fsSL -o {{build}}/go.owl \
        http://purl.obolibrary.org/obo/go.owl)

# Download MONDO (base, no imports; once) into build/
mondo:
    @test -f {{build}}/mondo-base.owl || (mkdir -p {{build}} && curl -fsSL -o {{build}}/mondo-base.owl \
        http://purl.obolibrary.org/obo/mondo/mondo-base.owl)

# BOT modules of GO and MONDO holding just the terms <input> references,
# so the merged file carries their is-a ancestry and labels.
modules input=(build + "/sample.ofn"): robot go mondo
    {{robot}} extract --method BOT --input {{build}}/go.owl \
        --term-file <(grep -o 'http://purl.obolibrary.org/obo/GO_[0-9]*\|obo:GO_[0-9]*\|GO:[0-9]\{7\}' {{input}} \
            | sed 's|^obo:GO_|GO:|; s|^http://purl.obolibrary.org/obo/GO_|GO:|' | sort -u) \
        --output {{build}}/go-module.owl
    {{robot}} extract --method BOT --input {{build}}/mondo-base.owl \
        --term-file <(grep -o 'http://purl.obolibrary.org/obo/MONDO_[0-9]*\|obo:MONDO_[0-9]*\|MONDO:[0-9]\{7\}' {{input}} \
            | sed 's|^obo:MONDO_|MONDO:|; s|^http://purl.obolibrary.org/obo/MONDO_|MONDO:|' | sort -u) \
        --output {{build}}/mondo-module.owl

# Merge the GO and MONDO modules into <input> and classify with ELK.
# Writes OFN so OAK sees the prefix declarations.
reason input=(build + "/sample.ofn") out=(build + "/reasoned.ofn"): (modules input)
    {{robot}} merge --input {{input}} --input {{build}}/go-module.owl --input {{build}}/mondo-module.owl \
        reason --reasoner ELK --axiom-generators "SubClass" --exclude-tautologies structural \
        --output {{out}}

# Release: full TBox, reasoned
release: tbox (reason build + "/dismech-pathograph.ofn" build + "/dismech-pathograph-reasoned.ofn")
