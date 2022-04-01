#!/bin/bash

TESTMSG="test_message"
EXPECTED="Your Message has been received:"
PORT="${SERVERPORT:-12345}"

echo "Running 'echo $TESTMSG | nc -w 2 server $PORT'"

output=$(echo "$TESTMSG" | nc -w 2 server $PORT)

if [[ $? -ne 0 ]]; then
    echo "Something went wrong with the connection"
    exit 2
else
    if [[ "$EXPECTED $TESTMSG" == "$output" ]]; then
        echo "Server returned as expected"
        exit 0
    else
        echo "Unexpected return"
        echo "Expected: $EXPECTED"
        echo "Got: $output"
        exit 1
    fi
fi
