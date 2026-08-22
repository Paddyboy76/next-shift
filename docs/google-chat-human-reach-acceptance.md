# Google Chat Human Reach acceptance

This is the one-time live setup and acceptance sequence for the hackathon build.

## 1. Deploy the runtime first

Run `deploy_human_reach.sh` from the canonical repo. The final output prints the private Cloud Run URL to use for the Google Chat app HTTP endpoint.

Do not submit a new Next Shift handover until the Chat app and both routing spaces are ready.

## 2. Configure the Google Chat app

In Google Cloud Console, project `next-shift-506004`:

1. Open **Google Chat API -> Configuration**.
2. If shown, disable **Build this Chat app as a Google Workspace add-on**. Human Reach uses Chat API interaction events directly.
3. App name: `Next Shift Human Reach`.
4. Use a temporary square HTTPS avatar during engineering acceptance; replace it with the final Next Shift asset during product polish.
5. Description: `Frontline operations delivery`.
6. Enable interactive features.
7. Enable **Join spaces and group conversations**.
8. Connection: **HTTP endpoint URL**.
9. Use the Human Reach Cloud Run service root URL printed by the deploy script as the common HTTP endpoint for all triggers.
10. Authentication audience: **HTTP endpoint URL**.
11. Visibility: make the unpublished app available to the Workspace business account used for testing.
12. Enable Chat error logging.
13. Save.

The deployment script grants Google Chat's service identity permission to invoke the otherwise private Cloud Run service.

## 3. Create the two synthetic routing spaces

Using the Workspace business account in Google Chat, create two named spaces with these exact display names:

- `Next Shift - Facilities Ops`
- `Next Shift - Patient Flow`

Add `Next Shift Human Reach` to both spaces. The app should post its onboarding message when added.

The default deterministic routing map is:

- Facilities -> Facilities Ops
- AssetLogistics -> Facilities Ops
- EVSThroughput -> Facilities Ops
- LanguageAccess -> Patient Flow
- DischargeDME -> Patient Flow
- PatientTransport -> Patient Flow

The live service resolves exact display-name matches only among spaces that the Chat app has access to. No real user email or Chat space ID is committed to source control.

## 4. Optional second-account test

The business Workspace account is sufficient to prove owner-to-space routing.

If Workspace external-member policy permits it, the personal Google account can be added to one of the synthetic spaces as an additional observer/tester. Do not make the acceptance depend on this: unpublished interactive Chat app testing is scoped to trusted Workspace-domain testers.

When a human clicks a Human Reach card button, Next Shift does not persist their real Chat account identity. State Authority stores a stable pseudonymous responder fingerprint and the label `Frontline responder`.

## 5. Readiness check

After the app is a member of both spaces, proxy the private service and call `/ready`:

```bash
cd /home/patrick/next-shift || exit 1
source /home/patrick/next-shift/.venv/bin/activate

gcloud run services proxy next-shift-human-reach \
  --project=next-shift-506004 \
  --region=asia-southeast1 \
  --port=8088 >/tmp/next-shift-human-reach-proxy.log 2>&1 &
PROXY_PID=$!
trap 'kill "${PROXY_PID}" 2>/dev/null || true' EXIT
sleep 4
curl -fsS http://127.0.0.1:8088/ready | python -m json.tool
kill "${PROXY_PID}" 2>/dev/null || true
trap - EXIT
```

Expected status: `ready`, with all six owners resolved to one of the two named spaces.

## 6. Routing acceptance handover

Use a fresh synthetic room so the test is easy to distinguish from earlier acceptance records:

```text
Evening operations handover for Ward 6A.

The sink in Room 614 is leaking underneath the basin and Facilities still needs to repair it.

Patient Transport is needed to take the patient from Room 614 to the Discharge Lounge by wheelchair when ready.

Neither item has been confirmed complete.
```

Expected:

- one Facilities issue reaches ACTION_PENDING and a work card appears in `Next Shift - Facilities Ops`;
- one PatientTransport issue reaches ACTION_PENDING and a work card appears in `Next Shift - Patient Flow`;
- each card visibly contains WHO / WHAT / WHERE / WORK ORDER;
- each delivery is recorded independently from workflow state.

## 7. Human-state acceptance

On one work card:

1. Click **Acknowledge**.
2. Verify the card changes to acknowledged.
3. Click **Completed**.
4. Verify the card explicitly says completion is only claimed and trusted evidence plus independent verification are still required.

The operational issue must remain `ACTION_PENDING` after the human completion claim.

Then use the separate trusted-evidence and independent-verifier path to prove:

```text
COMPLETION_CLAIMED
is not
CLOSED

ACTION_PENDING
-> trusted evidence
-> VERIFYING
-> independent verifier
-> CLOSED
```

That separation is the core Human Reach acceptance criterion.
