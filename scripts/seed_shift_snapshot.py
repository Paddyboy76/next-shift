#!/usr/bin/env python3
"""Record a real shift-handover snapshot from current authoritative Firestore state.

`next_shift.workflows.continuity.create_shift_handover` is a real, tested
workflow, but nothing in the deployed services invokes it, so the
`shift_snapshots` collection stays empty and the Operations "Past" panel shows
"Shift snapshots 0". This script is the operator-side entry point for that
workflow. It is a pre-recording preparation tool, not a demo control:

- it does not mutate any issue;
- it does not change any issue state, owner, or evidence;
- it only reads current unresolved work and writes one snapshot document.

Usage:
    python scripts/seed_shift_snapshot.py --outgoing "Night" --incoming "Day"
    python scripts/seed_shift_snapshot.py --list
"""

from __future__ import annotations

import argparse
import json
import sys

from next_shift.persistence.continuity import SHIFT_COLLECTION
from next_shift.persistence.firestore import get_db
from next_shift.workflows.continuity import create_shift_handover


def list_snapshots() -> int:
    snapshots = [
        document.to_dict() or {}
        for document in get_db().collection(SHIFT_COLLECTION).stream()
    ]
    snapshots.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    print(f"shift_snapshots={len(snapshots)}")
    for snapshot in snapshots[:10]:
        print(
            f"  {snapshot.get('outgoing_shift')} -> {snapshot.get('incoming_shift')}"
            f" · unresolved={snapshot.get('unresolved_count')}"
            f" · {snapshot.get('created_at')}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outgoing", default="Night shift", help="Outgoing shift label")
    parser.add_argument("--incoming", default="Day shift", help="Incoming shift label")
    parser.add_argument("--list", action="store_true", help="List existing snapshots and exit")
    arguments = parser.parse_args()

    if arguments.list:
        return list_snapshots()

    snapshot = create_shift_handover(
        outgoing_shift=arguments.outgoing,
        incoming_shift=arguments.incoming,
    )

    print(
        json.dumps(
            {
                "snapshot_id": snapshot.get("id"),
                "outgoing_shift": snapshot.get("outgoing_shift"),
                "incoming_shift": snapshot.get("incoming_shift"),
                "unresolved_count": snapshot.get("unresolved_count"),
                "issues_by_owner": snapshot.get("issues_by_owner"),
                "created_at": snapshot.get("created_at"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
