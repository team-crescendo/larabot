#!/bin/sh
set -e

WORKSPACE=$(pwd)
PID=$(ps -ef | grep "[p]ython3 ${WORKSPACE}/src/bot.py" | awk '{ print $2 }')

if [ PID ]; then
  echo "$PID" | xargs kill -INT
fi

nohup python3 "${WORKSPACE}/src/bot.py" &
