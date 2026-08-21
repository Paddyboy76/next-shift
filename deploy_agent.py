from pathlib import Path

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

ROOT = Path(__file__).resolve().parent
NEXT_SHIFT_PACKAGE = ROOT / "next_shift"

RUNTIME_REQUIREMENTS = [
    "google-cloud-aiplatform[agent_engines,adk]==1.165.0",
    "cloudpickle==3.1.2",
    "pydantic==2.13.4",
    "google-cloud-firestore==2.28.1",
    "google-cloud-pubsub==2.39.0",
]


client = vertexai.Client(
    project=PROJECT_ID,
    location=LOCATION,
)

app = agent_engines.AdkApp(
    agent=root_agent,
)


def main() -> None:
    if not NEXT_SHIFT_PACKAGE.is_dir():
        raise FileNotFoundError(
            f"Missing local agent package: {NEXT_SHIFT_PACKAGE}"
        )

    print("Updating existing Next Shift Agent Runtime...")
    print(f"RESOURCE_NAME={RESOURCE_NAME}")
    print(f"EXTRA_PACKAGE={NEXT_SHIFT_PACKAGE}")

    remote_agent = client.agent_engines.update(
        name=RESOURCE_NAME,
        agent=app,
        config={
            "display_name": "Next Shift",
            "requirements": RUNTIME_REQUIREMENTS,
            "extra_packages": [str(NEXT_SHIFT_PACKAGE)],
            "staging_bucket": STAGING_BUCKET,
            "identity_type": types.IdentityType.AGENT_IDENTITY,
        },
    )

    print("UPDATE_COMPLETE")
    print(remote_agent)


if __name__ == "__main__":
    main()
