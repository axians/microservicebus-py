#!/usr/bin/env python3.7
import asyncio, logging
from orchestrator_service import Orchestrator

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

def main():
    try:
        orchestrator = Orchestrator("orchestrator", asyncio.Queue())
        orchestrator.loop.create_task(orchestrator.Start())
        orchestrator.loop.run_forever()
        print("")
    except KeyboardInterrupt:
        logging.info("Process interrupted")
    finally:
        orchestrator.loop.close()
        logging.info("Successfully shutdown the Mayhem service.")

if __name__ == "__main__":
    main()