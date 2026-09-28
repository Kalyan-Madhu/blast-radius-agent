"""Seed the Hindsight bank with the first 5 historical postmortems from data/incidents.json."""
import json
import logging
import sys
from pathlib import Path

from hindsight_client import BANK_ID, retain_memory


SEED_COUNT = 5
# ponytail: truncate logs to bound server-side extraction cost; raise if recall misses on deep stack frames.
LOG_EXCERPT_CHARS = 1500


def to_postmortem(inc):
    cascade = inc["cascade_pattern"]
    steps = "\n".join(f"{i}. {step}" for i, step in enumerate(inc["runbook_fix"], 1))
    return (
        f"Postmortem {inc['id']}: {inc['service']} incident at {inc['timestamp']}.\n"
        f"Cascade pattern: {cascade['type']} ({' -> '.join(cascade['path'])}).\n"
        f"Root cause: {inc['root_cause']}\n"
        f"Fix that resolved it:\n{steps}\n"
        f"Raw log excerpt:\n{inc['raw_log'][:LOG_EXCERPT_CHARS]}"
    )


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    incidents = json.loads(Path(__file__).with_name("data").joinpath("incidents.json").read_text(encoding="utf-8"))

    failed = 0
    for inc in incidents[:SEED_COUNT]:
        ok = retain_memory(
            BANK_ID,
            to_postmortem(inc),
            metadata={"incident_id": inc["id"], "service": inc["service"], "cascade_type": inc["cascade_pattern"]["type"]},
            document_id=inc["id"],
            timestamp=inc["timestamp"],
        )
        print(f"{'retained' if ok else 'FAILED  '} {inc['id']} ({inc['service']})")
        failed += not ok

    print(f"\n{SEED_COUNT - failed}/{SEED_COUNT} postmortems stored in bank '{BANK_ID}'.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
