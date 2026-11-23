# CORTEX AION

**The data foundation for agentic intelligence.**

CORTEX AION is an evolving Azure Data Engineering project focused on turning fragmented operational data into reliable, traceable information that future AI agents can safely use as context.

> **Status:** Planning / initial setup. No data pipeline or agent has been implemented yet.

## v0.1 — Data Foundations (UAX Big Data)

The first milestone is deliberately scoped to two practical Azure Data Factory exercises:

1. **Copy Activity in a pipeline** — ingest a reproducible sample of public operational-service data into Azure Data Lake Storage Gen2.
2. **Code-free data transformation** — use Azure Data Factory Mapping Data Flows to validate, normalize and route records into prepared and review datasets.

**Planned flow:**

```text
Public operational dataset
          |
          v
Azure Data Factory / Copy Activity
          |
          v
ADLS Gen2 / bronze (original data)
          |
          v
ADF Mapping Data Flow
          |
          +--> silver (validated records)
          |
          +--> quarantine (records requiring review)
```

## Design principles

- Preserve source data and provenance.
- Define explicit data contracts and reproducible transformations.
- Validate outputs with evidence rather than relying only on successful pipeline runs.
- Keep data-source adapters separate from reusable processing logic.
- Never commit secrets or unnecessary personal data.

## Future direction

Later versions may add multi-source enterprise integration, context retrieval, access control and agent memory. **These are future possibilities, not features of v0.1.**

## Repository

Azure Data Factory definitions will be maintained under `azure/adf/` once the GitHub integration is configured. Supporting scripts, tests and documentation will be added as implementation progresses.

## Academic context

Developed as an applied learning project for the UAX Master's in Big Data for Business. The first milestone targets the Unit 2 Azure data-integration activity. The university requires an individual PDF report documenting the exercises, findings, challenges and solutions; GitHub is additional portfolio documentation.

---
**Project:** CORTEX AION · **Stage:** v0.1 planning
