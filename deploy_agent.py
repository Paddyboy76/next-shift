from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

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
PYPROJECT = ROOT / "pyproject.toml"

RUNTIME_REQUIREMENTS = [
    "google-cloud-aiplatform[agent_engines,adk]==1.165.0",
    "cloudpickle==3.1.2",
    "pydantic==2.13.4",
]


client = vertexai.Client(
    project=PROJECT_ID,
    location=LOCATION,
)

app = agent_engines.AdkApp(
    agent=root_agent,
)


def _build_runtime_wheel(work_dir: Path) -> Path:
    source_dir = work_dir / "source"
    wheel_dir = work_dir / "wheel"

    source_dir.mkdir(parents=True)
    wheel_dir.mkdir(parents=True)

    shutil.copy2(
        PYPROJECT,
        source_dir / "pyproject.toml",
    )
    shutil.copytree(
        NEXT_SHIFT_PACKAGE,
        source_dir / "next_shift",
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
        ),
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            str(wheel_dir),
            str(source_dir),
        ],
        cwd=work_dir,
        check=True,
    )

    wheels = sorted(
        wheel_dir.glob("next_shift_runtime-*.whl")
    )

    if len(wheels) != 1:
        raise RuntimeError(
            "Expected exactly one Next Shift runtime wheel, "
            f"found {len(wheels)}"
        )

    return wheels[0]


def _stage_runtime_wheel(wheel_path: Path) -> Path:
    staged_wheel = ROOT / wheel_path.name

    if staged_wheel.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing runtime wheel: {staged_wheel}"
        )

    shutil.copy2(
        wheel_path,
        staged_wheel,
    )

    return staged_wheel


def main() -> None:
    if not NEXT_SHIFT_PACKAGE.is_dir():
        raise FileNotFoundError(
            f"Missing local agent package: {NEXT_SHIFT_PACKAGE}"
        )

    if not PYPROJECT.is_file():
        raise FileNotFoundError(
            f"Missing packaging metadata: {PYPROJECT}"
        )

    print("Updating existing Next Shift Agent Runtime...")
    print(f"RESOURCE_NAME={RESOURCE_NAME}")

    with tempfile.TemporaryDirectory(
        prefix="next-shift-agent-wheel-"
    ) as temp_dir:
        wheel_path = _build_runtime_wheel(
            Path(temp_dir)
        )
        staged_wheel = _stage_runtime_wheel(
            wheel_path
        )

        requirements = [
            *RUNTIME_REQUIREMENTS,
            staged_wheel.name,
        ]

        print(f"RUNTIME_WHEEL={staged_wheel}")

        previous_cwd = Path.cwd()

        try:
            os.chdir(ROOT)

            remote_agent = client.agent_engines.update(
                name=RESOURCE_NAME,
                agent=app,
                config={
                    "display_name": "Next Shift",
                    "requirements": requirements,
                    "extra_packages": [staged_wheel.name],
                    "staging_bucket": STAGING_BUCKET,
                    "identity_type": types.IdentityType.AGENT_IDENTITY,
                },
            )
        finally:
            os.chdir(previous_cwd)
            staged_wheel.unlink(missing_ok=True)

    print("UPDATE_COMPLETE")
    print(remote_agent)


if __name__ == "__main__":
    main()
