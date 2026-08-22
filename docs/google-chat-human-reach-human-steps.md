# Human steps for Google Chat Human Reach

After `deploy_human_reach.sh` completes successfully, use the Google Cloud Console and Google Chat UI to finish the one-time app registration and routing-space setup.

1. Select project `next-shift-506004` in Google Cloud Console.
2. Open **APIs & Services → Google Chat API → Configuration**.
3. Configure a native HTTP Chat app (not a Workspace add-on).
4. App name: `Next Shift Human Reach`.
5. Description: `Synthetic frontline operational work delivery for Next Shift.`
6. Enable **Join spaces and group conversations**.
7. Choose **HTTP endpoint URL** and **Use a common HTTP endpoint URL for all triggers**.
8. Paste the exact root `HUMAN_REACH_URL` printed by the deployment script. Do not append a path.
9. Under Visibility, make the app available to the Workspace-domain tester account(s) used for acceptance.
10. Enable error logging and save.
11. In Google Chat, create exactly `Next Shift - Facilities Ops` and `Next Shift - Patient Flow`.
12. Add the `Next Shift Human Reach` app to both spaces.
13. The app must be a member of both spaces before the asynchronous Human Reach sender can list and resolve them under `chat.bot` app authentication.
14. A personal external Google account is optional. The first acceptance should use Workspace trusted testers so external-membership policy cannot block the test.
