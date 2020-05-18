"""Global Cache GC-100 send (emit) IR commands"""

import asyncio
from . import core

# @todo Formatting functions to convert different IR code formats (e.g., Pronto) into GC-100.

class IR_out:
    """Helper class for sending IR commands on a particular GC-100 connector address.

    The functions here are largely pass-through to the core GC100 object.
    """

    def __init__(self, gc100, addr):
        self._gc100 = gc100
        self._addr = addr

    def format_sendir(self, freq, code, id=1, count=1, offset=3):
        return self._gc100.format_sendir(self._addr, freq, code, id, count, offset)
        
    def parse_IR(self, ir):
        return self._gc100.parse_IR(ir)

    async def get_IR(self):
        return await self._gc100.get_IR(self._addr)

    # @todo: async def is_valid(self):  [ensure IR mode is 'IR' or 'IR_NOCARRIER'

    async def sendir_raw(self, cmd):
        """Send a fully constructed IR command.

        The 'cmd' should be a well-formed bytes object denoting a valid 'sendir' command, 
        with the trailing CR.

        In general, you should prefer this for static IR commands (e.g., from the same connector
        port, with a repeat count of 1) rather than constructing them each time.  It's just good form.
        """
        response = await self._gc100.raw_request(cmd)
        return response # @todo is there any reason to examine/use the response?

    async def sendir(self, addr, freq, code, id=1, count=1, offset=3):
        response = await self._gc100.sendir(self._addr, freq, code, id, count, offset)
        return response # @todo ditto.
        
