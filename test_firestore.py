from next_shift.handover_store import (
    create_issue,
    get_issue,
    transition_issue,
)


issue = create_issue(
    title="Room 1204 air conditioner unresolved",
    description=(
        "Air conditioner remains broken from the previous shift. "
        "Facilities was contacted but attendance is not confirmed."
    ),
    source_type="handover_note",
    source_reference="synthetic-demo-001",
    owner="Facilities",
    human_approval_required=False,
)

print("CREATED")
print(issue)

issue_id = issue["id"]

updated = transition_issue(
    issue_id=issue_id,
    new_state="TRIAGED",
    actor="next_shift",
    reason="Operational facilities issue identified",
)

print("\nTRIAGED")
print(updated)

stored = get_issue(issue_id)

print("\nREAD_BACK")
print(stored)
