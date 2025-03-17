# utility fucntion to use when dealing with task model.
import time
import uuid


def generate_task_id():
    timestamp = int(time.time() * 1000)  # milliseconds since epoch
    unique_id = uuid.uuid4()

    return f"{timestamp}-{unique_id}"

def generate_new_id(prefix: str="") -> str:
    timestamp = str(int(time.time()))
    unique_id = uuid.uuid4()

    return f"{prefix}{timestamp}{unique_id.hex}"
