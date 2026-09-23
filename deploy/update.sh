#!/usr/bin/env bash
# Deploy the latest code on the server. Run as the `cofur` user from /srv/cofur:
#   bash deploy/update.sh
set -euo pipefail
cd /srv/cofur
source .venv/bin/activate

if [ -d .git ]; then
  git pull --ff-only
fi
pip install -r requirements.txt --quiet
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check --deploy
sudo systemctl restart cofur
echo "Deployed. Tail logs with: sudo journalctl -u cofur -f"
