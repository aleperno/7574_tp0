#!/bin/bash

PREFIX="version: '3'
services:
  server:
    container_name: server
    image: server:latest
    entrypoint: [\"python3\",  \"/main.py\"]
    environment:
      - PYTHONUNBUFFERED=1
      - SERVER_PORT=12345
      - SERVER_LISTEN_BACKLOG=7
      - LOGGING_LEVEL=DEBUG
    networks:
      - testing_net
    volumes:
      - ./server/config.ini:/config.ini
"

SUFFIX="
networks:
  testing_net:
    name: 7574_tp0_net
    ipam:
      driver: default
      config:
        - subnet: 172.25.125.0/24
"

echo -n "$PREFIX"

for i in $(seq $1); do
echo -n "
client$i:
    container_name: client$i
    image: client:latest
    entrypoint: /client
    environment:
      - CLI_ID=$i
    networks:
      - testing_net
    depends_on:
      - server
    volumes:
      - ./client/config.yaml:/config.yaml
"
done

echo -n "$SUFFIX"
