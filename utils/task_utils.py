# utility fucntion to use when dealing with task model.
import uuid
import time

def generate_task_id():
    timestamp = int(time.time() * 1000)  # milliseconds since epoch
    unique_id = uuid.uuid4()
    return f"{timestamp}-{unique_id}"
