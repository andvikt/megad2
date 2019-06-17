"""
Центральный класс - Mega отвечает за коммуникацию с устройством, по сути это просто контейнер с ip-адресом и оберткой над
requests с обеспечением необходимой блокировки на время выполнения запроса
"""

from logging import basicConfig
basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from . import const
from . import utils
from .mega import Mega
from .one_wire import OneWireBus
from . import things
from .things import Servo, Relay, SpeedSelect
