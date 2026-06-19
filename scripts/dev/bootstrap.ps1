Copy-Item .env.example .env -ErrorAction SilentlyContinue
pnpm install
Push-Location apps/api
python -m pip install -e ".[dev]"
Pop-Location
docker compose -f docker-compose.local.yml build
