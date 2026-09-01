"""An append-oriented evidence ledger.

Orchestration checkpoints and an audit record have different lifetimes and
different readers, so this is not the graph's state store. A LangGraph
checkpoint exists to resume a workflow; this exists to answer a question three
months later, when the workflow is long gone.

Records are hash-chained. That does not make the file tamper-proof -- anyone
who can rewrite it can recompute the chain -- it makes truncation and in-place
edits detectable, which is the honest claim for a local JSONL file. A real
deployment substitutes an event store or immutable object storage;
`verify_chain` is what such a store would have to keep true.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterator, Optional

from .provenance import EvidenceRecord

__all__ = ["EvidenceLedger"]

GENESIS = "0" * 64


class EvidenceLedger:
    def __init__(self, path: Optional[str | Path] = None) -> None:
        self.path = Path(path) if path else None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rows: list[dict] = []
        self._last_hash = GENESIS
        if self.path is not None and self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._rows.append(row)
                    self._last_hash = row["hash"]

    @staticmethod
    def _hash(prev_hash: str, seq: int, body: dict) -> str:
        payload = json.dumps(
            {"prev": prev_hash, "seq": seq, "record": body}, sort_keys=True, default=str
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def append(self, record: EvidenceRecord) -> dict:
        seq = len(self._rows)
        body = record.to_dict()
        row = {
            "seq": seq,
            "prev_hash": self._last_hash,
            "hash": self._hash(self._last_hash, seq, body),
            "record": body,
        }
        self._rows.append(row)
        self._last_hash = row["hash"]
        if self.path is not None:
            with self.path.open("a") as fh:
                fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        return row

    def verify_chain(self) -> bool:
        prev = GENESIS
        for seq, row in enumerate(self._rows):
            if row["seq"] != seq or row["prev_hash"] != prev:
                return False
            if row["hash"] != self._hash(prev, seq, row["record"]):
                return False
            prev = row["hash"]
        return True

    def records(self) -> tuple[EvidenceRecord, ...]:
        return tuple(EvidenceRecord(**row["record"]) for row in self._rows)

    def for_request(self, request_id: str) -> tuple[EvidenceRecord, ...]:
        return tuple(r for r in self.records() if r.request_id == request_id)

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self) -> Iterator[dict]:
        return iter(self._rows)
