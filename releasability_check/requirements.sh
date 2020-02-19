#!/bin/bash
#create requirements.txt
jq -r '.default
        | to_entries[]
        | .key + .value.version' \
    Pipfile.lock > src/requirements.txt
