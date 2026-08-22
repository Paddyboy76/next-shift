# Human Reach routing acceptance

Use two named Google Chat spaces for the first live routing proof.

## Facilities Ops route

Owners:
- Facilities
- AssetLogistics
- EVSThroughput

Destination:
- `Next Shift - Facilities Ops`

## Patient Flow route

Owners:
- LanguageAccess
- DischargeDME
- PatientTransport

Destination:
- `Next Shift - Patient Flow`

The destination is resolved by exact display name at send time using Chat app authentication. The Chat app must already be a member of each space.

For initial acceptance, prefer a Workspace-domain trusted tester in both spaces. A personal external Google account is optional and should not be required for the core routing proof.
