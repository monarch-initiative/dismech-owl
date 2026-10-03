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
    uv run dismech-owl-tbox --dismech-dir {{dismech_dir}} -o {{build}}/dismech-pathograph.owl {{args}}

# Quick build over a few entries, for development
tbox-sample pattern="Fanconi*":
    mkdir -p {{build}}
    uv run dismech-owl-tbox --dismech-dir {{dismech_dir}} --entry '{{pattern}}' -o {{build}}/sample.owl

# Download ROBOT (once) into tools/
robot:
    @test -f tools/robot.jar || (mkdir -p tools && curl -fsSL -o tools/robot.jar \
        https://github.com/ontodev/robot/releases/download/v{{robot_version}}/robot.jar)

# Download GO (once) into build/
go:
    @test -f {{build}}/go.owl || (mkdir -p {{build}} && curl -fsSL -o {{build}}/go.owl \
        http://purl.obolibrary.org/obo/go.owl)

# Merge in GO and the HP/CL/UBERON/CHEBI terms the TBox references, as a
# BOT module of each, then reason with ELK. Input defaults to the sample build.
reason input=(build + "/sample.owl") out=(build + "/reasoned.owl"): robot go
    {{robot}} extract --method BOT --input {{build}}/go.owl \
        --term-file <(grep -o 'http://purl.obolibrary.org/obo/GO_[0-9]*' {{input}} | sort -u) \
        --output {{build}}/go-module.owl
    {{robot}} merge --input {{input}} --input {{build}}/go-module.owl \
        reason --reasoner ELK --axiom-generators "SubClass" --exclude-tautologies structural \
        --output {{out}}

# Release: full TBox, reasoned
release: tbox (reason build + "/dismech-pathograph.owl" build + "/dismech-pathograph-reasoned.owl")
