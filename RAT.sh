#!/bin/bash
lcUsername=$(echo "$3" | tr '[:upper:]' '[:lower:]')
python -u riftChatBot.py "$@" 2>&1 | tee $lcUsername".log"