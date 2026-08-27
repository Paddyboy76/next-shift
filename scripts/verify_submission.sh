#!/usr/bin/env bash

set -euo pipefail

REPO="/home/patrick/next-shift"
cd "${REPO}"

printf '=== NEXT SHIFT SUBMISSION VERIFICATION ===\n'

bash ./verify_readiness.sh

echo
bash ./scripts/demo_proof_snapshot.sh

echo
printf 'NEXT_SHIFT_SUBMISSION=PASS\n'
