"""
mc.py - tiny MultiChain JSON-RPC client (standard library only, no pip needed).

Every MultiChain API command (grant, create, issue, publishfrom, ...) is
available as a method:   node.grant(addr, "send,receive")
"""
import base64
import json
import os
import urllib.error
import urllib.request


class MultiChainError(Exception):
    pass


def _read_conf(path):
    conf = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            conf[k.strip()] = v.strip()
    return conf


class MultiChain:
    def __init__(self, datadir, chain, rpcport, host="127.0.0.1"):
        conf_path = os.path.join(datadir, chain, "multichain.conf")
        if not os.path.exists(conf_path):
            raise MultiChainError(
                "Cannot find %s - has this node been started once?" % conf_path)
        conf = _read_conf(conf_path)
        token = base64.b64encode(
            ("%s:%s" % (conf["rpcuser"], conf["rpcpassword"])).encode()).decode()
        self.url = "http://%s:%d" % (host, rpcport)
        self.chain = chain
        self.headers = {"Content-Type": "application/json",
                        "Authorization": "Basic " + token}

    def call(self, method, *params):
        body = json.dumps({"method": method, "params": list(params),
                           "id": 1, "chain_name": self.chain}).encode()
        req = urllib.request.Request(self.url, data=body, headers=self.headers)
        try:
            raw = urllib.request.urlopen(req, timeout=30).read()
        except urllib.error.HTTPError as e:      # MultiChain sends errors as HTTP 500 + JSON
            raw = e.read()
        except urllib.error.URLError as e:
            raise MultiChainError(
                "Cannot reach node at %s (is multichaind running?): %s" % (self.url, e))
        resp = json.loads(raw.decode())
        if resp.get("error"):
            raise MultiChainError("%s -> %s" % (method, resp["error"].get("message", resp["error"])))
        return resp["result"]

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *args: self.call(name, *args)


def item_json(item):
    """Return the JSON payload of a stream item (or {} if it is not JSON)."""
    data = item.get("data")
    if isinstance(data, dict) and "json" in data:
        return data["json"]
    return {}
