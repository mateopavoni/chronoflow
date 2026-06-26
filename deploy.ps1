# deploy.ps1 — actualiza la demo en el server Dokku desde la rama actual.
#
# Uso:
#   ./deploy.ps1          -> deploya api + web
#   ./deploy.ps1 web      -> solo el front
#   ./deploy.ps1 api      -> solo el back
#
# Pushea tu rama LOCAL actual (HEAD) a la rama 'main' de cada app en Dokku,
# que es lo que Dokku buildea y redeploya. No toca GitHub (origin).
param([ValidateSet('all', 'api', 'web')] [string]$target = 'all')

# ponytail: --force porque el remote de Dokku es solo destino de deploy, no fuente
# de verdad; evita "non-fast-forward" cuando rebaseás/amendás en dev. Si algún día
# querés que rechace pushes raros, sacá el --force.
if ($target -in 'all', 'api') {
    Write-Host "==> Deploying API (cf-api)..." -ForegroundColor Cyan
    git push --force cf-api HEAD:main
}
if ($target -in 'all', 'web') {
    Write-Host "==> Deploying WEB (cf-web)..." -ForegroundColor Cyan
    git push --force cf-web HEAD:main
}
