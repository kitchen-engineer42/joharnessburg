# to-skills-backend-sku-regression — a cautionary tale

Production's `to-skills-backend` collapsed the 4-type research taxonomy (see `a2o-four-types.md`) into a single `SKU` shape with five parts: `metadata`, `context`, `trigger`, `core_logic`, `output`, plus a `custom_attributes` dict.

This was an over-fitting move for the verification-app domain. For knowledge engineering generally, it lost information richness. Treat this note as a **warning, not a template**.

## The collapse

In `to-skills-backend/app/pipeline/stages/sku_extractor.py`, every extracted unit gets the same shape:

```python
@dataclass
class SKU:
    metadata: SKUMetadata          # uuid, name, source_ref
    context: SKUContext            # applicable_objects, prerequisites, constraints
    trigger: SKUTrigger            # condition_logic
    core_logic: SKUCoreLogic       # logic_type, execution_body, variables
    output: SKUOutput              # output_type, result_template
    custom_attributes: dict
```

A factual statement, a relational pair, a procedural how-to, and a meta-note all get squeezed into this. Factual entries end up with empty `trigger` and `core_logic`. Relational entries end up with their relationship type buried in `custom_attributes`. The schema works for *rules* (its native fit) and is awkward-to-wrong for everything else.

## What was lost

- **Relational typing**. The 13 explicit relation types from A2O (`is-a`, `has-a`, `part-of`, `causes`, ...) became free-form strings in `custom_attributes`. Cross-link queries became substring matches.
- **Meta entries as first-class objects**. The "eureka" / "mapping" / "glossary" categories from A2O don't have a natural home in the SKU schema. They get jammed in.
- **Skill format adherence**. Procedural SKUs claim to be skills but lack the Claude Code SKILL.md frontmatter conventions; they're skill-shaped JSON, not skills.

## Why it happened

Two pressures:

1. **Storage simplicity** — one table, one shape, no schema-evolution headaches.
2. **Extraction pipeline simplicity** — one extractor prompt, one parser.

The trade-off saved engineering effort at the cost of representational power. For the verification-app domain (where everything *is* a rule), it was tolerable. For broader knowledge engineering, it's regressive.

## What John does instead

- **Don't collapse types.** If a project wants 4 types or 7 types or 1 type, the schema-design phase decides per project. The plugin doesn't force a shape.
- **Templates may collapse** if their domain only ever uses one type. A doc-verification template can ship a rules-only schema. That's the template's choice, not core John's.
- **Header + body remains universal.** Across all types, the header (one-liner + classification + cross-refs) / body (full content) split holds. That's progressive disclosure, not a schema choice — see [[knowledge-rewrite]].

## Source

- `to-skills-backend/app/pipeline/stages/sku_extractor.py` defines the SKU dataclass.
- `Anything2Ontology/src/chunks2skus/schemas/sku.py` has the richer 4-type model that production departed from.
- `Anything2Ontology/gaps_analysis.md` records the team's own observation that the collapse cost richness.
