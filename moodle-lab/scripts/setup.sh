#!/usr/bin/env bash
# Stands up the Moodle support lab from nothing: Moodle 5.0 and MariaDB in Docker, web services on, one service for the lab.
#   bash moodle-lab/scripts/setup.sh      then Moodle is at http://localhost:8093/ and the admin password is in build/admin_password.txt
# The first start installs Moodle's database and takes about five minutes.
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1   # Git Bash on Windows rewrites /lab into a Windows path otherwise

# Passwords are made fresh on this machine and kept in build/ (ignored by git), never written in a command line here.
mkdir -p build
[ -s build/.env ] || python scripts/make_env.py > build/.env
sed -n 's/^LAB_ADMIN_PW=//p' build/.env > build/admin_password.txt
docker compose --env-file build/.env up -d

echo "waiting for Moodle to finish installing (up to 12 minutes)"
code=000
for _ in $(seq 1 144); do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8093/login/index.php || true)
  [ "$code" = "200" ] && break
  sleep 5
done
[ "$code" = "200" ] || { echo "Moodle did not come up"; exit 1; }

docker compose --env-file build/.env exec -T -u daemon moodle php /lab/lab.php setup-ws
echo "done: http://localhost:8093/"
