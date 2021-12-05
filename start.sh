#! /usr/bin/env bash
echo "" > nohup.out
nohup poetry run python3.9 boot_manager.py &
echo "Done"
