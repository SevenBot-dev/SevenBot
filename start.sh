#! /usr/bin/env bash
source ./.venv/bin/activate
nohup python3.9 boot_manager.py &
deactivate
echo "Done"
