import subprocess
import json


def create_session(timeout=30):
    proc = subprocess.Popen(["ubus", "-S", "call", "session", "create"], stdout=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    proc.poll()

    # cmd failed
    if not proc.returncode == 0:
        return None

    # failed to parse json
    try:
        output = json.loads(stdout)
    except ValueError:
        return None

    # missing session
    if "ubus_rpc_session" not in output:
        return None

    return output["ubus_rpc_session"]


def grant_listen(session):

    if not session:
        return False

    msg = {
        "ubus_rpc_session": session,
        "scope": "ubus", "objects": [
            ["websocket-listen", "listen-allowed"],
        ]
    }
    proc = subprocess.Popen(
        ["ubus", "-S", "call", "session", "grant", json.dumps(msg)], stdout=subprocess.PIPE)
    proc.communicate()
    proc.poll()

    if not proc.returncode == 0:
        return False

    return True
