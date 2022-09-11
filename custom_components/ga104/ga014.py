#有建议可以ywyhass@126.com交流
import requests
import json
import threading
import time
import logging
_LOGGER = logging.getLogger(__name__)

class GA014(threading.Thread):
    def __init__(self,hass,host):
        threading.Thread.__init__(self)
        self._hass= hass
        self._host= host
        self._names=[]
        self._status={}
        self.get_name()
        self.get_status()
        self._run = False
        self._lock = threading.Lock()

    def get_name(self):
        url1 = 'http://{0}/protocol.csp?fname=485&opt=getroomlist&function=get'
        try:
            r= requests.get(url1.format(self._host), timeout = 5)
        except Exception as e:
            _LOGGER.error('GA014:%s',str(e))
            return False
        jd = r.json()
        roomlist=jd['arg']['roomlist']
        self._names=json.loads(roomlist)['aclist']
        return True
        
    def get_status(self):
        url2 = 'http://{0}/protocol.csp?fname=485&opt=getaclist&function=get&haddr=0&taddr=9'
        try:
            r= requests.get(url2.format(self._host), timeout = 5)
        except Exception as e:
            _LOGGER.error('GA014:%s',str(e))
            return False
        jd = r.json()
        # _LOGGER.error(jd)
        if jd['arg']!='':
            aclist=json.loads(jd['arg'])['aclist']
            for ac in aclist:
                addr=int(ac['addr'])
                ac['name']=self._names[addr]['name']
                self._status[addr]=ac
        return True
        
    def set_status(self,id,hvac,fan,temp,aux,swing):
        extflag=0
        if aux:
            extflag=extflag+2
        if swing>0:
            extflag=extflag+4
        url2 = 'http://{0}/protocol.csp?fname=485&opt=setac&function=set&addr={1}&run_mode={2}&fan_speed={3}&cooling_temp={4}&heating_temp={4}&extflag={5}'
        # _LOGGER.error(url2.format(self._host,id,hvac,fan,temp,extflag))
        try:
            r= requests.get(url2.format(self._host,id,hvac,fan,temp,extflag), timeout = 5)
        except Exception as e:
            _LOGGER.error('GA014:%s',str(e))
            return False
        return True
 
    def run(self):
        while self._run:
            self.get_status()
            time.sleep(1)

    def start_keep_alive(self):
        with self._lock:
            self._run = True
            threading.Thread.start(self)

    def stop_keep_alive(self):
        with self._lock:
            self._run = False
            self.join()
