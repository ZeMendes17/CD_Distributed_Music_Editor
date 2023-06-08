#!/bin/bash

NUMBER_OF_WORKERS=2

workers=${1:-$NUMBER_OF_WORKERS}

source venv/bin/activate
for i in $(seq 1 $workers); do
    x-terminal-emulator -e taskset -c $((i-1)) celery -A worker worker --loglevel=INFO -n worker$i@%h &
done

x-terminal-emulator -e celery flower -A worker &

x-terminal-emulator -e python3 server.py

sleep 3

# um curl