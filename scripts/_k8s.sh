# Sourced by the remote scripts. Values come from .env; procedure from the
# kubernetes-remote-gpu skill. Fails closed without PREFIX.
set -euo pipefail
KCFG="${KCFG:-$HOME/.kube/config}"
NS="${NS:-p-production}"
PREFIX="${PREFIX:?set PREFIX in .env, e.g. prod-rsv-<owner>}"
REMOTE_CHECKOUT="${REMOTE_CHECKOUT:?set REMOTE_CHECKOUT in .env}"
REMOTE_OUTPUT_ROOT="${REMOTE_OUTPUT_ROOT:?set REMOTE_OUTPUT_ROOT in .env}"

k() { kubectl --kubeconfig "$KCFG" -n "$NS" "$@"; }

running_pods() {
  k get pods --no-headers | awk -v p="^$PREFIX" '$1 ~ p && $3=="Running"{print $1}'
}

# prints: pod idle|busy <nvidia-smi csv>
probe_pods() {
  for p in $(running_pods); do
    smi=$(k exec "$p" -- nvidia-smi --query-gpu=index,utilization.gpu,memory.used \
            --format=csv,noheader,nounits 2>/dev/null || echo "unavailable")
    state=idle
    while IFS=, read -r _ util mem; do
      util=${util// /}; mem=${mem// /}
      if [[ "$util" =~ ^[0-9]+$ ]] && { (( util > 5 )) || (( mem > 500 )); }; then state=busy; fi
    done <<< "$smi"
    printf '%s %s %s\n' "$p" "$state" "$(echo "$smi" | tr '\n' ';')"
  done
}

idle_pod() {
  probe_pods | awk '$2=="idle"{print $1; exit}'
}
