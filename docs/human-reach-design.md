# Human Reach

Human Reach is Next Shift's cross-cutting human-delivery capability.

It makes operational work visible and actionable to frontline humans without giving operational specialists broad messaging authority or allowing a human completion claim to bypass trusted evidence and independent verification.

## Core distinction

Delivery is not acknowledgement.

Acknowledgement is not completion.

A human completion claim is not trusted evidence.

Trusted evidence is not verified closure.

```text
specialist reaches ACTION_PENDING
        ↓
State Authority creates durable DeliveryRequest
        ↓
versioned Pub/Sub event
        ↓
Human Reach resolves an allowlisted destination
        ↓
Google Chat work card delivered
        ↓
DELIVERED
        ↓
ACKNOWLEDGED / BLOCKED / COMPLETION_CLAIMED
        ↓
separate trusted evidence
        ↓
VERIFYING
        ↓
independent verifier
        ↓
CLOSED
```

## DeliveryRequest v1

State Authority owns the durable delivery record. The channel-neutral contract contains:

- delivery_id
- issue_id
- schema_version
- owner / routing_key
- who
- what
- where
- work_order
- issue_title
- issue_description
- workflow_state
- delivery_status
- requested_at

No Google Chat space, user email, or other channel-specific recipient is selected by an agent or stored in the issue proposal.

## Recipient resolution

The Human Reach runtime resolves `routing_key` to a Google Chat named-space display name using `HUMAN_REACH_ROUTES_JSON` supplied at deployment time.

The runtime lists only spaces that the configured Next Shift Chat app is already a member of and requires exactly one exact display-name match. A missing or ambiguous destination fails visibly.

This keeps recipient selection deterministic and allowlisted while avoiding real user addresses or space IDs in source control.

## Google Chat adapter

Google Chat is the only live adapter in the hackathon build.

The Human Reach Cloud Run identity:

- can invoke State Authority;
- can call Google Chat as the configured Chat app;
- has no direct Firestore workflow mutation role;
- cannot close issues;
- cannot record trusted evidence.

Google Chat card actions are limited to:

- Acknowledge
- Blocked
- Completed

`Completed` records `COMPLETION_CLAIMED`. It does not create trusted evidence and does not change the issue to `VERIFYING` or `CLOSED`.

## Acceptance routing

For initial acceptance use two named spaces inside the Workspace organization, for example:

- `Next Shift - Facilities Ops`
- `Next Shift - Patient Flow`

Suggested mapping:

- Facilities, AssetLogistics, EVSThroughput -> Facilities Ops
- LanguageAccess, DischargeDME, PatientTransport -> Patient Flow

This proves deterministic routing without requiring multiple production users. Additional humans can be added to the spaces later.
