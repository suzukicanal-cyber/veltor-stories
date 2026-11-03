#!/usr/bin/env bash
# Install / update the VELTOR guard on the VPS. Run as root:
#   curl -fsSL https://raw.githubusercontent.com/suzukicanal-cyber/veltor-stories/main/guard/install.sh | bash
set -euo pipefail
BASE=https://raw.githubusercontent.com/suzukicanal-cyber/veltor-stories/main/guard
mkdir -p /opt/veltor-guard
curl -fsSL "$BASE/guard.py" -o /opt/veltor-guard/guard.py
curl -fsSL "$BASE/veltor-guard.service" -o /etc/systemd/system/veltor-guard.service

if [ ! -f /etc/veltor-guard.env ]; then
  read -rsp "Токен @VELTOR_moderator_bot (ввод не отображается): " BOT_TOKEN </dev/tty; echo
  read -rsp "GitHub-токен (Actions: read & write для veltor-stories): " GITHUB_TOKEN </dev/tty; echo
  umask 077
  cat > /etc/veltor-guard.env <<EOF
BOT_TOKEN=$BOT_TOKEN
GITHUB_TOKEN=$GITHUB_TOKEN
GROUP_USERNAME=koreamotocycles_veltor
MOTO_TOPIC_ID=8
EOF
fi

systemctl daemon-reload
systemctl enable --now veltor-guard
systemctl restart veltor-guard
sleep 3
systemctl --no-pager status veltor-guard | head -n 12
echo
echo "Журнал: journalctl -u veltor-guard -f"
