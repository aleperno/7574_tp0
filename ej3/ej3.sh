#!/bin/bash

docker run --rm --name ej3 -v $(pwd)/script.sh:/script.sh --network=7574_tp0_net alpine /bin/sh script.sh
