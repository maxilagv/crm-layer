# Deploy en Contabo, un solo VPS

Objetivo: publicar `crm-layer` en Ubuntu LTS con una sola superficie publica
(Caddy en 80/443), servicios internos sin puertos publicados, secretos fuertes,
backups diarios y reinicio automatico.

Referencias oficiales: Docker Engine Ubuntu
<https://docs.docker.com/engine/install/ubuntu/> y Caddy
<https://caddyserver.com/docs/install>.

## 1. Endurecer el servidor

Entra por SSH como `root` la primera vez y crea un usuario no-root:

```bash
adduser deploy
usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy
```

Bloquea login por password y root. Edita `/etc/ssh/sshd_config`:

```text
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Aplica firewall, fail2ban y actualizaciones automaticas:

```bash
apt update && apt upgrade -y
apt install -y ufw fail2ban unattended-upgrades git curl ca-certificates
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
dpkg-reconfigure -plow unattended-upgrades
systemctl restart ssh
```

Abre una segunda terminal y confirma que puedes entrar como `deploy` antes de
cerrar la sesion root.

## 2. Instalar Docker

Como `deploy`:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker deploy
newgrp docker
docker run --rm hello-world
```

## 3. Clonar repo y crear `.env.prod`

```bash
mkdir -p ~/apps
cd ~/apps
git clone <REPO_URL> crm-layer
cd crm-layer
cp .env.prod.example .env.prod
chmod 600 .env.prod
```

Genera secretos fuertes y copialos en `.env.prod`:

```bash
python3 - <<'PY'
import secrets
for name, size in [
    ("SECRET_KEY", 64),
    ("JWT_SIGNING_KEY", 48),
    ("WA_BRIDGE_SHARED_SECRET", 48),
    ("POSTGRES_PASSWORD", 32),
    ("WHATSAPP_VERIFY_TOKEN", 32),
]:
    print(f"{name}={secrets.token_urlsafe(size)}")
PY
```

Edita al menos:

```text
DOMAIN=crm.tudominio.com
ACME_EMAIL=admin@tudominio.com
PUBLIC_APP_URL=https://crm.tudominio.com
API_BASE_URL=https://crm.tudominio.com
NEXT_PUBLIC_API_BASE_URL=https://crm.tudominio.com
ALLOWED_HOSTS=crm.tudominio.com
CORS_ALLOWED_ORIGINS=https://crm.tudominio.com
CSRF_TRUSTED_ORIGINS=https://crm.tudominio.com
POSTGRES_PASSWORD=<valor generado>
DATABASE_URL=postgres://ai_crm:<valor generado>@postgres:5432/ai_crm
SECRET_KEY=<valor generado>
JWT_SIGNING_KEY=<valor generado>
WA_BRIDGE_SHARED_SECRET=<valor generado>
ORGANIZATION_ID=<uuid de la organizacion luego del quickstart>
OPENAI_API_KEY=<si vas a habilitar textos OpenAI>
GEMINI_API_KEY=<requerida para clasificacion/bulk>
```

`GOOGLE_CSE_CX` puede quedar vacio; Custom Search queda en no-op hasta cargarlo.

## 4. DNS

En el panel DNS del dominio crea:

```text
Tipo: A
Nombre: crm
Valor: <IP publica del VPS>
TTL: 300
```

Espera propagacion antes de exigir TLS. Caddy pedira y renovara certificados
automaticamente cuando 80/443 lleguen al VPS.

## 5. Levantar produccion

Valida el compose con el env real:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml config >/tmp/crm-compose.yml
```

Construye y levanta:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f --tail=200 api caddy
```

El contenedor `api` corre `migrate` y `collectstatic` antes de iniciar Gunicorn.
Solo `caddy` publica puertos; Postgres y Redis quedan sin `ports`.

## 6. Bootstrap de la app

Crea owner, organizacion, Gemini, prompts y perfil:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec api \
  python manage.py quickstart \
  --email owner@tudominio.com \
  --name "Owner" \
  --organization "Mi Empresa" \
  --password '<password fuerte>' \
  --owner-phone '549...'
```

Copia el UUID de la organizacion a `ORGANIZATION_ID` en `.env.prod` y reinicia
el bridge:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --force-recreate wa-bridge
```

Adopta proveedores y prompts versionados:

```bash
ORG_ID=<uuid>
docker compose --env-file .env.prod -f docker-compose.prod.yml exec api \
  python manage.py ai_setup_providers --organization-id "$ORG_ID"
docker compose --env-file .env.prod -f docker-compose.prod.yml exec api \
  python manage.py ai_seed_prompts --update --organization-id "$ORG_ID"
```

Los flags `auto_reply` y `auto_followup` quedan en `false` por defecto: el bot
sugiere borradores y el owner aprueba. Activalos por campania solo cuando ya
validaste SafetyGuard, topes, horario y opt-out.

## 7. Verificacion

```bash
curl -fsS https://crm.tudominio.com/api/health/live/
curl -fsS https://crm.tudominio.com/api/health/ready/
curl -I https://crm.tudominio.com
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

Revisa que `api`, `worker`, `scheduler`, `web`, `wa-bridge`, `backup`, `redis`,
`postgres` y `caddy` esten `healthy` o corriendo sin reinicios.

## 8. WhatsApp

En la UI, entra a Configuracion > WhatsApp. Escanea el QR del bridge una vez.
La sesion persiste en el volumen `wa-bridge-auth`. No escales `wa-bridge`: debe
existir una sola instancia.

Confirma que el outbox se mueve:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f wa-bridge api worker
```

## 9. Backups y restore

El servicio `backup` corre `pg_dump` diario y conserva
`BACKUP_RETENTION_DAYS`. Forzar un backup:

```bash
make backup
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backup ls -lh /backups
```

Para offsite S3/R2/MinIO, completa:

```text
BACKUP_S3_BUCKET=
BACKUP_S3_PREFIX=crm-layer/postgres
BACKUP_S3_ENDPOINT_URL=
BACKUP_S3_REGION=
BACKUP_S3_ACCESS_KEY_ID=
BACKUP_S3_SECRET_ACCESS_KEY=
```

Restore probado una vez, en ventana de mantenimiento:

```bash
FILE=/backups/postgres-YYYYmmddTHHMMSSZ.sql.gz
docker compose --env-file .env.prod -f docker-compose.prod.yml stop api worker scheduler web wa-bridge
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm backup \
  /scripts/postgres-restore.sh "$FILE"
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

## 10. Operacion diaria

```bash
make prod-up
make prod-logs
make prod-migrate
make prod-down
```

Antes de desplegar cambios:

```bash
make ci
docker compose --env-file .env.prod -f docker-compose.prod.yml config >/tmp/crm-compose.yml
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

Recomendado, no bloqueante: correr `pip-audit` en `apps/api` y `pnpm audit`
cuando no introduzca ruido operativo.

## 11. Cinturones anti-costo

1. En Google Cloud Billing, crea una alerta de presupuesto para el proyecto que
   contiene Places, PageSpeed y Programmable Search.
2. Mantiene los caps in-app: CSE, Apollo, Hunter y daily caps de campania.
3. Si una key se compartio por un canal inseguro, rotala antes del primer uso
   real.

## 12. Incidentes rapidos

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=200 api
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=200 worker
docker compose --env-file .env.prod -f docker-compose.prod.yml restart api worker scheduler
docker compose --env-file .env.prod -f docker-compose.prod.yml exec api python manage.py check --deploy
```

Si TLS falla, revisa DNS A-record, puertos 80/443 en UFW y logs de `caddy`.
