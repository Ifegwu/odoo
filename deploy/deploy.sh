#!/usr/bin/env bash
# Deploy latest production code on the droplet and restart Odoo.
# Invoked by GitHub Actions over SSH.
set -euo pipefail

DEPLOY_PATH="${ODOO_DEPLOY_PATH:-/opt/odoo/odoo}"
SERVICE="${ODOO_SERVICE:-odoo}"
DB_NAME="${ODOO_DB_NAME:-aciu}"
GIT_BRANCH="${GIT_BRANCH:-production}"
UPDATE_MODULES="${UPDATE_MODULES:-true}"
REPO_URL="${REPO_URL:-https://github.com/Ifegwu/odoo.git}"
CLONE_TOKEN="${GH_CLONE_TOKEN:-}"
GIT_SHA="${GIT_SHA:-unknown}"

echo "==> Deploy host=$(hostname) sha=${GIT_SHA} branch=${GIT_BRANCH}"

AUTH_URL="${REPO_URL}"
if [ -n "${CLONE_TOKEN}" ]; then
  AUTH_URL="$(echo "${REPO_URL}" | sed -E "s#https://#https://x-access-token:${CLONE_TOKEN}@#")"
fi
export GIT_TERMINAL_PROMPT=0

sync_tree() {
  local url="$1"
  if [ ! -d "${DEPLOY_PATH}/.git" ]; then
    echo "==> No git checkout — shallow clone ${GIT_BRANCH}"
    rm -rf "${DEPLOY_PATH}"
    sudo -u odoo git clone --depth 1 --branch "${GIT_BRANCH}" --single-branch "${url}" "${DEPLOY_PATH}"
    return
  fi

  cd "${DEPLOY_PATH}"
  sudo -u odoo git remote set-url origin "${url}"
  echo "==> git fetch origin/${GIT_BRANCH}"
  sudo -u odoo git fetch --depth 1 --prune origin "${GIT_BRANCH}" \
    || sudo -u odoo git fetch --prune origin

  # Force onto production even if prior interrupted clone left untracked files
  echo "==> force checkout ${GIT_BRANCH}"
  sudo -u odoo git clean -fd -e venv -e .venv || true
  if ! sudo -u odoo git checkout -f "${GIT_BRANCH}" 2>/dev/null; then
    sudo -u odoo git branch -D "${GIT_BRANCH}" 2>/dev/null || true
    if ! sudo -u odoo git checkout -f -B "${GIT_BRANCH}" "origin/${GIT_BRANCH}"; then
      echo "==> Checkout still broken — wiping and re-cloning"
      cd /
      rm -rf "${DEPLOY_PATH}"
      sudo -u odoo git clone --depth 1 --branch "${GIT_BRANCH}" --single-branch "${url}" "${DEPLOY_PATH}"
      cd "${DEPLOY_PATH}"
    fi
  fi
  sudo -u odoo git reset --hard "origin/${GIT_BRANCH}" || sudo -u odoo git reset --hard "FETCH_HEAD"
}

sync_tree "${AUTH_URL}"
cd "${DEPLOY_PATH}"
sudo -u odoo git remote set-url origin "${REPO_URL}"
sudo -u odoo git log -1 --oneline
sudo -u odoo git status -sb

# Refresh Python deps if requirements changed
if [ -f requirements.txt ] && [ -x "${DEPLOY_PATH}/venv/bin/pip" ]; then
  echo "==> pip install -r requirements.txt"
  sudo -u odoo "${DEPLOY_PATH}/venv/bin/pip" install -q -r requirements.txt
fi

if [ "${UPDATE_MODULES}" = "true" ]; then
  echo "==> Odoo -u aciu modules on ${DB_NAME}"
  systemctl stop "${SERVICE}" || true
  sudo -u odoo "${DEPLOY_PATH}/venv/bin/python" "${DEPLOY_PATH}/odoo-bin" \
    -c /etc/odoo/odoo.conf -d "${DB_NAME}" \
    -u aciu_base,aciu_membership,aciu_dues \
    --stop-after-init
fi

echo "==> Restart ${SERVICE}"
systemctl restart "${SERVICE}"
sleep 2
systemctl --no-pager --full status "${SERVICE}" | head -n 20 || true

echo "==> Deploy finished"
