"""
Functions to get and use authenticated responses from GitHub

You'll need to set the GH_ACCESS_TOKEN environment variable for this to work.
See https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
to create a token.  Then add the token to an environment variable called GH_ACCESS_TOKEN.
"""

# function to connect to GitHub repo
def connect_repo(repo_name):
    import os
    import sys
    from github import Github

    try:
        token = os.environ["GH_ACCESS_TOKEN"]
    except:
        print("Please set GH_ACCESS_TOKEN environment variable")
        print(
            "See https://github.com/sdgilley/learn-tools/blob/main/create-update-auth.md"
        )
        sys.exit()
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
    except:
        print("Error connecting to repo.  Make sure your access token is still valid.")
        print(token)
        print(
            "See https://github.com/sdgilley/learn-tools/blob/main/create-update-auth.md"
        )
        sys.exit()
    return repo


def get_auth_response(url):
    import requests
    import sys
    import os

    # *** AUTHENTICATE
    # Get GH access token from environment variables (assumes you've exported this)
    # try to read GH_ACCESS_TOKEN from environment variables
    # if not there, tell user to set it
    try:
        token = os.environ["GH_ACCESS_TOKEN"]
    except:
        print("Please set GH_ACCESS_TOKEN environment variable")
        sys.exit()

    # The headers for your request
    headers = {
        "Authorization": f"token {token}",
    }
    files = []

    while url:
        response = requests.get(url, headers=headers)
        files.extend(response.json())
        url = response.links["next"]["url"] if "next" in response.links else None

    return files

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
