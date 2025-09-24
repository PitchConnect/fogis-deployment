#!/usr/bin/env bash
set -euo pipefail

DATE_INPUT="${1:-2025-08-26}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUTDIR="fogis-deployment/logs/diagnostics/${DATE_INPUT}-${STAMP}"
mkdir -p "${OUTDIR}"

log() { printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*"; }

echo "FOGIS diagnostics for date: ${DATE_INPUT}" | tee "${OUTDIR}/_meta.txt"

# 0) Snapshot status & internal health bodies
log "docker ps snapshot" | tee -a "${OUTDIR}/_meta.txt"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' \
  | tee "${OUTDIR}/docker-ps.txt"

log "Internal /health bodies"
{
  printf "[match-list-processor] "; docker exec match-list-processor sh -lc 'curl -sS -m 6 http://localhost:8000/health || true'; echo
  printf "[fogis-calendar-phonebook-sync] "; docker exec fogis-calendar-phonebook-sync sh -lc 'curl -sS -m 6 http://localhost:5003/health || true'; echo
  printf "[google-drive-service] "; docker exec google-drive-service sh -lc 'curl -sS -m 6 http://localhost:5000/health || true'; echo
  printf "[fogis-api-client-service] "; docker exec fogis-api-client-service sh -lc 'curl -sS -m 6 http://localhost:8080/health || true'; echo
  printf "[team-logo-combiner] "; docker exec team-logo-combiner sh -lc 'curl -sS -m 6 http://localhost:5002/health || true'; echo
} | tee "${OUTDIR}/internal-health.txt"

# 1) Token checks
log "Token presence checks"
{
  echo "[drive] present:"; docker exec google-drive-service sh -lc 'test -f /app/data/google-drive-token.json && echo yes || echo no'
  echo "[drive] refresh_token:"; docker exec google-drive-service sh -lc 'grep -q "\"refresh_token\"" /app/data/google-drive-token.json && echo yes || echo no' || true
  echo "[calendar] present:"; docker exec fogis-calendar-phonebook-sync sh -lc 'test -f /app/data/google-calendar/token.json && echo yes || echo no'
  echo "[calendar] refresh_token:"; docker exec fogis-calendar-phonebook-sync sh -lc 'grep -q "\"refresh_token\"" /app/data/google-calendar/token.json && echo yes || echo no' || true
  echo "[contacts] present:"; docker exec fogis-calendar-phonebook-sync sh -lc '[ -f /app/token.json ] && echo yes || echo no'
} | tee "${OUTDIR}/tokens.txt"

# 2) API-driven investigation (best-effort)
log "fogis-api-client-service queries"
{
  echo "---> /health"; curl -sS -m 8 http://localhost:9086/health || echo '(failed)'; echo
  echo "---> /matches?date=${DATE_INPUT}"; curl -sS -m 12 "http://localhost:9086/matches?date=${DATE_INPUT}" || true; echo
  echo "---> /matches?from=$(date -v-2d -j -f %Y-%m-%d "${DATE_INPUT}" +%Y-%m-%d 2>/dev/null || echo 2025-08-24)&to=${DATE_INPUT}"; \
    curl -sS -m 12 "http://localhost:9086/matches?from=$(date -v-2d -j -f %Y-%m-%d "${DATE_INPUT}" +%Y-%m-%d 2>/dev/null || echo 2025-08-24)&to=${DATE_INPUT}" || true; echo
} | tee "${OUTDIR}/api-client.txt"

# 3) Trigger fresh processing to surface logs
log "Trigger fresh processing"
python3 fogis-deployment/trigger_fresh_processing.py || true
sleep 60

# 4) Log extraction with broad date patterns
log "Extract logs for date patterns"
PATTS=(
  "${DATE_INPUT}"
  "${DATE_INPUT/T/}"
  "${DATE_INPUT//-/}"
  "$(echo "${DATE_INPUT}" | awk -F- '{print $3"-"$2"-"$1}')" # DD-MM-YYYY
  "$(echo "${DATE_INPUT}" | awk -F- '{print $3"/"$2"/"$1}')" # DD/MM/YYYY
  "$(echo "${DATE_INPUT}" | awk -F- '{print $1"/"$2"/"$3}')" # YYYY/MM/DD
)

FILTER=''
for p in "${PATTS[@]}"; do
  if [ -z "$FILTER" ]; then FILTER="$p"; else FILTER="$FILTER|$p"; fi
done

# Match-list-processor
(docker logs match-list-processor --since 14d 2>&1 \
  | egrep -i "$FILTER|detected new|processing match|processed|calendar|contacts|drive|logo|avatar" || true) \
  | tee "${OUTDIR}/match-list-processor.filtered.log"

echo "== tail (match-list-processor) ==" | tee -a "${OUTDIR}/summary.txt"
tail -n 80 "${OUTDIR}/match-list-processor.filtered.log" | tee -a "${OUTDIR}/summary.txt"

# Calendar/Contacts
(docker logs fogis-calendar-phonebook-sync --since 14d 2>&1 \
  | egrep -i "$FILTER|created event|event created|calendar|contact|contacts|phonebook|people api|error|exception|unauthorized|forbidden|invalid|token|scope" || true) \
  | tee "${OUTDIR}/fogis-calendar-phonebook-sync.filtered.log"

echo "== tail (calendar/contacts) ==" | tee -a "${OUTDIR}/summary.txt"
tail -n 80 "${OUTDIR}/fogis-calendar-phonebook-sync.filtered.log" | tee -a "${OUTDIR}/summary.txt"

# Drive service
(docker logs google-drive-service --since 14d 2>&1 \
  | egrep -i "$FILTER|upload|create|file|drive|avatar|logo|error|exception|permission|unauthorized|forbidden|invalid" || true) \
  | tee "${OUTDIR}/google-drive-service.filtered.log"

echo "== tail (drive) ==" | tee -a "${OUTDIR}/summary.txt"
tail -n 80 "${OUTDIR}/google-drive-service.filtered.log" | tee -a "${OUTDIR}/summary.txt"

# Logo combiner
(docker logs team-logo-combiner --since 14d 2>&1 \
  | egrep -i "$FILTER|combine|logo|avatar|fetch|download|error|exception|404|not found" || true) \
  | tee "${OUTDIR}/team-logo-combiner.filtered.log"

echo "== tail (combiner) ==" | tee -a "${OUTDIR}/summary.txt"
tail -n 80 "${OUTDIR}/team-logo-combiner.filtered.log" | tee -a "${OUTDIR}/summary.txt"

log "Diagnostics written to ${OUTDIR}"
# Print final summary to stdout
cat "${OUTDIR}/summary.txt" || true

