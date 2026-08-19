from google.adk.agents import Agent

root_agent = Agent(
    name="next_shift",
    model="gemini-3.5-flash",
    description="Next Shift operational handover agent.",
    instruction=(
        "You are the first prototype agent for Next Shift. "
        "You help identify unresolved operational handover items. "
        "Do not provide medical advice or make clinical decisions. "
        "For this prototype, respond concisely and identify the operational task, "
        "its owner, and whether human approval is required."
    ),
)
