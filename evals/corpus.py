"""Generate the discovery corpus. Deterministic, so the numbers are reproducible.

Forty datasets across eight domains, twenty-four queries, four authorization
profiles. Relevance is defined by construction -- a dataset is relevant to a
query if it belongs to the query's domain -- because a ground truth argued
after the fact is a ground truth fitted to the retriever.

Run `python evals/corpus.py` to regenerate `evals/datasets/*.json`. The outputs
are committed, so the measurement can be reproduced without rerunning this.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "datasets"

DOMAINS = {
    "purification": {
        "vocabulary": "purification recovery yield elution buffer capture polish load",
        "facets": ["batch records", "step yields", "buffer conditions", "load challenges", "elution pools"],
        "sensitivity": "internal",
    },
    "chromatography": {
        "vocabulary": "chromatography column peak resolution retention gradient pooling",
        "facets": ["peak tables", "column performance", "gradient profiles", "pooling decisions", "resolution trends"],
        "sensitivity": "internal",
    },
    "fermentation": {
        "vocabulary": "fermentation bioreactor viability titer feed dissolved oxygen",
        "facets": ["viability curves", "titer profiles", "feed schedules", "oxygen transfer", "harvest criteria"],
        "sensitivity": "internal",
    },
    "analytics": {
        "vocabulary": "assay analytical potency purity impurity release specification",
        "facets": ["potency assays", "purity results", "impurity profiles", "release testing", "specification limits"],
        "sensitivity": "confidential",
    },
    "clinical": {
        "vocabulary": "clinical subject endpoint adverse dose cohort visit",
        "facets": ["subject observations", "endpoint summaries", "adverse events", "dose cohorts", "visit schedules"],
        "sensitivity": "restricted",
    },
    "supply": {
        "vocabulary": "supply inventory lot shipment warehouse cold chain logistics",
        "facets": ["lot inventory", "shipment tracking", "cold chain excursions", "warehouse stock", "logistics routes"],
        "sensitivity": "internal",
    },
    "equipment": {
        "vocabulary": "equipment calibration maintenance asset downtime utilisation sensor",
        "facets": ["calibration records", "maintenance logs", "downtime events", "asset utilisation", "sensor streams"],
        "sensitivity": "internal",
    },
    "quality": {
        "vocabulary": "quality deviation capa audit complaint change control batch disposition",
        "facets": ["deviations", "CAPA records", "audit findings", "complaints", "batch disposition"],
        "sensitivity": "confidential",
    },
}

CAPABILITIES = ["search", "aggregate", "compare", "summarize"]

# principal class -> domains it holds capabilities on
PROFILES = {
    "process-engineer": ["purification", "chromatography", "fermentation", "equipment"],
    "analyst": ["analytics", "chromatography", "quality"],
    "clinical-reviewer": ["clinical", "analytics"],
    "external-auditor": ["quality"],
}

CLEARANCE = {
    "process-engineer": "confidential",
    "analyst": "confidential",
    "clinical-reviewer": "restricted",
    "external-auditor": "internal",
}


def build() -> tuple[list[dict], list[dict], dict]:
    datasets: list[dict] = []
    for domain, spec in DOMAINS.items():
        for index, facet in enumerate(spec["facets"], start=1):
            datasets.append(
                {
                    "dataset": f"{domain}-{facet.replace(' ', '-').lower()}",
                    "domain": domain,
                    "version": "2026.09.01",
                    "revision": f"rev-{domain}-{index:02d}",
                    "schema_version": "1",
                    "description": f"{facet.capitalize()} for {domain}: {spec['vocabulary']}.",
                    "schemas": [facet.replace(" ", "_")],
                    "capabilities": [
                        {
                            "name": name,
                            "effect": "read" if name in ("search", "compare") else "compute",
                            "sensitivity": spec["sensitivity"],
                            "description": f"{name} over {facet} in {domain}",
                        }
                        for name in CAPABILITIES
                    ],
                    "prohibited": ["delete_source", "bypass_governance"],
                    "policies": [f"POL-{domain.upper()[:4]}-001"],
                    "freshness": {"maximum_age_s": 86400},
                    "age_s": 3600,
                    "provenance": {"system": "volume", "source": "synthetic"},
                }
            )

    queries: list[dict] = []
    for domain, spec in DOMAINS.items():
        for facet in spec["facets"][:3]:
            queries.append(
                {
                    "query": f"what do the {facet} tell us about {spec['vocabulary'].split()[1]}",
                    "domain": domain,
                    "relevant": [d["dataset"] for d in datasets if d["domain"] == domain],
                }
            )

    profiles = {
        name: {
            "principal_class": name,
            "clearance": CLEARANCE[name],
            "grants": {
                d["dataset"]: CAPABILITIES
                for d in datasets
                if d["domain"] in domains
            },
        }
        for name, domains in PROFILES.items()
    }
    return datasets, queries, profiles


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    datasets, queries, profiles = build()
    (OUT / "corpus.json").write_text(json.dumps({"datasets": datasets}, indent=2) + "\n")
    (OUT / "queries.json").write_text(json.dumps({"queries": queries}, indent=2) + "\n")
    (OUT / "profiles.json").write_text(json.dumps({"profiles": profiles}, indent=2) + "\n")
    print(
        f"{len(datasets)} datasets across {len(DOMAINS)} domains, "
        f"{len(queries)} queries, {len(profiles)} authorization profiles"
    )


if __name__ == "__main__":
    main()
