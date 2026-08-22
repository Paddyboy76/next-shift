import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "services" / "human_reach_runtime"
DEPLOY = ROOT / "deploy_human_reach.sh"
ENTRYPOINT = RUNTIME_DIR / "entrypoint.py"

if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

import auth  # noqa: E402


AUDIENCE = (
    "https://next-shift-human-reach-"
    "mycnigy7dq-as.a.run.app"
)
PUSH_SA = (
    "ns-push-human-reach@"
    "next-shift-506004.iam.gserviceaccount.com"
)


class HumanReachDrsAuthTests(unittest.TestCase):
    def env(self):
        return patch.dict(
            os.environ,
            {
                "HUMAN_REACH_AUDIENCE": AUDIENCE,
                "PUBSUB_PUSH_SERVICE_ACCOUNT": PUSH_SA,
            },
            clear=False,
        )

    def test_chat_accepts_only_google_chat_identity(self) -> None:
        claims = {
            "email": "chat@system.gserviceaccount.com",
            "email_verified": True,
        }

        with self.env(), patch.object(
            auth.id_token,
            "verify_oauth2_token",
            return_value=claims,
        ) as verify:
            self.assertTrue(
                auth.authorize_chat_request(
                    "Bearer signed-chat-token"
                )
            )

        self.assertEqual(
            verify.call_args.args[2],
            AUDIENCE,
        )

        claims["email"] = PUSH_SA

        with self.env(), patch.object(
            auth.id_token,
            "verify_oauth2_token",
            return_value=claims,
        ):
            self.assertFalse(
                auth.authorize_chat_request(
                    "Bearer signed-push-token"
                )
            )

    def test_pubsub_accepts_only_exact_push_identity(self) -> None:
        claims = {
            "email": PUSH_SA,
            "email_verified": True,
        }

        with self.env(), patch.object(
            auth.id_token,
            "verify_oauth2_token",
            return_value=claims,
        ):
            self.assertTrue(
                auth.authorize_pubsub_request(
                    "Bearer signed-push-token"
                )
            )

        claims["email"] = "chat@system.gserviceaccount.com"

        with self.env(), patch.object(
            auth.id_token,
            "verify_oauth2_token",
            return_value=claims,
        ):
            self.assertFalse(
                auth.authorize_pubsub_request(
                    "Bearer signed-chat-token"
                )
            )

    def test_invalid_bearer_fails_closed(self) -> None:
        with self.env(), patch.object(
            auth.id_token,
            "verify_oauth2_token",
            side_effect=ValueError("bad token"),
        ):
            self.assertFalse(
                auth.authorize_chat_request(
                    "Bearer bad"
                )
            )
            self.assertFalse(
                auth.authorize_pubsub_request(
                    "Bearer bad"
                )
            )

        with self.env():
            self.assertFalse(
                auth.authorize_chat_request(None)
            )
            self.assertFalse(
                auth.authorize_pubsub_request(
                    "Basic nope"
                )
            )

    def test_email_must_be_verified(self) -> None:
        claims = {
            "email": "chat@system.gserviceaccount.com",
            "email_verified": False,
        }

        with self.env(), patch.object(
            auth.id_token,
            "verify_oauth2_token",
            return_value=claims,
        ):
            self.assertFalse(
                auth.authorize_chat_request(
                    "Bearer signed-chat-token"
                )
            )

    def test_entrypoint_protects_chat_and_pubsub_paths(self) -> None:
        source = ENTRYPOINT.read_text(encoding="utf-8")

        self.assertIn(
            "authorize_chat_request",
            source,
        )
        self.assertIn(
            "authorize_pubsub_request",
            source,
        )
        self.assertIn(
            'request.path in {"/", "/chat"}',
            source,
        )
        self.assertIn(
            'request.path == "/pubsub"',
            source,
        )
        self.assertIn(
            '"chat_authentication_required"',
            source,
        )
        self.assertIn(
            '"pubsub_authentication_required"',
            source,
        )

    def test_deploy_uses_drs_safe_invoker_mode(self) -> None:
        source = DEPLOY.read_text(encoding="utf-8")

        self.assertIn(
            "--no-invoker-iam-check",
            source,
        )
        self.assertIn(
            "HUMAN_REACH_AUDIENCE=${HUMAN_REACH_URL}",
            source,
        )
        self.assertIn(
            "PUBSUB_PUSH_SERVICE_ACCOUNT=${PUSH_SA}",
            source,
        )
        self.assertIn(
            "HUMAN_REACH_APP_LEVEL_OIDC_OK=1",
            source,
        )
        self.assertNotIn(
            "chat@system.gserviceaccount.com",
            source,
        )


if __name__ == "__main__":
    unittest.main()
