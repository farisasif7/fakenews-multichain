# Fake News Trust Chain on MultiChain

A permissioned-blockchain implementation of *"Fake Media Detection Based on NLP and Blockchain"*,
built on **MultiChain 2.3.3** with a pure-standard-library Python client (no `pip install`).

- **Publishers** post news items to the `news` stream.
- **Validators** (human experts + an NLP detector) vote REAL/FAKE on the `votes` stream.
- **Admin** finalizes a quorum verdict on the `verdicts` stream, pays `CRED` tokens for correct actions,
  issues strikes, and revokes write permission from repeat offenders.

## Files
| File | Purpose |
|---|---|
| `config.py` | Paths, ports, governance parameters (quorum, strike limit, rewards) |
| `mc.py` | Minimal MultiChain JSON-RPC client |
| `nlp.py`, `nlp_weights.json` | Lightweight NLP fake-news scorer and its weights |
| `dataset.py` | Sample news items (batch 1 / batch 2) |
| `fakenews.py` | CLI: `bootstrap`, `publish`, `vote`, `finalize`, `status` |
| `GUIDE.md` | Full step-by-step Windows setup (nodes, params.dat, permissions) |
| `Fake_News_MultiChain_Report_v2.docx` | Project report |

## Requirements
- Python 3.9+ (tested on 3.14)
- [MultiChain 2.3.3](https://www.multichain.com/download-community/) (binaries are not included in this repo)

## Quick start
1. Follow `GUIDE.md` sections 0-3 to create the `fakenews` chain and start 3 nodes
   (override the node folder with `set MC_BASE=C:\path\to\mc` if not `D:\UniWork\mc`).
2. Run:
```
python fakenews.py bootstrap
python fakenews.py publish --batch 1
python fakenews.py vote
python fakenews.py finalize
python fakenews.py status
python fakenews.py publish --batch 2   # the revoked publisher is now rejected by the chain
```
`bootstrap` generates `roles.json` (local wallet addresses; git-ignored).
