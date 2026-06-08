"""
Functions to get GitHub responses using the secure native auth path.

This uses the authenticated GitHub CLI session when available, which works for
private repositories without requiring a personal access token in the code.
"""

import base64
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import requests

# Load .env file if it exists (overrides system env vars; in Codespaces without
# a .env file, Codespace secrets are used directly)
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.is_file():
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=True)


def _run_gh_api(path, *, paginate=False):
    cmd = ["gh", "api"]
    if paginate:
        cmd.append("--paginate")
    cmd.append(path)

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gh api failed")

    text = result.stdout.strip()
    if not text:
        return []

    return json.loads(text)


class GhContent(SimpleNamespace):
    @property
    def decoded_content(self):
        content = getattr(self, "content", None)
        if content:
            return base64.b64decode(content.encode("utf-8"))

        download_url = getattr(self, "download_url", None)
        if download_url:
            response = requests.get(download_url, timeout=60)
            response.raise_for_status()
            return response.content

        return b""


class GhRepoAdapter:
    def __init__(self, repo_name):
        self.full_name = repo_name
        self.name = repo_name.split("/")[-1]
        meta = _run_gh_api(f"repos/{repo_name}")
        self._meta = meta
        self.private = bool(meta.get("private", False))

    def get_contents(self, path, ref="HEAD"):
        response = _run_gh_api(f"repos/{self.full_name}/contents/{path}?ref={ref}")
        if isinstance(response, list):
            return [GhContent(**item) for item in response]
        return GhContent(**response)

    def get_pulls(self, state="open", sort="updated", direction="desc"):
        items = _run_gh_api(
            f"repos/{self.full_name}/pulls?state={state}&sort={sort}&direction={direction}"
        )

        def normalize(item):
            created_at = item.get("created_at")
            updated_at = item.get("updated_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

            return SimpleNamespace(
                number=item.get("number"),
                title=item.get("title"),
                user=SimpleNamespace(login=item.get("user", {}).get("login") if isinstance(item.get("user"), dict) else None),
                state=item.get("state"),
                draft=item.get("draft", False),
                created_at=created_at,
                updated_at=updated_at,
                html_url=item.get("html_url"),
                labels=[SimpleNamespace(name=label.get("name")) for label in item.get("labels", [])],
                requested_reviewers=[SimpleNamespace(login=user.get("login")) for user in item.get("requested_reviewers", [])],
                requested_teams=[SimpleNamespace(slug=team.get("slug")) for team in item.get("requested_teams", [])],
                assignees=[SimpleNamespace(login=user.get("login")) for user in item.get("assignees", [])],
                mergeable=item.get("mergeable"),
                body=item.get("body"),
            )

        return [normalize(item) for item in items]


# function to connect to GitHub repo
def connect_repo(repo_name):
    try:
        return GhRepoAdapter(repo_name)
    except Exception as exc:
        print("Error connecting to repo via GitHub CLI auth.")
        print(exc)
        raise


def get_auth_response(url):
    path = url.replace("https://api.github.com/", "", 1)
    return _run_gh_api(path, paginate=True)

# test the functions
if __name__ == "__main__":
    # get the files in the repo
    # print ("Testing get_auth_response")
    # files = get_auth_response("https://api.github.com/repos/sdgilley/learn-tools/git/trees/main?recursive=1")
    # # print the first 5 files
    # for file in files[:5]:
    #     print(file["path"])
    # print(f"Total files: {len(files)}")
    # print("Done")

    print ("Testing connect_repo")
    repo = connect_repo("MicrosoftDocs/azure-docs")
    print(repo.name)
