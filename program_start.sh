#!/bin/bash

export DISPLAY=:0 #can run through ssh
cd /home/pi/smartphotoframe/
git pull
python3 main.py
