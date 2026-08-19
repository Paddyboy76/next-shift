import vertexai

from vertexai import agent_engines
from vertexai import types

from next_shift.agent import root_agent


PROJECT_ID = "next-shift-506004"
LOCATION = "asia-southeast1"
STAGING_BUCKET = "gs://next-shift-506004-agent-staging"


client = vertexai.Client(
    project=PROJECT_ID,
    location=LOCATION,
)

app = agent_engines.AdkApp(
    agent=root_agent,
)


def main() -> None:
    print("Deploying Next Shift to Agent Runtime...")

    remote_agent = client.agent_engines.create(
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

    print("DEPLOYMENT_COMPLETE")
    print(remote_agent)


if __name__ == "__main__":
    main()
