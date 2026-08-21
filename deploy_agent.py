import vertexai

from vertexai import agent_engines
from vertexai import types

from next_shift.agent import root_agent


PROJECT_ID = "next-shift-506004"
PROJECT_NUMBER = "963749706976"
LOCATION = "asia-southeast1"
STAGING_BUCKET = "gs://next-shift-506004-agent-staging"
REASONING_ENGINE_ID = "8140616966286082048"
RESOURCE_NAME = (
    f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/"
    f"reasoningEngines/{REASONING_ENGINE_ID}"
)


client = vertexai.Client(
    project=PROJECT_ID,
    location=LOCATION,
)

app = agent_engines.AdkApp(
    agent=root_agent,
)


def main() -> None:
    print("Updating existing Next Shift Agent Runtime...")
    print(f"RESOURCE_NAME={RESOURCE_NAME}")

    remote_agent = client.agent_engines.update(
        name=RESOURCE_NAME,
        agent=app,
        config={
            "display_name": "Next Shift",
            "requirements": [
                "google-cloud-aiplatform[agent_engines,adk]==1.165.0",
                "cloudpickle==3.1.2",
                "pydantic",
            ],
            "staging_bucket": STAGING_BUCKET,
            "identity_type": types.IdentityType.AGENT_IDENTITY,
        },
    )

    print("UPDATE_COMPLETE")
    print(remote_agent)


if __name__ == "__main__":
    main()
