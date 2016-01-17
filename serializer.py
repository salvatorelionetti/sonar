#!/usr/bin/env python
import time
import datetime
import threading

class Serializer:

    # Send packets only when channel is idle by some time
    def __init__(self, idleCb, idleMinSecs, sendAllEvents=True):
        self.idleMinSecs = idleMinSecs
        self.idleCb = idleCb
        self.dtLastSent = None
        self.sendAllEvents = sendAllEvents
        self.timers = []

    def schedule(self, data):

        tNow = time.time()
        dt = 0
        if self.dtLastSent is not None:
            dt = int(tNow - (self.dtLastSent + self.idleMinSecs))

        print 'dt', dt, 'dtLastSent', self.dtLastSent
        if dt>0:
            dt = 0
        if dt<0:
            dt = -dt

        self.dtLastSent = tNow + dt
        if dt>0:
            print 'scheduling data', data, 'in', dt,'secs'
            t = threading.Timer(dt, lambda: self.timerExpired(data))
            self.timers.append(t)
            t.start()
            print t
            print 'after timers.append', len(self.timers)
        else:
            self.idleCb(data)
    
    def timerExpired(self, data):
        # FIFO
        t = self.timers.pop(0)
        print 'TimerExpired', t, len(self.timers), 'timers actives'
        #print 'after timers.pop', len(self.timers), 'timers'
        self.idleCb(data)

        if not self.sendAllEvents:
            self.close()

    def close(self):
        print 'timers2del', len(self.timers)
        for t in self.timers:
            print 'Timer cancelled', t
            t.cancel()
        self.timers = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def test0():
    def sendCb(data):
        print 'SENDCB!', data
    with Serializer(sendCb, 3) as s:
        s.schedule(1)
        s.schedule(2)
        s.schedule(3)
        time.sleep(5)

if __name__ == '__main__':
    test0()
