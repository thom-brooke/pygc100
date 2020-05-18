"""Global Cache serial interface (bidirectional)"""

import asyncio
from . import core

class SerialError(core.Error):
    # @todo components and/or derived exceptions
    pass

BASE_PORT = 4999


class Serial:
    """Helper class for sending and receiving serial data through GC-100"""

    def __init__(self, gc100, addr, index):
        self._gc100 = gc100
        # @todo: lookup connector address from index (or vice versa)
        self._addr = addr
        self._w = None
        self._r = None
        self._port = BASE_PORT + index


    async def connect(self):
        if self._w is not None:
            # already connected.  may be broken, but already connected.
            return
        self._r, self._w = await asyncio.open_connection(self._gc100.host(), self._port)

        
    async def disconnect(self):
        if self._w is None:
            # not connected
            return
        try:
            self._w.close()
            await self._w.wait_closed()
        finally:
            self._r = None
            self._w = None

            
    async def get_SERIAL(self):
        return await self._gc100.get_SERIAL(self._addr)

    
    def is_connected(self):
        return self._w is not None

    
    def parse_SERIAL(self, serial):
        return self._gc100.parse_SERIAL(serial)

    
    async def recv(self, size):
        """Return up to next 'size' bytes"""
        if self._r is None:
            raise SerialError("not connected")

        try:
            data = await self._r.read(size)
            if data:
                return data
            else:
                await self.disconnect()
        except Exception as e:
            await self.disconnect()
            raise e

        
    async def send(self, msg):
        """Send 'msg' (in bytes)"""
        if self._w is None:
            raise SerialError("not connected")

        try:
            self._w.write(msg)
            await self._w.drain()
            # The GC-100 gets VERY confused if you send packets too quickly.
            # It doesn't seem to correctly ACK retransmissions, eventually timing
            # out and then rebooting.  So, inject a delay here.
            await asyncio.sleep(0.01)
        except Exception as e:
            await self.disconnect()
            raise e

        
    async def set_SERIAL(self, baudrate, flowcontrol, parity):
        await self._gc100.set_SERIAL(self._addr, baudrate, flowcontrol, parity)
