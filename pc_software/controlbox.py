import matplotlib.pyplot as plt
# import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import PySimpleGUI as sg
import matplotlib
import serial as ser
from serial import SerialException
from time import sleep
import glob
import os
# from pathlib import Path
from threading import Thread
from configparser import ConfigParser
import sys
import signal
import time
import datetime



def command(l):
    print('SEND: '+l)
    s.write(l.encode('utf-8'))
    s.write(b'\r\n')
    return receive(1)

def send(l):
    s.write(l.encode('utf-8'))
    #s.write(b'\r\n')

def receive(end): ## end will signal when to die
    global busy, recibido
    while True:
        line = s.readline().decode()
        recibido += line
        if line.strip() == end:
            busy = False
            with open(file,'w') as f:
                for i in recibido.splitlines():
                    if len(i)>1:
                        f.write(i.replace('.',',')+'\n')
            f.close()
            return

def update(): # send elon & force values to Arduino
    global recibido, MaximumElongation, MaxPushForce
    send('L'+str(MaximumElongation))
    line = s.readline().decode()
    recibido += line
    window['box'].update(recibido)
    send('F'+str(MaxPushForce))
    line = s.readline().decode()
    recibido += line
    window['box'].update(recibido)

config = ConfigParser()
found = config.read('defaults.ini')

if len(found):
    # Read config parameter from INI file
    print("INI file: "+str(found[0]))
    port  = config.get('SerialPort','COM')
    ComSpeed = config.getint('SerialPort','BaudRate')
    CellScale = config.getfloat('General','CellScale')
    MaxPushForce = config.getfloat('General','MaxPushForce')
    MaximumElongation  = config.getfloat('General','MaximumElongation')
    DataDir = config.get('General','DataDir')

layout=[[sg.Text("Serial Port to Arduino:"), sg.Input(port, size=(25, 1), enable_events=True, key="Port"), sg.Button('Connect'),sg.Button('Disconnect')],
        [sg.Text('MaxDisplacement (mm)'), sg.Input(MaximumElongation,size=(5,1),key="Elon"), sg.Text('MaxForce (N)'),sg.Input(MaxPushForce,size=(5,1),key="Force"), sg.Button('Set') ],
        [sg.Button('Start'), sg.Button('ResetCell'),sg.Button('ManualMeasurement'),  sg.Button('STOP',button_color=(None,'red'))],
        [sg.Button('StartManualTest'), sg.Text('motor disabled')],
        [sg.Multiline('Last measures',size=(40,10),key='box', autoscroll=True,)]]
window = sg.Window('Push Device Control',layout, finalize=True)
window['Disconnect'].update(disabled=True)

recibido='Last measurements\n'

connected = False
busy = False
while True:
    if not busy:
        windows, event, values = sg.read_all_windows()
    else:
        windows, event, values = sg.read_all_windows(timeout=200)
    window['box'].update(recibido) #values['box']+"Line")    
        

    if not connected and event == 'Connect': #################CONNECT!!!!!!!
        connected = True
        window['Disconnect'].update(disabled=False)
        window['Connect'].update(disabled=True)
        try:
            port = values['Port']
            s = ser.Serial(port, baudrate=ComSpeed, timeout=2)
        except SerialException:
            print("ERROR Opening the Serial Port: "+values['Port'])
            event='Exit'
            s.close()
            break
        #sleep(1)
        ok = False
        for i in range(3):
            line=s.readline().strip()
            # print(line)
            if line == b'ready':
                ok = True
                break
        if not ok:
            print('NOT CONNECTED')
            event='Exit'
            s.close()
            break
        recibido = 'CONNECTED\n'
        window['box'].update(recibido)
        update()

    if connected and event == 'Disconnect':  #######DISCONNECT
        connected = False
        window['Connect'].update(disabled=False)
        window['Disconnect'].update(disabled=True)
        s.close()

    if event == sg.WIN_CLOSED or event == 'Exit': break

    if connected and event == 'STOP': send('X')

    if connected and event == 'Start':
        file = sg.popup_get_file('Filename to store test data:', save_as = True)
        recibido = ''
        busy = True
        send('S')
        thread = Thread(target=receive, args=('.'))
        thread.start()

    if connected and event == 'ManualMeasurement':
        send('?')
        line = s.readline().decode()
        recibido += line
        window['box'].update(recibido)

    if event == 'Set':
        MaximumElongation = values['Elon']
        MaxPushForce = values['Force']
        if connected: # if connected then push the values to the Arduino
            update()
        config['General']['MaxPushForce'] = MaxPushForce
        config['General']['MaximumElongation'] = MaximumElongation
        config['SerialPort']['COM'] = values['Port'] 
        with open('defaults.ini', 'w') as configfile:
            config.write(configfile)

    if connected and event == 'StartManualTest':
        file = sg.popup_get_file('Filename to store test data:', save_as = True)
        recibido = ''
        busy = True
        send('M')
        thread = Thread(target=receive, args=('.'))
        thread.start()
        
window.close()
s.close()   
