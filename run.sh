#!/bin/bash

NUMBER_OF_WORKERS=2

workers=${1:-$NUMBER_OF_WORKERS}

source venv/bin/activate
for i in $(seq 1 $workers); do
    x-terminal-emulator -e celery -A worker worker --loglevel=INFO -n worker$i@%h &
done

x-terminal-emulator -e celery flower -A worker &

x-terminal-emulator -e python3 server.py &

sleep 5

curl -F "myfile=@test.mp3" http://localhost:5000/music -o response.json

sleep 5

curl -F "instruments=bass,drums" http://localhost:5000/music/$(cat response.json | jq -r '.music_id')

rm response.json


