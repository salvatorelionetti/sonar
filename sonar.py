#!/usr/bin/env python
import re
import time
import serial
import datetime
import httplib, urllib
import smtplib, email.mime.text
import logging
import serializer
import sonar_log
import notifications
import config

sonarConfig = {
    'LogFileSize': 256*1024,
    'LogFileName': '/tmp/sonar.raw',
    'SerialFileName': '/dev/ttyUSB1',
    'SerialBaudRate': 57600,
}


serializerIdleMinSecs = 20 # Thingspeak interarrival time is 15secs

distKm1 = None
distK = None
lastDistSent = None
lastDistNotificationTime = None
tStartup = time.time()
lastTimeDistList = []

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def isDistChanged(distPrev, distCur):
    """
    Check if previous measure is "different" from current one
    where "different" mean:
     * no previous measure (first sample)
     * more than 5mm far
    """
    return (distPrev is None) or abs(distPrev-distCur)>10 # 6mm

def sendNotification():
    global logging
    global lastTimeDistList
    
    msg = ''
    for el in lastTimeDistList:
        msg += "%s: %s\r\n"%(el[0], str(el[1]))

    notifications.send(logging, msg)

    logging.debug('Notifications sent!')

def sendDistance(dist):
    global distK
    global lastDistSent
    global lastDistNotificationTime

    assert distK is not None

    dict = {}
    dict['field2'] = dist

    if isDistChanged(lastDistSent, distK):
        dict['field1'] = distK
        lastDistSent = distK

        # Send mail
        tNow = time.time()
        if lastDistNotificationTime is not None:
            logging.debug(abs(tNow - lastDistNotificationTime))
        if (lastDistNotificationTime is None) or abs(tNow - lastDistNotificationTime)>(3*60):
            # Discard startup events
            # By this way the event: door opened when device rebooted is lost!
            if (tNow - tStartup)>1.0:
                sendNotification()
                lastDistNotificationTime = tNow

    logging.debug('sendDistance'+str(dict))
    dict['key'] = config.config['thingspeak_ch2_api_key']

    params = urllib.urlencode(dict)
    headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}
    conn = httplib.HTTPConnection("api.thingspeak.com:80", timeout=30)
    conn.request("POST", "/update", params, headers)
    response = conn.getresponse()
    if response.status != 200:
        logging.debug(str(response.status) + '/' + response.reason)
    data = response.read()
    conn.close()

def updateDistance(dist, serializer):
    serializer.schedule(dist)

def decodeMessage(msg, sonarLog, serializer):
    global distKm1
    global distK
    global lastTimeDistList

    doLog = False

    m = re.match('R([0-9]*)', msg)
    dist = -1

    if m is not None and len(m.groups())==1:
        try:
            dist = int(m.group(1))

            # Store previous message
            if isDistChanged(distKm1, dist):
                distKm1 = dist
                doLog = True
                #dt = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                #print 'DecodeMessage', msg, dt
        except:
            doLog = True
            logging.error('Invalid (null bytes?) message:' + str(msg))
            dist = -2

    else:
        if len(msg)>=2:
            doLog = True
            logging.error('Invalid msg '+ str(len(msg)) + str(msg))
            dist = -3
        else:
            doLog = True
            logging.error('Invalid short msg ' + str(len(msg)) + str(msg))
            dist = -4

    distK = dist

    if doLog:
        dt = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        lastTimeDistList.append([dt, dist])
        if len(lastTimeDistList)>30:
            lastTimeDistList.remove(lastTimeDistList[0])

        updateDistance(dist, serializer)

        #print 'DecodeMessage', msg, dt
        sonarLog.write(msg + ' ' + dt + '('+str(dist)+')'+"\n")
        sonarLog.flush()

    return dist

ser = None
sonarLog = None

try:
    sonarLog = sonar_log.SonarLog(sonarConfig['LogFileName'], sonarConfig['LogFileSize']/2)
    logging.info('opening ' + sonarConfig['SerialFileName'])
    ser = serial.Serial(sonarConfig['SerialFileName'], sonarConfig['SerialBaudRate'])
    v = ser.isOpen()

    msg = ''

    with serializer.Serializer(sendDistance, serializerIdleMinSecs) as serializer:
        while 1:
            # Read until '\d' is reached
            s = ser.read(1)
            #print type(s),s,hex(ord(s))
            if type(s) == type(''):
                #print 'is a string', s=='\d', s is '\d', ord(s)==0xd
                if ord(s) == 0xd:
                    # Got a message, dispatch it
                    ret = decodeMessage(msg, sonarLog, serializer)
                    #time.sleep(1) does not trigger sometimes
                    msg = ''
                else:
                    msg += s
                    if len(msg) > 1000:
                        logging.error('Discarded 1000bytes!')
                        msg = ''

            else:
                logging.error('Bytes with unkown type:', type(s), s, hex(ord(s)))
    
finally:
    if ser is not None:
        logging.info('Closing serial port')
        ser.close()

    if sonarLog is not None:
        logging.info('Closing log file')
        sonarLog.close()

    notifications.close()
