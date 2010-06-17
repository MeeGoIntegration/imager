import threading
import subprocess as sub
from models import *
class MicThread(threading.Thread):
    def __init__(self, filename):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self._filename = filename
        self._proc = sub.Popen(['cat', self._filename], shell=False, stdout=sub.PIPE)
    def run(self):
        self._proc.poll()
    def log(self):
        return self._proc.stdout.read()
    def pid(self):
        return self._proc.pid
        
    
