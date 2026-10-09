"""
fakenews.py - MultiChain version of "Fake Media Detection Based on NLP and Blockchain".

Usage (after the 3 nodes are running, see GUIDE.md):
    python fakenews.py bootstrap          # create streams, asset, roles, permissions
    python fakenews.py publish --batch 1  # publishers post news           (stream: news)
    python fakenews.py vote               # validators vote REAL/FAKE      (stream: votes)
    python fakenews.py finalize           # quorum -> verdict, CRED reward, strikes, revoke
    python fakenews.py status             # balances, permissions, verdicts
    python fakenews.py publish --batch 2  # P2 is now blocked by the chain
    python fakenews.py vote ; python fakenews.py finalize ; python fakenews.py status

Manual vote (useful in the exam):   python fakenews.py vote --news n3 --validator V1 --value REAL
"""
import argparse
import hashlib
import json
import os
import sys
import time

from config import *
from dataset import BY_ID, NEWS
from mc import MultiChain, MultiChainError, item_json
from nlp import Detector

HERE = os.path.dirname(os.path.abspath(__file__))
ROLES_FILE = os.path.join(HERE, "roles.json")


# ----------------------------------------------------------------- helpers
def connect():
    nodes = {}
    for name, c in NODES.items():
        nodes[name] = MultiChain(c["datadir"], CHAIN, c["rpcport"])
    return nodes


def load_roles():
    if os.path.exists(ROLES_FILE):
        with open(ROLES_FILE) as f:
            return json.load(f)
    return None


def save_roles(r):
    with open(ROLES_FILE, "w") as f:
        json.dump(r, f, indent=2)


def node_for(label, nodes):
    key = "admin" if label == "admin" else label[0]
    return nodes[ROLE_NODE[key]]


def all_labels(roles):
    d = {"admin": roles["admin"]}
    d.update(roles["publishers"])
    d.update(roles["validators"])
    return d


def label_of(addr, roles):
    for k, v in all_labels(roles).items():
        if v == addr:
            return k
    return addr[:8] + "..."


def short(a):
    return a[:6] + ".." + a[-4:]


def try_(fn, *a):
    """Run an RPC call, tolerate 'already exists' style errors."""
    try:
        return fn(*a)
    except MultiChainError as e:
        msg = str(e).lower()
        if "already" in msg or "exist" in msg or "same name" in msg:
            return None
        raise


def retry(fn, *a, tries=12, delay=3):
    """Retry while the chain is still confirming earlier transactions (blocks take a few seconds)."""
    for i in range(tries):
        try:
            return fn(*a)
        except MultiChainError as e:
            if i == tries - 1:
                raise
            time.sleep(delay)


def wait_confirmed(node, streams, timeout=90):
    """Wait until the new streams are in a block (grants on them need that)."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            if all(node.liststreams(s)[0].get("confirmed", True) for s in streams):
                return
        except MultiChainError:
            return            # command not available / not needed
        time.sleep(3)


def read_items(node, stream, key=None):
    if key is None:
        return node.liststreamitems(stream, False, 1000)
    return node.liststreamkeyitems(stream, key, False, 1000)


def backlog_texts(nodes):
    """Texts of news already confirmed FAKE (the paper's 'backlog for future detection')."""
    out = []
    news = {it["keys"][0]: item_json(it) for it in read_items(nodes["node1"], STREAM_NEWS)}
    for v in read_items(nodes["node1"], STREAM_VERDICTS):
        if item_json(v).get("verdict") == "FAKE" and v["keys"][0] in news:
            out.append(news[v["keys"][0]].get("text", ""))
    return out


def cred_balance(node, addr):
    try:
        for b in node.getaddressbalances(addr, 0):
            if b.get("name") == ASSET:
                return b["qty"]
    except MultiChainError:
        pass
    return 0


def strikes_from_chain(nodes):
    """strikes[address] derived ONLY from the verdicts stream (auditable)."""
    s = {}
    for v in read_items(nodes["node1"], STREAM_VERDICTS):
        j = item_json(v)
        for a in j.get("wrong_validators", []):
            s[a] = s.get(a, 0) + 1
        if j.get("verdict") == "FAKE" and j.get("publisher"):
            s[j["publisher"]] = s.get(j["publisher"], 0) + 1
    return s


# ----------------------------------------------------------------- commands
def cmd_bootstrap(args):
    nodes = connect()
    n1, n2, n3 = nodes["node1"], nodes["node2"], nodes["node3"]
    for name, n in nodes.items():
        info = n.getinfo()
        print("[ok] %s  chain=%s  blocks=%s  connections=%s" %
              (name, info["chainname"], info["blocks"], info["connections"]))

    admin = n1.getaddresses()[0]
    roles = load_roles()
    if not roles:
        roles = {"admin": admin,
                 "publishers": {"P1": n2.getnewaddress(), "P2": n2.getnewaddress()},
                 "validators": {"V1": n3.getnewaddress(), "V2": n3.getnewaddress(),
                                "V3": n3.getnewaddress()},
                 "revoked": []}
        save_roles(roles)
    print("[ok] admin address:", admin)

    # 1. basic permissions (permissioned network: nobody can send/receive by default)
    for lbl, addr in list(roles["publishers"].items()) + list(roles["validators"].items()):
        n1.grant(addr, "send,receive")
        print("[grant] %s %s send,receive" % (lbl, short(addr)))

    # 2. streams (restricted: only addresses holding <stream>.write may publish)
    for s in STREAMS:
        try_(n1.create, "stream", s, False)
        print("[stream] created %s (restricted)" % s)
    wait_confirmed(n1, STREAMS)
    for s in STREAMS:
        retry(n1.grant, admin, s + ".write")

    # 3. credibility asset
    try:
        n1.issue(admin, {"name": ASSET, "open": True}, 100000, 1)
        print("[asset] issued 100000 %s" % ASSET)
    except MultiChainError as e:
        print("[asset] %s (already issued?)" % e)

    # 4. role-specific stream permissions + initial credibility
    for lbl, addr in roles["publishers"].items():
        retry(n1.grant, addr, STREAM_NEWS + ".write")
    for lbl, addr in roles["validators"].items():
        retry(n1.grant, addr, STREAM_VOTES + ".write")
    for lbl, addr in list(roles["publishers"].items()) + list(roles["validators"].items()):
        retry(n1.sendassetfrom, admin, addr, ASSET, INITIAL_CRED)
        print("[asset] sent %d %s to %s" % (INITIAL_CRED, ASSET, lbl))

    # 5. every node subscribes to the streams so it can read them
    for name, n in nodes.items():
        for s in STREAMS:
            for _ in range(15):
                try:
                    n.subscribe(s)
                    break
                except MultiChainError as e:
                    if "already" in str(e).lower():
                        break
                    time.sleep(2)
    print("\nBootstrap finished. Next: python fakenews.py publish --batch 1")


def cmd_publish(args):
    nodes = connect()
    roles = load_roles()
    n2 = nodes["node2"]
    for n in NEWS:
        if n["batch"] != args.batch:
            continue
        if read_items(n2, STREAM_NEWS, n["id"]):
            print("[skip] %s already on chain" % n["id"])
            continue
        addr = roles["publishers"][n["publisher"]]
        payload = {"title": n["title"], "text": n["text"],
                   "sha256": hashlib.sha256(n["text"].encode()).hexdigest(),
                   "ts": int(time.time())}
        try:
            txid = n2.publishfrom(addr, STREAM_NEWS, n["id"], {"json": payload})
            print("[news] %s by %s published  tx=%s.." % (n["id"], n["publisher"], txid[:12]))
        except MultiChainError as e:
            print("[REJECTED] %s by %s -> %s" % (n["id"], n["publisher"], e))


def cast_vote(nodes, roles, news_id, vlabel, value):
    n3 = nodes["node3"]
    addr = roles["validators"][vlabel]
    txid = n3.publishfrom(addr, STREAM_VOTES, news_id, {"json": {"vote": value, "by": vlabel}})
    print("[vote] %s: %s -> %s  tx=%s.." % (news_id, vlabel, value, txid[:12]))


def votes_for(nodes, roles, news_id):
    """latest vote per validator address (revoked validators ignored)."""
    out = {}
    for it in read_items(nodes["node3"], STREAM_VOTES, news_id):
        addr = it["publishers"][0]
        if addr in roles["validators"].values() and addr not in roles["revoked"]:
            out[addr] = item_json(it).get("vote")
    return out


def cmd_vote(args):
    nodes = connect()
    roles = load_roles()
    if args.news and args.validator and args.value:
        try:
            cast_vote(nodes, roles, args.news, args.validator, args.value.upper())
        except MultiChainError as e:
            print("[REJECTED]", e)
        return
    det = Detector()
    backlog = backlog_texts(nodes)
    for it in read_items(nodes["node3"], STREAM_NEWS):
        nid = it["keys"][0]
        text = item_json(it).get("text", "")
        hint, conf, feats = det.predict(text, backlog)
        print("\n%s  NLP hint=%s (conf %.2f) %s" % (nid, hint, conf, feats))
        have = votes_for(nodes, roles, nid)
        for vlabel, vaddr in roles["validators"].items():
            if vaddr in have or vaddr in roles["revoked"]:
                continue
            # --- simulated validators -------------------------------------------------
            # V1, V2: human experts (use ground truth).  V3: automatic validator = NLP only.
            if vlabel == "V3" or nid not in BY_ID:
                value = hint
            else:
                value = BY_ID[nid]["truth"]
            try:
                cast_vote(nodes, roles, nid, vlabel, value)
            except MultiChainError as e:
                print("[REJECTED] %s -> %s" % (vlabel, e))


def cmd_finalize(args):
    nodes = connect()
    roles = load_roles()
    n1 = nodes["node1"]
    admin = roles["admin"]
    det = Detector()
    done = {v["keys"][0] for v in read_items(n1, STREAM_VERDICTS)}
    strikes = strikes_from_chain(nodes)
    for it in read_items(n1, STREAM_NEWS):
        nid = it["keys"][0]
        if nid in done:
            continue
        pub = it["publishers"][0]
        text = item_json(it).get("text", "")
        votes = votes_for(nodes, roles, nid)
        if len(votes) < QUORUM:
            print("[wait] %s has %d/%d votes" % (nid, len(votes), QUORUM))
            continue
        fake = sum(1 for v in votes.values() if v == "FAKE")
        real = sum(1 for v in votes.values() if v == "REAL")
        if fake == real:
            print("[tie ] %s - need another validator" % nid)
            continue
        verdict = "FAKE" if fake > real else "REAL"
        backlog = backlog_texts(nodes)
        pred, _, _ = det.predict(text, backlog)
        wrong = [a for a, v in votes.items() if v != verdict]
        record = {"verdict": verdict, "real": real, "fake": fake, "nlp_pred": pred,
                  "publisher": pub, "wrong_validators": wrong, "ts": int(time.time())}
        n1.publishfrom(admin, STREAM_VERDICTS, nid, {"json": record})
        print("\n[VERDICT] %s = %s  (REAL %d / FAKE %d)  publisher=%s" %
              (nid, verdict, real, fake, label_of(pub, roles)))

        # --- reward correct validators, and the publisher if news was REAL --------
        for a, v in votes.items():
            if v == verdict:
                n1.sendassetfrom(admin, a, ASSET, REWARD)
                print("   +%d %s -> %s (correct vote)" % (REWARD, ASSET, label_of(a, roles)))
        if verdict == "REAL":
            n1.sendassetfrom(admin, pub, ASSET, REWARD)
            print("   +%d %s -> %s (verified news)" % (REWARD, ASSET, label_of(pub, roles)))

        # --- strikes + revoke -------------------------------------------------------
        for a in wrong:
            strikes[a] = strikes.get(a, 0) + 1
            print("   strike %d/%d -> %s (vote against consensus)" %
                  (strikes[a], STRIKE_LIMIT, label_of(a, roles)))
        if verdict == "FAKE":
            strikes[pub] = strikes.get(pub, 0) + 1
            print("   strike %d/%d -> %s (published fake news)" %
                  (strikes[pub], STRIKE_LIMIT, label_of(pub, roles)))
        for a, c in strikes.items():
            if c >= STRIKE_LIMIT and a not in roles["revoked"]:
                perm = STREAM_NEWS + ".write" if a in roles["publishers"].values() \
                    else STREAM_VOTES + ".write"
                try:
                    n1.revoke(a, perm)
                    roles["revoked"].append(a)
                    save_roles(roles)
                    print("   !! REVOKED %s from %s (credibility too low)" %
                          (perm, label_of(a, roles)))
                except MultiChainError as e:
                    print("   revoke failed:", e)

        # --- RL step: verdict is the reward signal for the NLP model --------------
        r = det.feedback(text, verdict, backlog)
        det.save()
        print("   NLP predicted %s -> reward %+d (model %s)" %
              (pred, r, "unchanged" if r > 0 else "updated"))


def cmd_status(args):
    nodes = connect()
    roles = load_roles()
    strikes = strikes_from_chain(nodes)
    print("\n%-6s %-14s %-6s %-8s %s" % ("ROLE", "ADDRESS", "CRED", "STRIKES", "STATE"))
    for lbl, addr in all_labels(roles).items():
        node = node_for(lbl, nodes)
        state = "REVOKED" if addr in roles["revoked"] else "active"
        print("%-6s %-14s %-6s %-8s %s" % (lbl, short(addr), cred_balance(node, addr),
                                          strikes.get(addr, 0), state))
    print("\nVERDICTS")
    for v in read_items(nodes["node1"], STREAM_VERDICTS):
        j = item_json(v)
        print("  %-4s %-5s REAL %s / FAKE %s   NLP said %s   tx=%s.." %
              (v["keys"][0], j["verdict"], j["real"], j["fake"], j["nlp_pred"], v["txid"][:10]))
    print("\nITEM COUNTS  news=%d  votes=%d  verdicts=%d" % (
        len(read_items(nodes["node1"], STREAM_NEWS)),
        len(read_items(nodes["node1"], STREAM_VOTES)),
        len(read_items(nodes["node1"], STREAM_VERDICTS))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bootstrap").set_defaults(fn=cmd_bootstrap)
    p = sub.add_parser("publish"); p.add_argument("--batch", type=int, default=1); p.set_defaults(fn=cmd_publish)
    v = sub.add_parser("vote")
    v.add_argument("--news"); v.add_argument("--validator"); v.add_argument("--value")
    v.set_defaults(fn=cmd_vote)
    sub.add_parser("finalize").set_defaults(fn=cmd_finalize)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    args = ap.parse_args()
    try:
        args.fn(args)
    except MultiChainError as e:
        print("\nMultiChain error:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
