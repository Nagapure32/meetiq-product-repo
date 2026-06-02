# Azure Deployment

This repo deploys the MeetIQ platform:

```text
backend/   FastAPI API
frontend/  Next.js app
```

Azure resources:

- Azure App Service Linux for the FastAPI backend.
- Azure App Service Linux for the Next.js frontend.
- Azure Key Vault for secrets.
- Azure Blob Storage, AI Speech, AI Search, and Azure OpenAI for platform services.
- Self-hosted Supabase on Azure, or a future migration to Azure Database for PostgreSQL plus replacement auth/API services.

The platform talks to the separate Teams bot repo through:

```text
BOT_INTERNAL_API_KEY
TEAMS_BOT_BASE_URL=https://<bot-domain>
```
