r"""
config.py - the ONLY file you should need to edit for paths/ports.

Layout on your laptop (Windows):
    D:\UniWork\mc\node1   -> Admin / News Organisation / Miner
    D:\UniWork\mc\node2   -> Publishers (P1, P2)
    D:\UniWork\mc\node3   -> Validators (V1, V2, V3)
"""
import os

CHAIN = "fakenews"
BASE = os.environ.get("MC_BASE", r"D:\UniWork\mc")   # change if your node folders are elsewhere

NODES = {
    "node1": {"datadir": os.path.join(BASE, "node1"), "rpcport": 7410},
    "node2": {"datadir": os.path.join(BASE, "node2"), "rpcport": 7420},
    "node3": {"datadir": os.path.join(BASE, "node3"), "rpcport": 7430},
}

# Which node holds the wallet of which role
ROLE_NODE = {"admin": "node1", "P": "node2", "V": "node3"}

# On-chain objects
ASSET = "CRED"                    # credibility token
STREAM_NEWS = "news"              # publishers write news items (hash + text)
STREAM_VOTES = "votes"            # validators write REAL/FAKE votes
STREAM_VERDICTS = "verdicts"      # admin writes final verdict (quorum result)
STREAMS = [STREAM_NEWS, STREAM_VOTES, STREAM_VERDICTS]

# Governance parameters (easy to change during the exam)
QUORUM = 2            # minimum number of validator votes before a verdict
STRIKE_LIMIT = 2      # strikes before write permission is revoked
REWARD = 1            # CRED tokens paid per correct action
INITIAL_CRED = 10     # CRED given to every publisher / validator at start
