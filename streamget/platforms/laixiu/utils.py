import hashlib
import time
import uuid


def generate_uuid(ua_type: str):
    if ua_type == "mobile":
        return str(uuid.uuid4())
    return str(uuid.uuid4()).replace('-', '')


def calculate_sign(ua_type: str = 'pc'):
    a = int(time.time() * 1000)
    s = generate_uuid(ua_type)
    u = 'kk792f28d6ff1f34ec702c08626d454b39pro'

    input_str = f"web{s}{a}{u}"
    md5_hash = hashlib.md5(input_str.encode('utf-8')).hexdigest()

    return {
        'timestamp': a,
        'imei': s,
        'requestId': md5_hash,
        'inputString': input_str
    }
