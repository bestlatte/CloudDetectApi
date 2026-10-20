import asyncio
import json
import logging
import os
import uuid

from app.jobs.monitor_runtime import claim_due_monitors, save_probe_result
from app.services.monitor_engine import execute_due_monitors


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    execution_id = os.getenv("CLOUD_RUN_EXECUTION") or os.getenv("EXECUTION_ID") or str(uuid.uuid4())
    summary = asyncio.run(
        execute_due_monitors(
            execution_id,
            claim_due=claim_due_monitors,
            save_result=save_probe_result,
        )
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

