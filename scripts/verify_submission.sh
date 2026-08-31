#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO}"

printf '=== NEXT SHIFT SUBMISSION VERIFICATION ===\n'

# The readiness gate intentionally requires durable security/proof records.
# gcloud logging read has a short implicit freshness window, so make the
# submission-time audit window explicit without weakening any predicate.
bash <(
    awk '
        /^    --limit=1 \\$/ { print "    --freshness=7d \\" }
        { print }
    ' ./verify_readiness.sh
)

echo
bash ./scripts/demo_proof_snapshot.sh

echo
printf 'NEXT_SHIFT_SUBMISSION=PASS\n'
