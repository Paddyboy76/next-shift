#!/usr/bin/env bash

set -u
set -o pipefail

REPO="/home/patrick/next-shift"
BRANCH="codex/autonomous-final-attack"
PROJECT_ID="next-shift-506004"
MASTER="${REPO}/docs/autonomy/MASTER_PLAN.md"
PHASE_DIR="${REPO}/docs/autonomy/phases"
STATUS_FILE="${REPO}/docs/autonomy/STATUS.md"
EVIDENCE_DIR="${REPO}/docs/autonomy/evidence"
LOG_ROOT="/home/patrick/autonomy-logs"
LOCK_FILE="/tmp/next-shift-autonomous-final-attack.lock"

export PATH="${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin"

mkdir -p "${LOG_ROOT}"
mkdir -p "${EVIDENCE_DIR}"

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    echo "Another autonomous final-attack controller is already running."
    exit 1
fi

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
    printf '[%s] %s\n' "$(timestamp)" "$*" | tee -a "${LOG_ROOT}/controller.log"
}

update_status() {
    local phase="$1"
    local state="$2"
    local commit="$3"

    python3 - "${STATUS_FILE}" "${phase}" "${state}" "${commit}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
phase = sys.argv[2]
state = sys.argv[3]
commit = sys.argv[4]

text = path.read_text()
lines = text.splitlines()

needle = f"| {phase} |"
replacement = f"| {phase} | {state} | {commit} |"

out = []
changed = False

for line in lines:
    if line.startswith(needle):
        out.append(replacement)
        changed = True
    else:
        out.append(line)

if not changed:
    raise SystemExit(f"phase missing from STATUS.md: {phase}")

path.write_text("\n".join(out) + "\n")
PY
}

readiness_gate() {
    local phase="$1"
    local outfile="${LOG_ROOT}/${phase}-readiness.log"

    log "Running readiness gate after ${phase}"

    (
        cd "${REPO}"
        READINESS_ALLOW_BRANCH=1 bash ./verify_readiness.sh
    ) 2>&1 | tee "${outfile}"

    local rc=${PIPESTATUS[0]}
    local fails
    local unexpected_warns

    fails="$(grep -c '^FAIL  ' "${outfile}" || true)"

    unexpected_warns="$(
        grep '^WARN  ' "${outfile}" \
          | grep -v 'non-main verification allowed' \
          | wc -l \
          | tr -d ' '
    )"

    if [[ "${rc}" -ne 0 || "${fails}" -ne 0 || "${unexpected_warns}" -ne 0 ]]; then
        log "Readiness gate FAILED after ${phase}: rc=${rc} fails=${fails} unexpected_warns=${unexpected_warns}"
        return 1
    fi

    log "Readiness gate passed after ${phase}"
    return 0
}

cd "${REPO}" || exit 1

log "Autonomous final attack starting."

gcloud config set project "${PROJECT_ID}" >/dev/null 2>&1

if ! codex login status >/dev/null 2>&1; then
    log "Codex is not authenticated."
    exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    log "GitHub CLI is not authenticated."
    exit 1
fi

git fetch origin || exit 1
git checkout "${BRANCH}" || exit 1
git pull --ff-only origin "${BRANCH}" || exit 1

if [[ -n "$(git status --porcelain)" ]]; then
    log "Refusing to start with dirty working tree."
    git status --short | tee -a "${LOG_ROOT}/controller.log"
    exit 1
fi

PHASES=(
    "07-live-truth-audit"
    "08-external-evidence-verification-failure"
    "09-coverage-critic-evidence-inspector"
    "10-registry-memory-otel"
    "11-gateway-model-armor-trace-proof"
    "12-recovery-planner"
    "13-reproducibility-submission"
    "14-spoken-handover"
    "15-four-minute-demo-public-bonus"
    "99-final-acceptance-freeze"
)

for phase in "${PHASES[@]}"; do
    if grep -Fq "| ${phase} | COMPLETE |" "${STATUS_FILE}"; then
        log "Skipping already-complete phase ${phase}"
        continue
    fi

    log "============================================================"
    log "START ${phase}"
    log "============================================================"

    update_status "${phase}" "RUNNING" "$(git rev-parse --short HEAD)"

    prompt_file="${LOG_ROOT}/${phase}-prompt.txt"
    last_message="${LOG_ROOT}/${phase}-last-message.txt"
    phase_log="${LOG_ROOT}/${phase}-codex.log"

    {
        cat "${MASTER}"
        printf '\n\n---\n\n'
        cat "${PHASE_DIR}/${phase}.md"
        printf '\n\n---\n\n'
        cat <<PROMPT
You are executing exactly one autonomous final-attack phase.

Current phase: ${phase}

Work directly in:
${REPO}

Before changing anything:
- read AGENTS.md completely;
- inspect current Git state;
- inspect relevant live GCP state.

You have authorization to modify repository files and the live synthetic Next Shift Google Cloud project where necessary to satisfy this phase.

Use real commands, real deployments, real verification, and authoritative state.

Do not merely write recommendations if you can safely implement and verify the improvement.

Do not change Git branches.
Do not commit.
Do not push.
Do not merge.
Do not create a pull request.
The outer controller handles Git.

Create the required evidence file for this phase.

At the very end of your final response, output exactly one of:

PHASE_RESULT: PASS

or

PHASE_RESULT: BLOCKED

Do not output PASS unless the phase is genuinely complete and verified.
PROMPT
    } > "${prompt_file}"

    codex exec \
        --ask-for-approval never \
        --sandbox danger-full-access \
        --output-last-message "${last_message}" \
        "$(cat "${prompt_file}")" \
        2>&1 | tee "${phase_log}"

    codex_rc=${PIPESTATUS[0]}

    if [[ "${codex_rc}" -ne 0 ]]; then
        update_status "${phase}" "FAILED" "$(git rev-parse --short HEAD)"
        log "Codex process failed for ${phase}: rc=${codex_rc}"
        exit 1
    fi

    if [[ "$(git branch --show-current)" != "${BRANCH}" ]]; then
        log "Codex changed branches during ${phase}. Aborting."
        exit 1
    fi

    evidence="${EVIDENCE_DIR}/${phase}.md"

    if [[ ! -f "${evidence}" ]]; then
        update_status "${phase}" "FAILED" "$(git rev-parse --short HEAD)"
        log "Required evidence file missing for ${phase}"
        exit 1
    fi

    if ! grep -Fq 'PHASE_RESULT: PASS' "${evidence}"; then
        update_status "${phase}" "BLOCKED" "$(git rev-parse --short HEAD)"
        log "Evidence file did not declare PASS for ${phase}"
        exit 1
    fi

    if ! grep -Fq 'PHASE_RESULT: PASS' "${last_message}"; then
        update_status "${phase}" "BLOCKED" "$(git rev-parse --short HEAD)"
        log "Codex final response did not declare PASS for ${phase}"
        exit 1
    fi

    if ! readiness_gate "${phase}"; then
        update_status "${phase}" "FAILED_READINESS" "$(git rev-parse --short HEAD)"

        git add -A
        if ! git diff --cached --quiet; then
            git commit -m "Record autonomous ${phase} readiness failure"
            git push origin "${BRANCH}"
        fi

        exit 1
    fi

    update_status "${phase}" "COMPLETE" "pending"

    git add -A

    if ! git diff --cached --quiet; then
        git commit -m "Complete autonomous ${phase}"
    fi

    phase_commit="$(git rev-parse --short HEAD)"
    update_status "${phase}" "COMPLETE" "${phase_commit}"

    git add "${STATUS_FILE}"

    if ! git diff --cached --quiet; then
        git commit --amend --no-edit
        phase_commit="$(git rev-parse --short HEAD)"
        update_status "${phase}" "COMPLETE" "${phase_commit}"
        git add "${STATUS_FILE}"
        git commit --amend --no-edit
    fi

    git push --force-with-lease origin "${BRANCH}" || exit 1

    log "COMPLETE ${phase} @ $(git rev-parse HEAD)"
done

log "All autonomous phases complete."
log "Running final branch readiness gate."

if ! readiness_gate "FINAL"; then
    log "Final branch readiness failed."
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    git add -A
    git commit -m "Finalize autonomous attack status"
    git push origin "${BRANCH}" || exit 1
fi

log "Creating final PR if needed."

existing_pr="$(
    gh pr list \
        --repo Paddyboy76/next-shift \
        --head "${BRANCH}" \
        --base main \
        --state open \
        --json number \
        --jq '.[0].number // empty'
)"

if [[ -z "${existing_pr}" ]]; then
    gh pr create \
        --repo Paddyboy76/next-shift \
        --base main \
        --head "${BRANCH}" \
        --title "Complete autonomous Next Shift final attack" \
        --body "Autonomous Missions 07-15 and final acceptance completed against the live synthetic Next Shift deployment. Each mission includes evidence under docs/autonomy/evidence/. Final readiness passed before merge."

    existing_pr="$(
        gh pr list \
            --repo Paddyboy76/next-shift \
            --head "${BRANCH}" \
            --base main \
            --state open \
            --json number \
            --jq '.[0].number // empty'
    )"
fi

if [[ -z "${existing_pr}" ]]; then
    log "Unable to resolve final PR number."
    exit 1
fi

log "Final PR is #${existing_pr}. Performing gated automatic merge."

gh pr merge "${existing_pr}" \
    --repo Paddyboy76/next-shift \
    --merge \
    --delete-branch=false || exit 1

log "PR merged. Verifying authoritative main."

git checkout main || exit 1
git fetch origin || exit 1
git reset --hard origin/main || exit 1

FINAL_LOG="${LOG_ROOT}/post-merge-readiness.log"

bash ./verify_readiness.sh 2>&1 | tee "${FINAL_LOG}"
final_rc=${PIPESTATUS[0]}

final_pass="$(grep -c '^PASS  ' "${FINAL_LOG}" || true)"
final_warn="$(grep -c '^WARN  ' "${FINAL_LOG}" || true)"
final_fail="$(grep -c '^FAIL  ' "${FINAL_LOG}" || true)"

log "POST_MERGE PASS=${final_pass} WARN=${final_warn} FAIL=${final_fail} RC=${final_rc}"

if [[ "${final_rc}" -ne 0 || "${final_warn}" -ne 0 || "${final_fail}" -ne 0 || "${final_pass}" -lt 159 ]]; then
    log "POST-MERGE READINESS FAILED. Manual inspection required."
    exit 1
fi

printf '%s\n' \
    "NEXT_SHIFT_AUTONOMOUS_FINAL_ATTACK=PASS" \
    "MAIN=$(git rev-parse HEAD)" \
    "PASS=${final_pass}" \
    "WARN=${final_warn}" \
    "FAIL=${final_fail}" \
    "COMPLETED=$(timestamp)" \
    | tee "${LOG_ROOT}/FINAL_SUCCESS.txt"

log "NEXT SHIFT AUTONOMOUS FINAL ATTACK COMPLETE."
exit 0
