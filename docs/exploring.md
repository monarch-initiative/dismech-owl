# Exploring the TBox with OAK

[OAK](https://github.com/INCATools/ontology-access-kit) reads the build through
its `funowl:` adapter, which parses with py-horned-owl. Use the OFN output,
because it carries the prefix declarations OAK needs to show CURIEs.

Every example below is real output from the bone-marrow-failure sample, which
`just example` builds. Long listings are cut short with `...`, and the
`relationships` tables show only the columns that matter here.

```bash
just example    # five entries + GO and MONDO modules, reasoned -> build/bmf-reasoned.ofn
R=funowl:build/bmf-reasoned.ofn
```

On this sample each command takes 3–5 seconds. On the full build
(`build/dismech-pathograph.ofn`, about 200 MB) it takes about 20 seconds,
almost all of it parsing.

**Use exact CURIEs, not label search.** `runoak … info 'l~…'` works but scans
every label through the generic search path; on a 4 MB file it took two
minutes. To find a node, grep the OFN file for its IRI:
`grep -o 'dismech/node/Fanconi_Anemia/pathophysiology/[A-Za-z0-9_]*' build/bmf.ofn`.

## Node CURIEs

Every pathograph node is a class with the IRI
`https://w3id.org/monarch-initiative/dismech/node/<entry>/<kind>/<slug>`,
which OAK shows as `dismech:node/<entry>/<kind>/<slug>`:

```
dismech:node/Fanconi_Anemia/pathophysiology/Genomic_Instability
dismech:node/Fanconi_Anemia/phenotype/Thrombocytopenia
dismech:node/Fanconi_Anemia/treatment/Androgen_Therapy
```

## Is-a: where a node sits in the node-class tree

```console
$ runoak -i $R tree -p i dismech:node/Fanconi_Anemia/pathophysiology/Genomic_Instability
* [] dismech:PathographNode ! pathograph node
    * [i] dismech:PathophysiologyNode ! pathophysiology node
        * [i] dnc:GENOMIC_EFFECT ! GENOMIC EFFECT
            * [i] dnc:GENOMIC_EFFECT__GENOME_INSTABILITY ! genome instability
                * [i] **dismech:node/Fanconi_Anemia/pathophysiology/Genomic_Instability ! Genomic Instability (Fanconi_Anemia)**
```

`dnc:` is the node-class tree. This node's place in it is asserted, because
the tree cites it as a worked example. For most nodes, the place is inferred by
the reasoner from the tree's logical definitions; see
[Classification](#classification-by-the-tree-definitions).

## Non-is-a edges

### Everything on one node

```console
$ runoak -i $R relationships dismech:node/Dyskeratosis_Congenita/pathophysiology/Impaired_Telomere_Maintenance
predicate                   object                                   object_label
rdfs:subClassOf             dnc:GENOMIC_EFFECT__GENOME_INSTABILITY   genome instability
rdfs:subClassOf             dnc:MOLECULAR_ACTIVITY_EFFECT            MOLECULAR ACTIVITY EFFECT
RO:0003302                  MONDO:0015780                            dyskeratosis congenita
dismech:causes              dismech:node/Dyskeratosis_Congenita/pathophysiology/Critically_Short_Telomeres_and_Replicative_Senescence
dismech:cellular_components GO:0005697                               telomerase holoenzyme complex
dismech:molecular_functions GO:0070034                               telomerase RNA binding
dismech:cell_types          CL:0000037                               hematopoietic stem cell
dismech:genes               hgnc:11824                               TINF2
dismech:genes               hgnc:25522                               WRAP53
...
```

The first `rdfs:subClassOf` is asserted: the node-class tree cites this node
as a *genome instability* example. The second is inferred: the tree defines
MOLECULAR ACTIVITY EFFECT as `molecular_functions some GO`, and this node
carries *telomerase RNA binding*. A node in two tiers is what the tree calls a
debundle candidate, a node making two claims at once (see
[Classification](#classification-by-the-tree-definitions)).

Three kinds of edge show up here:

| Edge | Meaning |
|---|---|
| `dismech:<slot>` (`genes`, `cell_types`, `biological_processes` …) | a descriptor bound on the node, read as "this node involves some instance of that term". With a `modifier`, the filler is `(term and modifier value INCREASED)`. |
| `RO:0003302` *causes or contributes to condition* | the node's link to its entry's disease. See [Back to the disease](#back-to-the-disease-and-to-mondo). |
| graph edges (`dismech:causes`, `dismech:treats` …) | the pathograph's own edges, below |

### Graph edges by predicate (full KB)

| Predicate | Axioms | From → to |
|---|---:|---|
| `causes` | 46,429 | pathophysiology → pathophysiology / phenotype |
| `targets` | 5,961 | treatment → mechanism |
| `contributes_to` | 5,521 | gene → mechanism |
| `treats` | 3,396 | treatment → phenotype |
| `models` / `partially_models` / `fails_to_model` | 2,070 / 1,268 / 292 | model → mechanism |
| `variant_of` | 1,610 | variant → gene |
| `readout` | 1,543 | mechanism → biomarker or phenotype |
| `leads_to` | 806 | phenotype → phenotype (sequelae) |
| `triggers` / `exacerbates` / `predisposes_to` / `modulates` / `protects_against` | 535 / 174 / 284 / 21 / 20 | exposure → mechanism |
| `measures` / `perturbs` / `rescues` | 410 / 313 / 219 | model → mechanism |
| `has_regulatory_target` | 23 | variant → gene |

Plus 64,144 disease links, 49,335 descriptor existentials, 3,461 `conforms_to`
subsumptions and 63,803 links from phenotype, exposure, treatment, gene and
biomarker nodes to their bound term. `just tbox` prints these counts.

`dismech:causes` and `dismech:leads_to` are declared sub-properties of
`RO:0002411` *causally upstream of*, so a query in RO terms reaches them.

### Following a causal chain

Each edge points from cause to effect, so OAK's "ancestors" over
`dismech:causes` are a node's downstream effects:

```console
$ runoak -i $R tree -p dismech:causes dismech:node/Fanconi_Anemia/pathophysiology/Genomic_Instability
* [] dismech:node/Fanconi_Anemia/phenotype/Myelodysplastic_Syndrome ! Myelodysplastic Syndrome (Fanconi_Anemia)
    * [causes] dismech:node/Fanconi_Anemia/pathophysiology/Clonal_Evolution ! Clonal Evolution (Fanconi_Anemia)
        * [causes] **dismech:node/Fanconi_Anemia/pathophysiology/Genomic_Instability ! Genomic Instability (Fanconi_Anemia)**
* [] dismech:node/Fanconi_Anemia/phenotype/Thrombocytopenia ! Thrombocytopenia (Fanconi_Anemia)
    * [causes] dismech:node/Fanconi_Anemia/pathophysiology/Bone_Marrow_Failure ! Bone Marrow Failure (Fanconi_Anemia)
        * [causes] dismech:node/Fanconi_Anemia/pathophysiology/Hematopoietic_Stem_Cell_Attrition ! Hematopoietic Stem Cell Attrition (Fanconi_Anemia)
            * [causes] **dismech:node/Fanconi_Anemia/pathophysiology/Genomic_Instability ! Genomic Instability (Fanconi_Anemia)**
...
```

Its "descendants" are everything upstream of a phenotype:

```console
$ runoak -i $R descendants -p dismech:causes dismech:node/Fanconi_Anemia/phenotype/Thrombocytopenia
dismech:node/Fanconi_Anemia/pathophysiology/Bone_Marrow_Failure ! Bone Marrow Failure (Fanconi_Anemia)
dismech:node/Fanconi_Anemia/pathophysiology/Hematopoietic_Stem_Cell_Attrition ! Hematopoietic Stem Cell Attrition (Fanconi_Anemia)
dismech:node/Fanconi_Anemia/pathophysiology/Genomic_Instability ! Genomic Instability (Fanconi_Anemia)
dismech:node/Fanconi_Anemia/pathophysiology/DNA_Repair_Deficiency ! DNA Repair Deficiency (Fanconi_Anemia)
dismech:node/Fanconi_Anemia/pathophysiology/Core_Complex_Dysfunction ! Core Complex Dysfunction (Fanconi_Anemia)
...
```

`viz --down` draws the same upstream view (needs `og2dot` from the npm package
`obographviz`, plus Graphviz):

```bash
runoak -i $R viz --down -p dismech:causes --no-view \
  -o docs/images/fanconi-thrombocytopenia-causes.png \
  dismech:node/Fanconi_Anemia/phenotype/Thrombocytopenia
```

![What causes thrombocytopenia in Fanconi anemia](images/fanconi-thrombocytopenia-causes.png)

### Treatments

```console
$ runoak -i $R relationships --direction down -p dismech:targets dismech:node/Fanconi_Anemia/pathophysiology/Bone_Marrow_Failure
subject                                                                   predicate
dismech:node/Fanconi_Anemia/treatment/Androgen_Therapy                    dismech:targets
dismech:node/Fanconi_Anemia/treatment/Hematopoietic_Stem_Cell_Transplantation_HSCT  dismech:targets
```

## Back to the disease, and to MONDO

Each pathophysiology and phenotype node is linked to its entry's disease term
by an existential on the node:

```
<pathophysiology node> SubClassOf RO:0003302 'causes or contributes to condition' some <MONDO disease>
<phenotype node>       SubClassOf RO:0002201 'phenotype of'                       some <MONDO disease>
```

The axiom is on the node, not on the MONDO class, on purpose. A node is a
disease-specific class, so "every instance of FA genomic instability
contributes to some case of FA" is true. The reverse direction, `MONDO:0019391
SubClassOf 'has phenotype' some <node>`, would say every case of Fanconi
anemia has every curated phenotype, which dismech does not claim (its
phenotypes carry frequencies). Module nodes have no disease term, so they get
no link. Both RO relations were looked up in RO
(`runoak -i sqlite:obo:ro labels RO:0003302 RO:0002201`), not written from
memory.

### From a disease to its mechanisms

```console
$ runoak -i $R relationships --direction down -p RO:0003302 MONDO:0019391
subject                                                                          object_label
dismech:node/Fanconi_Anemia/pathophysiology/Translesion_Synthesis_Defect          Fanconi anemia
dismech:node/Fanconi_Anemia/pathophysiology/Homologous_Recombination_Impairment   Fanconi anemia
dismech:node/Fanconi_Anemia/pathophysiology/Differentiation_Induced_Genotoxic_Stress  Fanconi anemia
...                                                                              (22 nodes)
```

### Through MONDO's hierarchy

`just example` merges a BOT module of MONDO (just the classes the build
references, plus their ancestors). Combining `i` with `RO:0003302` then answers
questions at any level of MONDO's classification. For example, the mechanisms
of any inherited aplastic anemia:

```console
$ runoak -i $R descendants -p i,RO:0003302 MONDO:0001713 | grep /pathophysiology/ | cut -d/ -f2 | sort | uniq -c
      6 Diamond-Blackfan_Anemia
      7 Diamond-Blackfan_Anemia_14_With_Mandibulofacial_Dysostosis
      4 Diamond-Blackfan_Anemia_15_With_Mandibulofacial_Dysostosis
     22 Fanconi_Anemia
      7 Inherited_Aplastic_Anemia
```

Dyskeratosis congenita is in the sample but missing from this list, because
MONDO does not file it under inherited aplastic anemia. It sits under
*hereditary neoplastic syndrome* and *ectodermal dysplasia syndrome*
(`runoak -i $R tree -p i MONDO:0015780`). Queries like this show where dismech's
mechanism view and MONDO's classification diverge.

Going the other way, from one mechanism up through its disease into MONDO:

```bash
runoak -i $R viz -p i,RO:0003302 --max-hops 5 --no-view -o docs/images/fanconi-hr-to-mondo.png \
  dismech:node/Fanconi_Anemia/pathophysiology/Homologous_Recombination_Impairment
```

![Homologous recombination impairment, Fanconi anemia, and MONDO's classification of it](images/fanconi-hr-to-mondo.png)

## Classification by the tree definitions

dismech's node-class tree (`kb/node_classes/pathograph_node_classes.txt`) is
used in four ways:

1. **Its classes are the upper hierarchy** for pathophysiology nodes: 101
   classes under `dismech:PathophysiologyNode`, glosses as `skos:definition`,
   `:key` attributes as `rdfs:comment`.
2. **Its worked examples are asserted.** All 2,185 `[Entry] Node` lines resolve
   to a node and become `SubClassOf` the class citing them.
3. **Its 46 `=` definitions become GCIs**, so a reasoner can place nodes the
   tree never mentions. `some PREFIX` atoms (`triggers some ECTO`) go through
   an "any ECTO term" placeholder, with every referenced term asserted under
   its prefix's placeholder.
4. **Optionally (`--scan`), the GO seed table**, applied through dismech's own
   scanner and asserted at the tier level. It is off by default because the
   scanner is a worklist, not reviewed claims.

On the full KB (`just tbox`, then `just reason` with GO and MONDO modules;
about 3 minutes):

| | Pathophysiology nodes with a tree class (of 23,853) | in two or more tiers |
|---|---:|---:|
| asserted (examples, plus `conforms_to` to a cited module node) | 2,378 | 15 |
| after ELK | 10,497 (44%) | 1,839 |

| Tier | asserted | after ELK |
|---|---:|---:|
| CELLULAR EFFECT | 378 | 3,425 |
| PATHWAY EFFECT | 130 | 2,232 |
| MOLECULAR ACTIVITY EFFECT | 195 | 2,195 |
| TISSUE / ORGAN EFFECT | 693 | 1,896 |
| MOLECULAR SUBSTANCE EFFECT | 175 | 1,245 |
| GENOMIC EFFECT | 246 | 792 |
| SYSTEMIC EFFECT | 164 | 397 |
| OUTCOME | 108 | 108 |
| ENVIRONMENTAL EFFECT | 64 | 72 |
| DISPOSITION | 55 | 55 |

What limits it:

- **Classes without a definition only ever hold their examples.** OUTCOME,
  DISPOSITION and the compensation and intervention-point classes are
  judgement classes in the tree, deliberately undefined, so their counts do
  not move.
- **`not` atoms cannot fire under the open-world assumption.** *Systemic
  inflammatory state* is defined as `inflammatory response … and not
  locations some UBERON`; a node without a location is not known to lack one,
  so the reasoner never places a node there.
- **ENVIRONMENTAL EFFECT barely moves** because few pathophysiology nodes use
  the `triggers` slot its definition reads. Exposures mostly connect through
  `environmental[].influences_mechanisms` edges (`dismech:triggers` in this
  TBox), which the definition does not consider.
- **The 1,839 nodes in two or more tiers** are the tree's own debundle signal,
  ready to export as a worklist.
