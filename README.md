# pygc100

An async library to control Global Cache GC-100 devices.

Global Cache (https://www.globalcache.com/) makes several products which can control non-network devices, such as older TV's and AV equipment, over a network.  

This library provides a Python async API to the GC-100 family of network adapters (https://www.globalcache.com/products/gc-100/).  It has some limited applicability to Global Cache iTach adapters; YMMV.

## Global Cache GC-100
The GC-100 has control modules for 

* IR output and digital input
* Serial data (RS-232)
* Relays

While the pygc100 library supports all of these, it was designed specifically for IR output and Serial data.  The IR (digital) input and Relay functions have not been tested.

In particular, due to the networking design, digital input as "sensor notify" will not work as expected.  If you require unsolicited notification of input changes, you'll need to make some modifications.

## Installation

At this point, pygc100 is not available in PyPi.

Download or clone the repository, and install it manually:

```bash
$ pip install -e /path/to/downloaded/pygc100
```

## Usage

This is not a tutorial on the GC-100 API.  See the Global Cache documentation for available commands and command formats (https://www.globalcache.com/files/docs/API-GC-100.pdf).  

This library manages connections to the GC-100, and simplifies the tedious formatting of commands.  But you still need to know what those commands are and how to use them.

You can find a few extremely simple sample applications in the "examples" folder.

### Concepts

The library defines one class, `GC100`, for the device itself, and individual classes, `Digital_in`, `IR_out`, `Relay`, and `Serial` for each module and/or port on the device (that you want to control).

Functions which interact with the GC-100 are asynchronous, so you'll need to brush up on your `asyncio`.  Note that the code snippets below do *not* include all of the necessary `asyncio` scaffolding; complete code may be found in the examples.

For the most part, the library expects success.  In general, exceptions are simply raised to the caller.  The library does, however, define a `CommandError` exception class which indicates error reponses returned from GC-100 commands.

### Getting Started

First, you need to connect to the GC-100.  It's a network device, so you'll need its address.  The GC-100 default TCP port is assumed, but you can change it if you must.
```python
import asyncio
import gc_100

gc = gc_100.GC100(host='192.168.1.99')
```

At this point, you can configure and query the device:
```python
await gc.blink(True)

response = await gc.get_NET()
info = gc.parse_NET(response)
print(f"Network (raw) = {response}")
print(f"Network (cooked) = {info}")
```

And you can send commands:
```python
on_off = '50,100,12,12,12,24,12,24,12,600'
response = await gc.sendir(addr='2:1', freq=38000, code=on_off)
```

This works, but typically you'll create an object that's associated with the port, and send commands through it:
```python
avr = gc_100.IR_out(gc, addr='2:1')

on_off = '50,100,12,12,12,24,12,24,12,600'
response = await avr.sendir(freq=38000, code=on_off)
```

For the most part, ports are identified by their "connector address", which is the GC-100 module number (here, 2) and the port number within that module (here, 1).  

Note that I/O classes, such as `IR_out`, don't actually configure the port or the device; they expect the underlying port to already be configured properly -- in this case, that there is an IR module in position 2, and that its first port is configured for IR output.


### IR Output

The GC-100 describes the IR commands that it sends based on the underlying carrier frequency (e.g. 38kHz) and the pattern of turning that carrier frequency on and off, as a count of carrier frequency periods.

Obviously, every component that you may want to control has a different set of codes -- and usually quite a few of them.  You'll have to find out what they are.   Global Cache maintains a database of IR codes for various equipment at  https://irdb.globalcache.com/

You can format and send IR codes, as shown above:
```python
avr = gc_100.IR_out(gc, addr='2:1')

power_on = '50,100,12,12,12,24,12,24,12,600'
input_cd = '50,100,12,24,12,12,12,12,12,600'
muted_on = '50,100,12,24,12,24,12,12,12,600'
response = await avr.sendir(freq=38000, code=power_on)
response = await avr.sendir(freq=38000, code=input_cd)
```

But if the codes are static, it may be more efficient to pre-format them:
```python
avr = gc_100.IR_out(gc, addr='2:1')

power_on = avr.format_sendir(freq=3800, code='50,100,12,12,12,24,12,24,12,600')

try:
    response = await avr.sendir_raw(power_on)
except gc_100.CommandError as e:
    print(f"Bad Command: {e.str()}")
```

IR codes are particularly finicky; handling errors is highly recommended.

### Serial Data

The GC-100 dedicates a network TCP port for each serial (RS-232) module.  You send your data to the GC-100 over the network using that port, and the GC-100 forwards it on the RS-232 connection.  Similarly, when the GC-100 receives RS-232 data, it packages it up and forwards it to you on that port over the network.

The network TCP port remains connected throughout.  You have to take some precautions, since you may receive serial data at any time.

In addition to the GC-100 connection address, for serial ports you also need to supply the zero-based serial port index (this is used to identify the correct TCP port number):
```python
dvd = gc_100.Serial(gc, addr='1:1', index=0)
```

You also have to explicitly "connect" and "disconnect" from the port:
```python
await dvd.connect()

# do something clever

await dvd.disconnect()
```

Once connected, you can send and receive serial data (in bytes).  Whatever you send is passed through directly, unmodified:
```python
await dvd.send(b'hello\r')

response = await dvd.recv(80) # up to 80 bytes
print(f"received ->{response}<-")
```

One strategy for handling unsolicited incoming data is to define a separate asynchronous function to receive and process it:
```python
async def ReadData(serial):
    try:
        while True:
            msg = await serial.recv(1024)
            # process(msg)
            print(f"processing ->{msg}<-")
    except Exception as e:
        print(f"Reader failed with: {e} ({type(e)})")
```

Which you can start running after connecting to the serial port:
```python
dvd = gc_100.Serial(gc, addr='1:1', index=0)
await dvd.connect()

t = asyncio.create_task(Reader(dvd))

# do things until finished

t.cancel()
await t
await dvd.disconnect()
```
