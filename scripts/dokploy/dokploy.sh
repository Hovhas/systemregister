#!/bin/bash
# Dokploy CLI-wrapper mot panel.sundsvall.dev API.
#
# Kräver i miljö:
#   DOKPLOY_URL          — t.ex. https://panel.sundsvall.dev
#   DOKPLOY_API_TOKEN    — API-token från profile settings (ej lösenord)
#
# Läser från .env.local om den finns. Skriver ALDRIG token till stdout.
#
# Om DOKPLOY_APP_ID är satt i env så kan app-ID utelämnas för info/deploy/logs/status.
#
# Användning:
#   scripts/dokploy/dokploy.sh projects               # lista projekt
#   scripts/dokploy/dokploy.sh apps <project-id>      # lista services i projekt
#   scripts/dokploy/dokploy.sh info [app-id]          # info om applikation
#   scripts/dokploy/dokploy.sh deploy [app-id]        # trigga deploy
#   scripts/dokploy/dokploy.sh logs [app-id]          # senaste deploy-loggen
#   scripts/dokploy/dokploy.sh status [app-id]        # applicationStatus + senaste deploy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Läs .env.local om den finns
if [ -f "$REPO_ROOT/.env.local" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$REPO_ROOT/.env.local"
    set +a
fi

: "${DOKPLOY_URL:?Saknar DOKPLOY_URL (sätt i .env.local)}"
: "${DOKPLOY_API_TOKEN:?Saknar DOKPLOY_API_TOKEN (sätt i .env.local)}"

API="${DOKPLOY_URL%/}/api"

api_get() {
    local route="$1"
    shift
    curl -fsS -X GET \
        -H "x-api-key: $DOKPLOY_API_TOKEN" \
        -H "Content-Type: application/json" \
        "$API/$route" "$@"
}

api_post() {
    local route="$1"
    local body="${2:-{\}}"
    curl -fsS -X POST \
        -H "x-api-key: $DOKPLOY_API_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$body" \
        "$API/$route"
}

cmd="${1:-help}"
shift || true

case "$cmd" in
    projects)
        api_get "project.all" | jq -r '.[] | "\(.projectId)\t\(.name)"' 2>/dev/null \
            || api_get "project.all"
        ;;
    apps)
        project_id="${1:?ange project-id}"
        api_get "project.one?projectId=$project_id" \
            | jq -r '.environments[]? | . as $env |
                (.applications[]?   | "app\t\(.applicationId)\t\($env.name)/\(.name)\t\(.applicationStatus)"),
                (.compose[]?        | "cmp\t\(.composeId)\t\($env.name)/\(.name)\t\(.composeStatus)"),
                (.postgres[]?       | "pg \t\(.postgresId)\t\($env.name)/\(.name)\t\(.applicationStatus)")'
        ;;
    info)
        app_id="${1:-${DOKPLOY_APP_ID:?ange app-id eller sätt DOKPLOY_APP_ID}}"
        api_get "application.one?applicationId=$app_id"
        ;;
    deploy)
        app_id="${1:-${DOKPLOY_APP_ID:?ange app-id eller sätt DOKPLOY_APP_ID}}"
        echo "Triggering deploy för $app_id ..." >&2
        api_post "application.deploy" "{\"applicationId\":\"$app_id\"}"
        echo "" >&2
        echo "Deploy triggad. Följ med: $0 status" >&2
        ;;
    logs)
        app_id="${1:-${DOKPLOY_APP_ID:?ange app-id eller sätt DOKPLOY_APP_ID}}"
        api_get "application.one?applicationId=$app_id" \
            | jq -r '.deployments[0:5][]? | "\(.createdAt)\t\(.status)\t\(.logPath // "(ingen log)")"'
        echo ""
        echo "Öppna i Dokploy-UI för full log: $DOKPLOY_URL/dashboard/project"
        ;;
    status)
        app_id="${1:-${DOKPLOY_APP_ID:?ange app-id eller sätt DOKPLOY_APP_ID}}"
        api_get "application.one?applicationId=$app_id" \
            | jq '{name, applicationStatus, buildType, sourceType, branch, repository, lastDeployStatus: .deployments[0].status, lastDeployAt: .deployments[0].createdAt}'
        ;;
    help|*)
        sed -n '2,14p' "$0" | sed 's/^# \?//'
        ;;
esac
