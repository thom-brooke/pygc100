#! /usr/bin/env python3
import argparse
import asyncio
import gc_100
import datetime

parser = argparse.ArgumentParser(description="Connect and listen to Global Cache GC-100 (IR and Serial)")
parser.add_argument('--host', default="192.168.11.120",
                    help="IPv4 address of GC-100")
parser.add_argument('--port', type=int, default=4998,
                    help="TCP control port of GC-100 (default = 4998")
parser.add_argument('--addr', default='1:1',
                    help="GC-100 connector address (default='1:1')")
parser.add_argument('--index', type=int, default=0,
                    help="Serial port 'index' (0, the default, is first serial port)")
parser.add_argument('--timeout', type=int, default=0,
                    help="how long to wait for responses before closing port; 0 = indefinite (default)")
# parser.add_argument('--quiet', ...)

args = parser.parse_args()

print(f"Host ->{args.host}<-")
print(f"Port ->{args.port}<-")
print(f"Addr ->{args.addr}<-")
print(f"Index = {args.index}")

gc = gc_100.GC100(args.host, args.port)
serial = gc_100.Serial(gc, args.addr, args.index)

async def Reader(serial):
    try:
        while True:
            t_start = datetime.datetime.now()
            msg = await serial.recv(1024)
            print(f"recv ->{msg}<-\n")
    except Exception as e:
        t_end = datetime.datetime.now()
        print(f"Reader punted at {t_end - t_start} with ->{e} ({type(e)})")
        
        
async def main():
    try:
        print("connecting...")
        await serial.connect()

        print("start reader...")
        t = asyncio.create_task(Reader(serial))

        t_start = datetime.datetime.now()
        print(f"waiting for data (timeout = {args.timeout})...")
        if args.timeout == 0:
            dummy = input()
        else:
            await asyncio.sleep(args.timeout)
        t_end = datetime.datetime.now()
        print(f"punted after {t_end - t_start}.")
        
        print("cancel reader...")
        t.cancel()
        await t
        await serial.disconnect()
        print("all done")

    except Exception as e:
        print(f"Zoiks! {e}")

    
if __name__ == "__main__":
    asyncio.run(main())
    
