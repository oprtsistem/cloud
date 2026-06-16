# -*- coding: utf-8 -*-
'''
  @file  gain_heartbeat_SPO2.py
  @brief Get heart rate and oxygen saturation and post to server
  @copyright   Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
  @license     The MIT License (MIT)
  @author      PengKaixing(kaixing.peng@dfrobot.com)
  @version     V1.0.0
  @date        2021-03-28
  @url         https://github.com/DFRobot/DFRobot_BloodOxygen_S
'''

import sys
import os
import time
import requests
import RPi.GPIO as GPIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
from DFRobot_BloodOxygen_S import *

'''
  ctype=1: UART
  ctype=0: I2C
'''
ctype = 0

if ctype == 0:
    I2C_1       = 0x01               # Use i2c1 interface
    I2C_ADDRESS = 0x57               # I2C device address
    max30102 = DFRobot_BloodOxygen_S_i2c(I2C_1 ,I2C_ADDRESS)
else:
    max30102 = DFRobot_BloodOxygen_S_uart(9600)

def setup():
    while (False == max30102.begin()):
        print("init fail!")
        time.sleep(1)
    print("start measuring...")
    max30102.sensor_start_collect()
    time.sleep(1)

def data2server(bpm, spo2):
    url = 'http://35.74.86.245/api/upload'
    myobj = {'heart_rate': bpm, 'spo2': spo2}
    try:
        x = requests.post(url, json=myobj)
        print("Data POST success, status code: " + str(x.status_code))
    except requests.exceptions.RequestException as e:
        print("Server connection error: " + str(e))

def loop():
    max30102.get_heartbeat_SPO2()

    current_spo2 = max30102.SPO2
    current_bpm = max30102.heartbeat

    print("SPO2 is : " + str(current_spo2) + "%")
    print("heart rate is : " + str(current_bpm) + " Times/min")

    # Check if both values are valid (not -1) before sending to server
    if current_spo2 != -1 and current_bpm != -1:
        data2server(current_bpm, current_spo2)
    else:
        print("Invalid data (-1) detected, skipping POST request.")

    time.sleep(1)

if __name__ == "__main__":
    setup()
    while True:
        loop()