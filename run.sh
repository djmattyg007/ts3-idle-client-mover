#!/bin/bash

export VIRTUAL_ENV_DISABLE_PROMPT=1

cd "$(dirname -- "$(readlink -f "$0")")"

source bin/activate

exec python3 run.py "$@"
