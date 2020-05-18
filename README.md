# pygc100

An async library to control Global Cache GC-100 devices.

Global Cache (https://www.globalcache.com/) makes several products which can control non-network devices, such as older TV's and AV equipment, over a network.  

This library provides a Python async API to the GC-100 family of network adapters (https://www.globalcache.com/products/gc-100/).

## Global Cache GC-100
The GC-100 has control modules for 

* IR output and digital input
* Serial data (RS-232)
* Digital relays

While the pygc100 library supports all of these, it was designed specifically for IR output and serial data.

## Installation

At this point, pygc100 is not available in PyPi.

Download the repository, and install it manually:

```bash
$ pip install -e /path/to/downloaded/pygc100
```
