#!/bin/bash
lcUsername=$(echo "$3" | tr '[:upper:]' '[:lower:]')
python -u RAT.py "$@" 2>&1 | tee -a $lcUsername".log"