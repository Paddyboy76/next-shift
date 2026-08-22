window.addEventListener("load", () => {
  const issueId = new URLSearchParams(window.location.search).get("issue");

  if (!issueId) return;

  if (!/^[A-Za-z0-9_-]{1,128}$/.test(issueId)) {
    console.warn("Ignoring invalid issue deep link");
    return;
  }

  if (typeof openIssue !== "function") {
    console.warn("Issue drawer is not available");
    return;
  }

  openIssue(issueId).catch((error) => {
    console.warn("Unable to open issue deep link", error);
  });
});
