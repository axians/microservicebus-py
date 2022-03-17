#!/usr/bin/env python3.7
import asyncio
import logging
import os
import sys
sys.path.insert(1, os.path.dirname(__file__))
from orchestrator_service import Orchestrator

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

def main():
    try:
        print(f"pid: {os.getpid()}")
        sys.path.append(os.path.abspath('../lib'))

        orchestrator = Orchestrator("orchestrator", asyncio.Queue())
        orchestrator.loop.create_task(orchestrator.Start())
        orchestrator.loop.run_forever()
    except KeyboardInterrupt:
        logging.info("Process interrupted")
    finally:
        orchestrator.loop.close()
        logging.info("Successfully shutdown the Mayhem service.")


if __name__ == "__main__":
    main()
