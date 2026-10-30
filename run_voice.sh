#!/bin/sh
while true; do
  /usr/bin/python3 /home/radxa/voice_ptt_client.py --server http://192.168.8.14:8000/asr --device plughw:1,0
  sleep 2
done
