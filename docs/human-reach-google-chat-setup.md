# Next Shift Human Reach — Google Chat setup

This is the one-time human configuration required after `deploy_human_reach.sh` succeeds.

## 1. Use the canonical project

Google Cloud project:

`next-shift-506004`

The deployment script prints the private Cloud Run service URL as:

`HUMAN_REACH_URL=...`

Use that exact root URL for the Chat app HTTP endpoint.

## 2. Configure Google Chat API

In Google Cloud Console:

1. Open **APIs & Services → Google Chat API**.
2. Open **Configuration**.
3. If the page offers **Build this Chat app as a Google Workspace add-on**, disable that option. Next Shift uses the native HTTP Chat app model.
4. App name: **Next Shift Human Reach**.
5. Description: **Synthetic frontline operational work delivery for Next Shift.**
6. Avatar: use a non-proprietary/synthetic Next Shift icon URL. A temporary neutral public icon is acceptable for acceptance testing.
7. Under **Functionality**, enable **Join spaces and group conversations**.
8. Under **Connection settings**, choose **HTTP endpoint URL**.
9. Under **Triggers**, choose **Use a common HTTP endpoint URL for all triggers**.
10. Paste the exact root `HUMAN_REACH_URL` printed by the deployment script. Do not append `/chat` or `/pubsub`.
11. Under **Visibility**, choose **Make this Chat app available to specific people and groups in your domain** and add the Workspace account used for acceptance testing. Add another Workspace-domain tester if desired.
12. Enable **Log errors to Logging**.
13. Save.

The Cloud Run service remains private. `deploy_human_reach.sh` grants `roles/run.invoker` only to the dedicated Pub/Sub push identity and `chat@system.gserviceaccount.com` for Chat interaction events.

## 3. Create the two synthetic routing spaces

In Google Chat using the trusted Workspace tester account, create exactly these named spaces:

- `Next Shift - Facilities Ops`
- `Next Shift - Patient Flow`

Names must match exactly because Human Reach intentionally fails closed if it finds zero or multiple exact matches.

## 4. Add the Chat app to each space

For each space:

1. Open the space.
2. Add apps / manage members and apps.
3. Search for **Next Shift Human Reach**.
4. Add the app.

The app must be a member before app-authenticated `spaces.list` and message creation can see/use that destination.

## 5. Routing contract

The default acceptance routing is:

Facilities → `Next Shift - Facilities Ops`
AssetLogistics → `Next Shift - Facilities Ops`
EVSThroughput → `Next Shift - Facilities Ops`
LanguageAccess → `Next Shift - Patient Flow`
DischargeDME → `Next Shift - Patient Flow`
PatientTransport → `Next Shift - Patient Flow`

The deploy script passes this map as `HUMAN_REACH_ROUTES_JSON`. No user email addresses or Chat space IDs are committed to Git.

## 6. Personal Google account is optional

Do not make an external personal Gmail account a prerequisite for acceptance. Unpublished interactive Chat apps are shared to trusted testers in the Workspace organization. If Workspace external-space policy allows the personal account to join one of the named spaces, it can be used as a secondary observer/tester later, but the core routing proof is the two-space owner map above.

## 7. Acceptance signal

After the app is in both spaces, submit a small synthetic handover with at least one owner from each routing group. Expected behavior:

- specialist reaches `ACTION_PENDING`
- State Authority creates one durable Human Reach delivery record
- Human Reach sends exactly one card to the correct named space
- delivery becomes `DELIVERED`
- `Acknowledge` changes Human Reach status to `ACKNOWLEDGED`
- `Completed` changes Human Reach status to `COMPLETION_CLAIMED`
- completion claim does not close the operational issue
- trusted evidence is still required for `VERIFYING`
- independent verifier still owns `VERIFYING → CLOSED`

Responder identity persisted in Firestore is pseudonymous; real tester account identity is not stored in synthetic operational truth.
