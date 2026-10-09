# GUIDE - Run the MultiChain Fake-News Trust Chain on Windows

Your setup: MultiChain 2.3.3 in `D:\UniWork\multichain-windows-2.3.3`, Python 3.14.7, VS Code.
The Python files use **only the standard library** (no `pip install`). Python only talks to the nodes over
JSON-RPC (HTTP); **you create and start the nodes with MultiChain's own commands**.

## 0. What runs where

| Terminal | What it runs | Stays open? |
|---|---|---|
| T1 | `multichaind` node1 (Admin / News Organisation / Miner) | yes |
| T2 | `multichaind` node2 (Publishers P1, P2) | yes |
| T3 | `multichaind` node3 (Validators V1, V2, V3) | yes |
| T4 | `multichain-cli` commands and `python fakenews.py ...` | your working terminal |

In VS Code: Terminal -> New Terminal (the `+` button) four times. Use **Command Prompt** (dropdown next to `+`),
not PowerShell, then in **each** terminal run:

```
set PATH=%PATH%;D:\UniWork\multichain-windows-2.3.3
```

(If you prefer PowerShell: `$env:Path += ";D:\UniWork\multichain-windows-2.3.3"`.)
Check: `multichaind -version` prints `MultiChain 2.3.3 Daemon`.

## 1. Create the chain on node1 (T4)

```
mkdir D:\UniWork\mc
mkdir D:\UniWork\mc\node1
mkdir D:\UniWork\mc\node2
mkdir D:\UniWork\mc\node3
multichain-util create fakenews -datadir=D:\UniWork\mc\node1
dir D:\UniWork\mc\node1 /s /b
```

(`multichain-util` does not create missing folders - without `node1` you get
"cannot open file ...params.dat for writing". The `dir` line shows where params.dat was written.)

Open `D:\UniWork\mc\node1\fakenews\params.dat` in VS Code and set these lines
(**must be done BEFORE the first start; most values are frozen afterwards**):

```
chain-description = Fake news trust chain (MultiChain)
target-block-time = 5
default-network-port = 7411
default-rpc-port = 7410
anyone-can-connect = false
anyone-can-send = false
anyone-can-receive = false
anyone-can-create = false
anyone-can-issue = false
anyone-can-mine = false
anyone-can-activate = false
```

The `anyone-can-*` lines are already `false` by default in MultiChain; just confirm they say `false`.
That is the "permissioned network" of the paper (Fabric enrolment -> MultiChain permissions).
`target-block-time = 5` only makes the demo faster (default 15 s).

## 2. Start node1 (T1)

```
multichaind fakenews -datadir=D:\UniWork\mc\node1
```

Wait for `Node ready.` Leave it running. If Windows Firewall asks, click **Allow access**.
If blocks never appear (`getinfo` stays at 0 blocks), stop it and add `mining-requires-peers = false`
to params.dat **before** a fresh create (delete `D:\UniWork\mc` and redo step 1).

## 3. Add node2 and node3 (publishers and validators)

Node2 (T2):

```
multichaind fakenews@127.0.0.1:7411 -datadir=D:\UniWork\mc\node2 -port=7421 -rpcport=7420
```

It stops and prints a line like
`multichain-cli fakenews grant 1AbC...xyz connect` - **copy that address (ADDR2)**.
In T4 (admin grants it):

```
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 grant ADDR2 connect,send,receive
```

Run the node2 command in T2 again -> `Node ready.`

Node3 (T3) - same pattern, other ports:

```
multichaind fakenews@127.0.0.1:7411 -datadir=D:\UniWork\mc\node3 -port=7431 -rpcport=7430
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 grant ADDR3 connect,send,receive
multichaind fakenews@127.0.0.1:7411 -datadir=D:\UniWork\mc\node3 -port=7431 -rpcport=7430
```

Verify (T4) - **screenshot these**:

```
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 getinfo
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 getpeerinfo
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 listpermissions
```

`getinfo` should show `connections: 2`.

## 4. Run the system (T4, inside your VS Code project folder)

Copy the files (`config.py mc.py nlp.py dataset.py fakenews.py`) into `D:\UniWork\PythonProject` and:

```
python fakenews.py bootstrap          :: streams, CRED asset, roles, permissions (screenshot)
python fakenews.py publish --batch 1  :: P1 (honest) and P2 (fake spreader) post 5 items
python fakenews.py vote               :: V1,V2 experts + V3 NLP-only validator vote
python fakenews.py finalize           :: quorum -> verdicts, CRED rewards, strikes, REVOKE
python fakenews.py status             :: table of CRED balances, strikes, state (screenshot)
python fakenews.py publish --batch 2  :: P2 is now REJECTED by the chain (screenshot!)
python fakenews.py vote
python fakenews.py finalize           :: V3 gets 2nd strike -> votes.write revoked
python fakenews.py status
```

Expected story: P2 posts two fakes -> 2 strikes -> `news.write` revoked -> the next publish by P2 is
**rejected by the blockchain itself**. V3 (NLP-only) votes against the quorum twice -> loses `votes.write`.
Honest validators accumulate CRED.

Proof directly from MultiChain (screenshots):

```
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 liststreams
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 liststreamitems verdicts
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 listpermissions news.write
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 listassets
```

## 5. Same system with ONLY multichain-cli (no Python) - the exam fallback

Let `CLI = multichain-cli fakenews -datadir=D:\UniWork\mc\node1` and `ADMIN` = output of `CLI getaddresses`.

```
CLI getnewaddress                              :: (run on node2/node3 datadir with -rpcport) -> publisher/validator address
CLI grant PUB send,receive
CLI create stream news false
CLI create stream votes false
CLI create stream verdicts false
CLI grant PUB news.write
CLI grant VAL votes.write
CLI issue ADMIN "{\"name\":\"CRED\",\"open\":true}" 100000 1
CLI sendassetfrom ADMIN PUB CRED 10
CLI subscribe news
```

Publishing data on Windows is easiest as **hex** (no quoting problems). In PowerShell/cmd:
`python -c "print('Miracle cure banned!'.encode().hex())"` -> paste into

```
multichain-cli fakenews -datadir=D:\UniWork\mc\node2 -rpcport=7420 publishfrom PUB news n9 <HEX>
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 liststreamkeyitems news n9
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 revoke PUB news.write
```

## 6. Optional: more PoA-like consensus (second miner)

```
multichain-cli fakenews -datadir=D:\UniWork\mc\node3 -rpcport=7430 getaddresses       :: -> ADDR3
multichain-cli fakenews -datadir=D:\UniWork\mc\node1 grant ADDR3 mine
```

Blocks are now created in rotation by two permissioned miners (MultiChain's `mining-diversity` rule) -
that is MultiChain's equivalent of Proof-of-Authority round-robin.

## 7. Exam modification cheat-sheet

| They ask you to... | Change |
|---|---|
| Quorum 3 of 3 / stricter | `QUORUM` in `config.py` |
| Less/more tolerance | `STRIKE_LIMIT`, `REWARD`, `INITIAL_CRED` in `config.py` |
| Add a validator V4 | add `"V4"` in `roles.json` after `node3 getnewaddress` + `grant addr send,receive` + `grant addr votes.write` |
| Add a 4th stream (e.g. `appeals`) | append to `STREAMS` in `config.py`; `bootstrap` creates it |
| Change fake/real keywords | `SEED` dict in `nlp.py` |
| Different ports/folders | `NODES`/`BASE` in `config.py` (and `-port/-rpcport` flags) |
| Use another asset name | `ASSET` in `config.py` |
| New news items | `dataset.py` |

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `multichaind` not recognised | run the `set PATH=...` line in that terminal |
| `Cannot find ...multichain.conf` | that node was never started once (step 3) or `BASE` in config.py is wrong |
| `Cannot reach node at 127.0.0.1:74xx` | node not running or wrong `-rpcport` |
| node2/3 says `connect permission` | you did not run the `grant ... connect` for **that** printed address |
| `Port ... in use` | another node uses it; stop it or change `-port/-rpcport` |
| `Publishing in this stream requires write permission` | expected for revoked/unauthorised addresses (this is the demo!) |
| Reads return nothing on node2/3 | stream not subscribed yet: `multichain-cli ... subscribe news` |
| Start from scratch | close T1-T3 (Ctrl+C), delete `D:\UniWork\mc`, delete `roles.json` and `nlp_weights.json`, redo from step 1 |
