# The review desk on Azure App Service

The public demo at https://inbox-helper-quest-b108.azurewebsites.net runs the same code as
`uv run inbox-helper serve --set unseen --try-hosted`. These are the commands
it was deployed with, on 15 November 2026.

- **Plan.** App Service B1, Linux, West US 3. East US 2 and Central US had no
  App Service quota on this subscription, and the free tier had none either.
- **Identity.** The app has a system-assigned managed identity with one role,
  **Foundry Agent Consumer**, on the Foundry resource. It can invoke the agent
  and nothing else. There are no keys.
- **State.** In memory, one process, one instance. A restart resets the desk.
- **Access.** No password. The data is synthetic and nothing leaves the app, so
  the desk asks only for a name, which is recorded against each decision. The
  app is started with `--public` to make that an explicit choice.
- **Limits.** At most 40 live messages a day, one every few seconds.

```bash
az appservice plan create -g rg-inbox-helper-quest -n plan-inbox-helper --location westus3 --is-linux --sku B1
```

```bash
az webapp create -g rg-inbox-helper-quest -p plan-inbox-helper -n inbox-helper-quest-b108 --runtime "PYTHON:3.13" --https-only true --assign-identity "[system]"
```

```bash
az role assignment create --assignee-object-id <app principal id> --assignee-principal-type ServicePrincipal --role "Foundry Agent Consumer" --scope <Foundry resource id>
```

```bash
az webapp config appsettings set -g rg-inbox-helper-quest -n inbox-helper-quest-b108 --settings FOUNDRY_PROJECT_ENDPOINT=<project endpoint> INBOX_HELPER_AGENT_NAME=inbox-helper INBOX_HELPER_LIVE_CAP=40 INBOX_HELPER_SESSION_SECRET=<random> SCM_DO_BUILD_DURING_DEPLOYMENT=true PYTHONPATH=src WEBSITES_PORT=8000
```

```bash
az webapp config set -g rg-inbox-helper-quest -n inbox-helper-quest-b108 --always-on true --startup-file "python -m inbox_helper.cli serve --host 0.0.0.0 --port 8000 --set unseen --try-hosted --public"
```

The package is `src/`, `data/inbox/`, `data/policy/`, `data/recordings/*.json`,
`evals/rubric.md` and a `requirements.txt` exported from the lock file with
`uv export --no-dev --no-hashes --no-emit-project`. App Service builds it on
upload:

```bash
az webapp deploy -g rg-inbox-helper-quest -n inbox-helper-quest-b108 --src-path app.zip --type zip --track-status true
```

To take it down after the review:

```bash
az webapp delete -g rg-inbox-helper-quest -n inbox-helper-quest-b108 && az appservice plan delete -g rg-inbox-helper-quest -n plan-inbox-helper --yes
```
