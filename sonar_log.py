# Write binary data to file
class SonarLog:
    def __init__(self, fileName, maxSize):
        self.fileName = fileName
        self.bank = 0
        self.maxSize = maxSize
        self.open()

    # Support two banks: 0 and 1
    def open(self):
        self.f = open("%s.%d"%(self.fileName, self.bank), 'w')

    def write(self, s):
        if self.f.tell()>self.maxSize:
            self.bank = 1 - self.bank
            print 'Swapping log file to bank', self.bank
            self.close()
            self.open()
        self.f.write(s)

    def flush(self):
        self.f.flush()

    def close(self):
        self.f.close()

