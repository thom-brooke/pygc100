"""Global Cache GC-100 relay module"""

import asyncio
from . import core

class Relay:
    """Helper class for operating a relay on a particular GC-100 connector address.

    The function(s) here are largely pass-through to the core GC100 object.
    """

    def __init__(self, gc100, addr):
        self._gc100 = gc100
        self._addr = addr

    def parse_state(self, state):
        return self._gc100.parse_state(state)

    async def setstate(self, active):
        response = await self._gc100.setstate(self._addr, active)
        return response
    
