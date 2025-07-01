# Create/update a GitHub access token

The scripts in this repo require the use of a github token to authenticate.  Use these steps to create the token.  When the token expires, redo the same steps to create a new token.

## Create a GitHub token

1. Go to https://github.com/settings/tokens.  Generate a new token (classic). Add a note and pick an expiration date.  Skip all the checkboxes; scroll to the bottom, and click **Generate token**.
1. COPY the token. SAVE it somewhere temporarily.  It's about to go away and you'll need it in a future step.  
1. If you're going to run scripts locally, create or update an environment variable **GH_ACCESS_TOKEN** with this value.
1. To run in a codespace, see next section to save the token in a Codespace secret.
1. Make sure you have stored the copy of the token before going on to the next step.
1. Use **Configure SSO** to authorize **MicrosoftDocs** to use the token.  
    > ⚠️ IMPORTANT! Once you start this step, you'll never see the text of the token again. So make sure you've copied it before you select the dropdown.

### Troubleshooting

If your token doesn't work when you run code, verify that you've configured the SSO: 
 
1. Go to https://github.com/settings/tokens.
1. Select **Configure SSO**.  You should see **Deauthorize** for MicrosoftDocs.  If you see **Authorize**, select it to authorize MicrosoftDocs to use the token.

## Save the token as a Codespace secret

To save/update a Codespace secret:

1. Go to https://github.com/settings/codespaces.
1. Add or update the secret.
    * If adding for the first time
        1. Click **New secret**.  
        1. The secret name is **GH_ACCESS_TOKEN**  The value is the token you copied above.
        1. Dropdown **Select repositories** and add the repo **sdgilley/content-maintenance**.
    * To update GH_ACCESS_TOKEN, click **Update**.  
        * Under **Value** you'll see a sentence saying it can't be displayed.  Click on the **enter a new value** link, then paste in your new token.
    * Select **Save changes**.
    

## Update your codespace

Once you've created or changed the secret or environment variable, you'll need to restart any open Codespaces to use the new token.

If you have a codespace open, it sometimes detects the change and asks you if you want to restart.  If it doesn't, you can restart it manually.  At the bottom left, click on the Codespaces name, then select **Rebuild Container**.

## For local environments

To run the scripts locally, save the token as an environment variable with the name GH_ACCESS_TOKEN.

Close and reopen VS Code to use the new token.

Besides authentication, you also need to `pip install PyGithub` to use the scripts locally.

## Next

Return to [Maintain code snippets in Azure docs](code-snippets.md).