#!/usr/bin/env bash
# List Running reservation pods matching PREFIX with idle/busy state.
source "$(dirname "$0")/_k8s.sh"
echo "kubeconfig=$KCFG ns=$NS prefix=$PREFIX"
out=$(probe_pods)
if [ -z "$out" ]; then echo "no Running pods match prefix $PREFIX"; exit 1; fi
echo "$out"
