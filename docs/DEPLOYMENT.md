# Deployment (prepared, not yet done)

> No hosted URL exists yet. Don't list one in the submission until it is deployed and tested.

## Frontend → Vercel

1. Import the GitHub repo in Vercel and set **Root Directory** to `frontend` (framework auto-detects Next.js).
2. Environment variable: `NEXT_PUBLIC_API_URL=https://<your-backend-host>`.
3. Deploy. `npm run build` passes locally.

## Backend → container host (Render, Railway, Fly.io, Cloud Run, Azure Container Apps…)

`backend/Dockerfile` is provided:

```powershell
docker build -t mykshema-api ./backend
docker run -p 8000:8000 -e MYKSHEMA_CORS_ORIGINS=https://<your-vercel-app>.vercel.app mykshema-api
```

Recommended environment for a hosted **demo**:

```
MYKSHEMA_CORS_ORIGINS=https://<app>.vercel.app
MYKSHEMA_CORS_ORIGIN_REGEX=https://.*\.vercel\.app      # optional, for preview deployments
MYKSHEMA_TOKEN_SECRET=<long random string>
MYKSHEMA_AUTO_SEED=true
# MYKSHEMA_STORAGE=memory   # if the filesystem is read-only
# OPENAI_API_KEY=...        # optional
```

### Important: storage on cloud hosts

Local JSON files and the `uploads/` folder live on the container's disk. On most hosts that disk is **ephemeral**: data resets on every restart or redeploy, and multiple instances don't share it. That's acceptable for a seeded demo (it auto-seeds on start) and **unacceptable for real patient data**. Keep real patient data disabled. Run one instance. For persistence, attach a volume or move to the PostgreSQL + object storage plan in [POSTGRES_MIGRATION.md](POSTGRES_MIGRATION.md).

## Publishing to GitHub (manual commands)

The remote `https://github.com/chandrra111/MyKshema` was empty when inspected. From the project root:

```powershell
git remote add origin https://github.com/chandrra111/MyKshema.git
git push -u origin main
```

If authentication fails, sign in with Git Credential Manager (a browser prompt) or create a personal access token with `repo` scope, then push again. Never force-push over existing remote work. If the remote gained commits in the meantime, run `git pull --rebase origin main` first and review.
