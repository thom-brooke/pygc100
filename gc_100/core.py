"""Control for Global Cache GC-100 devices


"""

import asyncio

# It's not clear that you CAN change the command port on the GC-100.
# But if you ever can, we'll need to make it configurable; keep the
# default command port for most users.
DEFAULT_PORT = 4998

# Commands (and responses) are terminated with CR (0x0d).
CR = b'\r'

# Command (and response) fields are separated by commas.
SEP = ','


class Error(Exception):
    pass

class CommandError(Error):
    ERR_TEXT = {
        1: "Timeout: CR not received.",
        2: "Invalid module address (getversion)",
        3: "Invalid module address (does not exist)",
        4: "Invalid connector address",
        5: "Attempt to send IR command on 'sensor-in' connector address 1",
        6: "Attempt to send IR command on 'sensor-in' connector address 2",
        7: "Attempt to send IR command on 'sensor-in' connector address 3",
        8: "Offset is set to even transition number (IR command)",
        9: "Exceeded maximum IR transitions (> 256)",
        10: "Non-even number of IR transitions",
        11: "Contact-closure command sent to non-relay module",
        12: "Missing CR",
        13: "State request to invalid or non-sensor IR address",
        14: "Unsupported command",
        15: "Exceeded maximum IR transitions (SM_IR_INPROCESS)",
        16: "Non-even number of IR transitions",
        21: "IR command sent to non-IR module",
        23: "Command not supported by module type"
    }

    def __init__(self, errno):
        self.errno = errno

    def __str__(self):
        text = CommandError.ERR_TEXT.get(self.errno)
        return f"({self.errno}) {text}"


class GC100:
    """Global Cache GC-100 device

    This is the "core" device.  You can perform ALL commands from here,
    but it may be easier to use one of the helper classes:
    * gc_100.IR_out
    * gc_100.Serial
    * gc_100.Digital_in
    * gc_100.Relay

    In general, you can (and should) query the GC-100 from here.
    Use the helper classes for direct interaction with modules.
    Each helper class also includes relevant queries and configurations.

    This module/package has *limited* applicability to iTach devices.
    The error responses for GC-100 and iTach are different; iTach errors will 
    NOT be detected here (so don't make any mistakes :-).  Not all iTach features
    (e.g., <some IR mode(s)>) are supported here.
    """
    
    # At this point, command port connections are ephemeral:
    # connect to the port; do something; close the port.
    # This works as long as there is no unsolicitied traffic from the GC-100;
    # which is true UNLESS one of the IR connections is configured for SENSOR_NOTIFY,
    # in which case the connection must stay open (and monitored) in order to receive
    # the state change notifications.

    # This implementation assumes success.
    # Any exceptions (e.g., broken connections) are simply raised.
    # Command errors are detected and reported (but not prevented or corrected).

    # In general, we want to synchronize commands/requests, so that they don't overlap.
    # That's because subsequent IR commands will interrupt the prior command (when repeating),
    # and we usually don't want to do that.  Additionally, being able to interleave other commands
    # may also interleave any responses, which will make sorting them out difficult.
    #
    # So: we create a "lock" that ensures each request runs to completion before
    # letting the next one start.  This is a problem for things like 'stopir', but otherwise
    # acceptable.
    
    def __init__(self, host, port=DEFAULT_PORT):
        self._host = host
        self._port = port
        self._cmd_lock = asyncio.Lock()
        self._partial = b''
        # @todo etc.

    def error_check(self, response):
        """Does 'response' denote an error?

        If so, raise CommandError with the associated error number.
        Use str() to see error text.
        """
        # The error response separator is a space, not a comma.
        tokens = response.split(' ')
        if tokens[0] == 'unknowncommand':
            raise CommandError(int(tokens[1]))

    def format_sendir(self, addr, freq, code, id=1, count=1, offset=3):
        """Construct a raw 'sendir' command.

        Returns 'bytes', correctly formatted for 'raw_request()', with trailing CR.
        """
        command = f"sendir,{addr},{id},{freq},{count},{offset},{code}"
        return bytes(command, encoding='utf8')+CR

    def host(self):
        """Return the configured host IP [address]"""
        return self._host
    
    def parse_device(self, device):
        """Parse a single device string response (as from 'getdevices').

        The given 'device' should be the complete string, including the leading "device"
        token, but excluding the trailing CR.  This will return a dict with the component
        values for the module number and type.
        """
        tokens = device.split(SEP)
        if tokens[0] != 'device':
            return {}
        return {'module':int(tokens[1]),
                'type':tokens[2]}

    def parse_IR(self, ir):
        """Parse the IR connector port response string (as from 'get_IR').

        The given 'ir' should be the complete string, including the leading "IR" 
        token, but excluding the trailing CR.  This will return a dict with the component
        values for the connector address and mode.
        """
        tokens = ir.split(SEP)
        if tokens[0] != 'IR':
            return {}
        return {'addr': tokens[1],
                'mode': tokens[2]}
    
    def parse_NET(self, network):
        """Parse the unit network configuration string (as from 'get_NET').

        The given 'network' should be the complete string, including the leading "NET" 
        token, but excluding the trailing CR.  This will return a dict with the component
        values for the connector address (always '0:1'), lock status, addressing mode (DHCP
        vs. static), IP address, subnet, and gateway.
        """
        tokens = network.split(SEP)
        if tokens[0] != 'NET':
            return {}
        return {'addr': tokens[1],
                'lock': tokens[2],
                'mode': tokens[3],
                'ip'  : tokens[4],
                'subnet': tokens[5],
                'gateway': tokens[6]}

    def parse_SERIAL(self, serial):
        """Parse the serial port configuration string (as from 'get_SERIAL').

        The given 'serial' should be the complete string, including the leading "SERIAL" 
        token, but excluding the trailing CR.  This will return a dict with the component
        values for the connector address, baud rate, flow control and parity.
        """
        tokens = serial.split(SEP)
        if tokens[0] != 'SERIAL':
            return {}
        return {'addr': tokens[1],
                'baud': int(tokens[2]),
                'flow': tokens[3],
                'parity': tokens[4]}
    
    def parse_state(self, state):
        """Parse the digital input response string (as from 'getstate' or 'setstate').

        The given 'state' should be the complete string, including the leading "state" 
        token, but excluding the trailing CR.  This will return a dict with the component
        values for the connector address and state (as integer 0 or 1).
        """
        tokens = state.split(SEP)
        if tokens[0] != 'state':
            return {}
        return {'addr': tokens[1],
                'state': int(tokens[2])}
    
    def parse_version(self, version):
        """Parse a module version string (as from 'getversion').

        The given 'version' should be the complete string, including the leading "version" 
        token, but excluding the trailing CR.  This will return a dict with the component
        values for the module and version text.
        """
        tokens = version.split(SEP)
        if tokens[0] != 'version':
            return {}
        return {'module':int(tokens[1]),
                'text': tokens[2]}
    
    async def recv_response(self, reader):
        """Return the next response string.

        This will split multiple responses (as from 'getdevices') into individual
        strings.  It will also combine partial responses (as from a heavily loaded 
        network or NIC) to construct the complete string.  Responses are returned as
        ASCII strings *without* the trailing CR.
        """
        idx = self._partial.find(CR)
        if idx != -1:
            # there's a complete response available
            response = self._partial[0:idx]
            self._partial = self._partial[idx+1:]
            return response.decode('ascii')
        else:
            # we don't have a complete response; go get more
            data = await reader.read(1024)
            if not data:
                # socket closed on us; return whatever we have.
                # Note that this may be a mistake.  If the caller/client doesn't
                # realize that the connection is broken, we'll just spin around here
                # constantly returning nothing.  Keep an eye on it.
                response = self._partial
                self._partial = b''
                return response.decode('ascii')
            else:
                # append data read and see if there's a complete response in there.
                self._partial += data
                return await self.recv_response(reader)

            
    async def raw_command(self, data):
        """Send a command (not expecting a response).

        The 'data' should be well-formed: as 'bytes' terminated with a CR.
        This will send it and return.
        """
        async with self._cmd_lock:
            r, w = await asyncio.open_connection(self._host, self._port)
            try:
                self._partial = b''
                w.write(data)
                await w.drain()
                # this is a *command*.  No response expected.
            finally:
                w.close()
                await w.wait_closed()
                # wait_closed() does not seem to actually wait until the socket is
                # completely closed.  Consequenctly, attempting to open a new connection
                # on the same port too quickly will fail.  Hence the kludgy "sleep" hack:
                await asyncio.sleep(0.01)

        
    async def raw_request(self, data):
        """Send a command, expecting a response.

        The 'data' should be well-formed: as 'bytes' terminated with a CR.
        This will send it and wait for a response.  If the response is an 
        error it will raise CommandError; otherwise it will return the response
        *as an ASCII string* without the trailing CR.
        """
        async with self._cmd_lock:
            r, w = await asyncio.open_connection(self._host, self._port)
            self._partial = b''
            try:
                w.write(data)
                await w.drain()
                # this is a *request*.  There should be a response.
                response = await self.recv_response(r)
                self.error_check(response)
            finally:
                w.close()
                await w.wait_closed()
                # wait_closed() does not seem to actually wait until the socket is
                # completely closed.  Consequently, attempting to open a new connection
                # on the same port too quickly will fail.  Hence the kludgy "sleep" hack:
                await asyncio.sleep(0.01)
            return response


    async def blink(self, turn_on):
        """Blink the power light, or stop blinking it.

        If 'turn_on' is True (or non-zero), start/continue blinking.
        If False, stop blinking.
        """
        command = f"blink,{1 if turn_on else 0}"
        CMD = bytes(command, encoding='utf8')+CR
        await self.raw_command(CMD)
    
    async def getdevices(self):
        """Get the list of configured/installed devices in this GC-100.

        This will return a list of individual device strings, one per module.
        The semantics should be obvious, but you can parse each returned device 
        string with 'parse_device()'.
        """
        async with self._cmd_lock:
            r, w = await asyncio.open_connection(self._host, self._port)
            self._partial = b''
            devices = []
            endlist = False
            try:
                CMD = b'getdevices'+CR
                w.write(CMD)
                await w.drain()
            
                while not endlist:
                    response = await self.recv_response(r)
                    self.error_check(response)
                    tokens = response.split(SEP)
                    if tokens[0] == 'endlistdevices':
                        endlist = True
                    elif tokens[0] == 'device':
                        devices.append(response)
            finally:
                w.close()
                await w.wait_closed()
                await asyncio.sleep(0.01)
            return devices


    async def get_IR(self, addr):
        """Get the current mode setting for a particular port (connector address)"""
        command = f"get_IR,{addr}"
        CMD = bytes(command, encoding='utf8')+CR
        response = await self.raw_request(CMD)
        return response
    
    async def get_NET(self):
        """Get the current device network configuration.

        This returns a network configuration string containing the network address mode
        and current IP address/subnet/gateway.
        Use 'parse_Net()' to split/decode the response.
        """
        CMD = b'get_NET,0:1'+CR
        response = await self.raw_request(CMD)
        return response

    async def get_SERIAL(self, addr):
        """Get the current serial port parameters for the 'addr' connector port address.

        This returns a serial port configuration string containing the baud rate, flow control
        mode, and data parity.  Use 'parse_SERIAL()' to split/decode the response
        """
        command = f"get_SERIAL,{addr}"
        CMD = bytes(command, encoding='utf8')+CR
        response = await self.raw_request(CMD)
        return response

    async def getstate(self, addr):
        """Get the current state/value of the digital input on the 'addr' connector port address.
        
        This returns a 'state' response; use 'parse_state()' to decode it.
        """
        command = f"getstate,{addr}"
        CMD = bytes(command, encoding='utf8')+CR
        response = await self.raw_request(CMD)
        return response
    
    async def getversion(self, module):
        """Get the version number of 'module'.

        The 'module' number is 1, 2, 3, etc.  It is _not_ a "connector address".
        """
        command = f"getversion,{module}"
        CMD = bytes(command, encoding='utf8')+CR
        response = await self.raw_request(CMD)
        return response

    async def sendir(self, addr, freq, code, id=1, count=1, offset=3):
        """Send an IR command.

        This will construct the command for the designated connector 'addr'
        based on the carrier frequency (in Hz), request ID, repeat count,  
        repeat offset (see the API documentation for details), and the on/off 
        code pattern.
        """
        CMD = self.format_sendir(addr, freq, code, id, count, offset)
        response = await self.raw_request(CMD)
        return response

    async def setstate(self, addr, active):
        """Set the state of a digital output/relay on the 'addr' connector port address.

        If 'active' is True (or non-zero), set the relay to '1' (closed).
        If False, set it to '0' (open).
        
        This returns a 'state' response; use 'parse_state()' to decode it.
        """
        command = f"setstate,{addr},{1 if active else 0}"
        CMD = bytes(command, encoding='utf8')+CR
        response = await self.raw_request(CMD)
        return response
    
    async def set_IR(self, addr, mode):
        """Set the IR mode for the IR port at the given 'addr'.

        The 'addr' is a "connector address": module:port (e.g., '2:1').

        This expects a valid string for 'mode':
        'IR', 'SENSOR', 'SENSOR_NOTIFY', 'IR_NOCARRIER'.
        """
        command = f"set_IR,{addr},{mode}"
        CMD = bytes(command, encoding='utf8')+CR
        await self.raw_command(CMD)
        
    async def set_NET(self):
        """[Don't] set the device network configuration.

        If this were implemented, the device IP address might change, which might
        confuse/perturb existing clients.  If you *really* need to change the 
        network configuration, use the web interface (on port 80), or manually construct
        and send the command (e.g., via 'raw_command()').
        """
        raise NotImplementedError()

    async def set_SERIAL(self, addr, baudrate, flowcontrol, parity):
        """Set serial parameters for given 'addr'.

        The baudrate is an integer in [1200, 2400, 4800, 9600, 19200, 38400, 57600].
        The flowcontrol is boolean (or 0/1), where True denote Hardware flow control,
        and False denotes no flow control.
        The parity is one of ['PARITY_NO', 'PARITY_ODD', 'PARITY_EVEN']
        """
        command = f"set_SERIAL,{addr},{baudrate},{'FLOW_HARDWARE' if flowcontrol else 'FLOW_NONE'},{parity}"
        CMD = bytes(command, encoding='utf8')+CR
        await self.raw_command(CMD)

    async def stopir(self, addr):
        """Stop the currently running (repeated) IR command on connector port 'addr'.

        This is largely pointless with ephemeral connections, as you can't make a new connection 
        to send it while the existing 'sendir' command is still running.
        This is here for completeness.
        """
        command = f"stopir,{addr}"
        CMD = bytes(command, encoding='utf8')+CR
        await self.raw_command(CMD)
