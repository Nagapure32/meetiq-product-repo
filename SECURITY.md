# Security Policy

Do not commit real `.env` files, service role keys, publish profiles, API keys, connection strings, or OAuth secrets.

Use GitHub Actions secrets and Azure Key Vault for deployed values. Rotate any secret that was previously committed before production deployment.
