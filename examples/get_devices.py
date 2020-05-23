#! /usr/bin/env python3
import argparse
import asyncio
import gc_100
import datetime

parser = argparse.ArgumentParser(description="Get Global Cache GC-100 device configuration")
parser.add_argument('--host', default="192.168.11.120",
                    help="IPv4 address of GC-100")
parser.add_argument('--port', type=int, default=4998,
                    help="TCP control port of GC-100 (default = 4998")

args = parser.parse_args()

print(f"Host ->{args.host}<-")
print(f"Port ->{args.port}<-")

gc = gc_100.GC100(args.host, args.port)

async def main():
    try:
        print("connecting...")
        devices = await gc.getdevices()

        print("devices:")
        for d in devices:
            print(f"  {gc.parse_device(d)}")

        print("all done")

    except Exception as e:
        print(f"Zoiks! {e}")

    
if __name__ == "__main__":
    asyncio.run(main())
    
