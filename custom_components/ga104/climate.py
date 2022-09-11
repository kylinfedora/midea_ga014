#有建议可以ywyhass@126.com交流
import json
import time
# import datetime
import voluptuous as vol

from homeassistant.components.climate import (ClimateEntity, PLATFORM_SCHEMA)
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE, HVAC_MODE_COOL, HVAC_MODE_DRY, HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT, SUPPORT_FAN_MODE, HVAC_MODE_AUTO, HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,SUPPORT_SWING_MODE,SUPPORT_AUX_HEAT)
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_PORT,TEMP_CELSIUS, ATTR_TEMPERATURE,STATE_ON,STATE_OFF)
import homeassistant.helpers.config_validation as cv
import requests

import logging
_LOGGER = logging.getLogger(__name__)
from datetime import timedelta
SCAN_INTERVAL = timedelta(seconds=1)

#工作模式
MODE_HVAC={0:HVAC_MODE_OFF,1:HVAC_MODE_FAN_ONLY,2:HVAC_MODE_COOL,3:HVAC_MODE_HEAT,4:HVAC_MODE_AUTO,5:HVAC_MODE_DRY}
#风力模式 #修改后可适配homekit
# MODE_FAN ={0:'关',1:'一档风',2:'二档风', 3:'三档风', 4:'四档风', 5:'五档风', 6:'六档风', 7:'七档风',8:'自动风'}
MODE_FAN ={0:'off',1:'low',2:'higher low', 3:'middle', 4:'really middle', 5:'medium', 6:'lower high', 7:'high',8:'auto'}

#摇头模式 #修改后可适配homekit
MODE_SWING={0:'off',1:'on'}
# MODE_SWING={0:'关',1:'扫风'}


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([Thermostat(hass,discovery_info)])


# pylint: disable=abstract-method
# pylint: disable=too-many-instance-attributes
class Thermostat(ClimateEntity):
    """Representation of a Midea thermostat."""

    def __init__(self,hass, conf):
        """Initialize the thermostat."""
        self._hass = hass
        self._name=conf.get('name');
        self._id=conf.get('id')
        self._unique_id=conf.get('id')
        self._room_temp=0
        self._set_temp=0
        self._run_mode=0
        self._fan_speed=0
        self._max_temp=30
        self._min_temp=17
        #电辅热
        self._aux=False
        #摇头模式
        self._swing=0
        self.time_start=0
        self.update()
        
    #支持的模式
    @property
    def supported_features(self):
        """Return the list of supported features."""
        return (SUPPORT_TARGET_TEMPERATURE|SUPPORT_FAN_MODE|SUPPORT_SWING_MODE|SUPPORT_AUX_HEAT)

    @property
    def should_poll(self):
        return True

    def update(self):
        if time.time()-self.time_start<10:
            return;
        status=self._hass.data['ga014']._status[self._id]
        # _LOGGER.error(self._name)
        self._room_temp=float(status['room_temp'])
        self._set_temp=float(status['cool_temp_set'])
        self._run_mode=int(status['run_mode'])
        self._swing=int(status['is_swing'])
        self._aux=(int(status['is_elec_heat'])>0)
        if int(status['is_auto_fan'])!=0:
            self._fan_speed=8
        else:
            self._fan_speed=int(status['fan_speed'])

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    #返回unique_id以适配UI编辑
    @property
    def unique_id(self):
        """Return the unique_id of the thermostat."""
        return self._unique_id

    @property
    def max_temp(self):
        """Return the max_temp of the thermostat."""
        return self._max_temp

    @property
    def min_temp(self):
        """Return the min_temp of the thermostat."""
        return self._min_temp

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    #当前室温
    @property
    def current_temperature(self):
        return self._room_temp

    #设置的温度
    @property
    def target_temperature(self):
        return self._set_temp

    def set_temperature(self, **kwargs):
        if self._run_mode>0:    
            self.time_start=time.time()
            self._set_temp=kwargs.get(ATTR_TEMPERATURE)
            self._hass.data['ga014'].set_status(self._id,self._run_mode,self._fan_speed,self._set_temp,self._aux,self._swing)

    # 直接调用climate.turn_on时的判断，bemfa平台下小爱、小度等设备开机时会直接调用turn_on，所以依照自动模式的判断逻辑
    
    def turn_on(self, **kwargs):
        if self._room_temp>=self._set_temp:
            self._run_mode=2
        else:
            self._run_mode=3        
        self._hass.data['ga014'].set_status(self._id,self._run_mode,self._fan_speed,self._set_temp,self._aux,self._swing)

    #工作模式列表
    @property
    def hvac_modes(self):
        return list(MODE_HVAC.values())

    #工作模式
    @property
    def hvac_mode(self):
        return MODE_HVAC[self._run_mode]

    def set_hvac_mode(self, hvac):
        self._run_mode=list(MODE_HVAC.keys())[list(MODE_HVAC.values()).index(hvac)]
        # 处理空调没有自动模式的问题，有时Siri开空调会选择自动模式
        if self._run_mode==4:
            if self._room_temp>=self._set_temp:
                self._run_mode=2
            else:
                self._run_mode=3

        self._hass.data['ga014'].set_status(self._id,self._run_mode,self._fan_speed,self._set_temp,self._aux,self._swing)
        
    #风力模式
    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return list(MODE_FAN.values())
    
    @property
    def fan_mode(self):
        """Return the fan setting."""
        return MODE_FAN[self._fan_speed]

    def set_fan_mode(self, fan):
        # month=datetime.datetime.today().month
        if self._run_mode>0:
            self.time_start=time.time()
            self._fan_speed=list(MODE_FAN.keys())[list(MODE_FAN.values()).index(fan)]
            # 处理Siri无法关闭空调问题，Siri只能将空调风速调为关闭，不能关闭空调本体
            if self._fan_speed==0:
                self._run_mode=0
            
            self._hass.data['ga014'].set_status(self._id,self._run_mode,self._fan_speed,self._set_temp,self._aux,self._swing)

        # 处理Siri无法开启空调问题，有时Siri只会调整空调风速，不会开启空调本体
        if self._run_mode==0:
            self._fan_speed=list(MODE_FAN.keys())[list(MODE_FAN.values()).index(fan)]
            if self._fan_speed>0:
                self.time_start=time.time()
                if self._room_temp>=self._set_temp:
                    self._run_mode=2
                else:
                    self._run_mode=3
            self._hass.data['ga014'].set_status(self._id,self._run_mode,self._fan_speed,self._set_temp,self._aux,self._swing)

        



    @property
    def is_aux_heat(self):
        return self._aux
        
    def turn_aux_heat_on(self):
        if self._run_mode>0:
            self.time_start=time.time()
            self._aux = True
            self._hass.data['ga014'].set_status(self._id,self._run_mode,self._fan_speed,self._set_temp,self._aux,self._swing)

    def turn_aux_heat_off(self):
        if self._run_mode>0:
            self.time_start=time.time()
            self._aux = False
            self._hass.data['ga014'].set_status(self._id,self._run_mode,self._fan_speed,self._set_temp,self._aux,self._swing)
        
    @property
    def swing_modes(self):
        return list(MODE_SWING.values())

    @property
    def swing_mode(self):
        return MODE_SWING[self._swing]

    def set_swing_mode(self, swing_mode):
        if self._run_mode>0:
            self.time_start=time.time()
            self._swing=list(MODE_SWING.keys())[list(MODE_SWING.values()).index(swing_mode)]
            self._hass.data['ga014'].set_status(self._id,self._run_mode,self._fan_speed,self._set_temp,self._aux,self._swing)
    