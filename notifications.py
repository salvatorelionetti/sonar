import base64
import urllib, urllib2
import threading, time
import fcntl, sys, os
import datetime
import smtplib, email, email.MIMEText
import traceback
import config

stopMonitorTimer = None

def stopMonitor():
    active = 0
    status = 'disabled'
    print 'STOPMONITORTIMER: stopping motion/sound detect!!!'
    print 'Motion %s(status %d)!'%(status, active)
    soundDetectionSet(active)
    print 'Sound %s!'%status
    motionDetectionSet(active)
    soundDetectionSet(active)
    
def startMonitorTimer():
    global stopMonitorTimer

    if stopMonitorTimer is not None:
        # Restart the timer from now
        print 'STARTMONITORTIMER: reschedule'
        stopMonitorTimer.cancel()

    # Start the timer
    print 'STARTMONITORTIMER: creation'
    stopMonitorTimer = threading.Timer(30*60, stopMonitor)
    stopMonitorTimer.start()

def sendMail(m = None):
    
    dst = config.config['mail_watchers'];
    if type(dst) == type([]):
        dst = ','.join(dst)

    msg = email.MIMEText.MIMEText(m+"\n"+'http://5.101.105.220/images/lamarmora_door/')
    #msg['To'] = dst
    msg['Subject'] = 'Porta aperta in via Lamarmora!'

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(config.config['mail_username'], config.config['mail_password'])
    server.sendmail(config.config['mail_username'], config.config['mail_watchers'], msg.as_string())

# Interact with D-Link DCS-5020L Camera
def request_response(resource, data):
    req = urllib2.Request('http://192.168.1.70' + resource, urllib.urlencode(data))
    auth_string = base64.encodestring('%s:%s' %(config.config['camera_door']['username'], config.config['camera_door']['password'])).replace('\n', '')
    req.add_header('Authorization', 'Basic %s' % auth_string)
    #req.add_header('Accept-encoding', 'gzip, deflate')
    #req.add_header('Referer', 'http://192.168.1.70' + resource)

    return urllib2.urlopen(req).read()

def motionDetectionSet(active):
    # The order DOES matter
    data = [
        ('ReplySuccessPage', 'motion.htm'),
        ('ReplyErrorPage', 'motion.htm'),
        ('MotionDetectionEnable', active),
        ('MotionDetectionScheduleDay', 127),
        ('ConfigSystemMotion', 'Save'),
    ]

    msg = request_response('/setSystemMotion', data)

def soundDetectionSet(active):
    # The order DOES matter
    data = [
        ('ReplySuccessPage', 'sounddb.htm'),
        ('ReplyErrorPage', 'sounddb.htm'),
        ('SoundDetectionEnable', active),
        ('SoundDetectionScheduleDay', 0),
        ('SoundDetectionDB', 90),
        ('ConfigSystemSoundDB', 'Save'),
    ]

    msg = request_response('/setSystemSoundDB', data)


def update(camera_armed_kp1, msg=None):
    status = ['dis', 'en'][camera_armed_kp1] + 'abled'
    if msg is None:
        msg = status
    sendMail(msg)
    print 'Mail sent ', status

    active = 1
    if camera_armed_kp1 is False:
        active = 0
    motionDetectionSet(active)
    print 'Motion %s(status %d)!'%(status, active)
    soundDetectionSet(active)
    print 'Sound %s!'%status

    if active is 1:
        startMonitorTimer()

def isKeyDevicePresent():
    ret = os.system("snmpwalk -c t0m1t0m1 -v 1 192.168.1.254 | grep -i 'E8 4E 84 0E 01 1F' >/dev/null")
    print type(ret), ret
    return ret == 0
        
class WiFiHuntingThread(threading.Thread):
    def __init__(self):
        print 'WiFiHuntingThread.__init__'
        self.door_opened = False
        self.camera_armed = None
        self.please_stop = False
        threading.Thread.__init__(self)

    def run(self):
        print 'WiFiHuntingThread.run'
        return

        while not self.please_stop:
            time.sleep(1)
            camera_armed = True
            if self.door_opened:
                self.door_opened = False
                camera_armed = True
            if isKeyDevicePresent():
                camera_armed = False

            if camera_armed != self.camera_armed:
                self.camera_armed = camera_armed
                update(camera_armed)

    def doorOpened(self):
        print 'WiFiHuntingThread.doorOpened'
        self.door_opened = True

    def pleaseStop(self):
        self.please_stop = True

wifiHuntingThread = None

def send(logging, lastTimeDistList):
    update(True, lastTimeDistList)

def start():
    global wifiHuntingThread

    restart
    pid_file = config.config['ramfs_dir'] + '/wifihunting.pid'
    fp = open(pid_file, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        wifiHuntingThread = WiFiHuntingThread()
        wifiHuntingThread.start()
    except IOError:
        # another instance is running
        traceback.print_exc()

def doorOpened():
    global wifiHuntingThread

    wifiHuntingThread.doorOpened()

def close():
    global wifiHuntingThread

    print 'Stopping WiFiHunting thread!'
    if wifiHuntingThread is not None:
        wifiHuntingThread.pleaseStop()

def t0():
    try:
        start()
        time.sleep(5)
        doorOpened()
        time.sleep(7)
    finally:
        print 'Finally'
        close()

def t01():
    update(False)

def t1():
    L = []
    for l in range(10):
        dt = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] 
        L.append([dt, l])
        time.sleep(0.1)
    print L
    msg = ''
    for el in L:
        msg += "%s: %s\r\n"%(el[0], str(el[1]))
    sendMail(msg)
    print 'Mail sent!'

if __name__ == '__main__':
    #t0()
    #t1()
    #t01()
    #sendMail()
    startMonitorTimer()
    time.sleep(2)
    startMonitorTimer()
    time.sleep(10)
