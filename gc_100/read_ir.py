"""Global Cache digital input (using IR module)"""

import asyncio
from . import core


class Digital_In:
    """Helper class for reading the digital input state on a particular GC-100 connector address.

    The function(s) here are largely pass-through to the core GC100 object.

    Note that this class does not currently support unsolicited 'statechange' messages 
    from the GC-100.  That would require a [continuously] open TCP connection, which
    the core library does not maintain.
    """

    def __init__(self, gc100, addr):
        self._gc100 = gc100
        self._addr = addr

    async def get_IR(self):
        return await self._gc100.get_IR(self._addr)

    async def getstate(self):
        response = await self._gc100.getstate(self._addr)
        return response

    # @todo: async def is_valid(self):  [ensure IR mode is 'SENSOR' or 'SENSOR_NOTIFY'

    def parse_IR(self, ir):
        return self._gc100.parse_IR(ir)

    def parse_state(self, state):
        return self._gc100.parse_state(state)

