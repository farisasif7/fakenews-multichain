"""
dataset.py - small FICTIONAL demo news set (no real people/organisations).
'truth' is used only to SIMULATE honest validators; the chain never sees it.
batch 1 is published first; batch 2 is published after P2 has been penalised.
"""
NEWS = [
    {"id": "n1", "batch": 1, "publisher": "P1", "truth": "REAL",
     "title": "City council approves new bus lanes",
     "text": "According to a council statement, officials confirmed that the new bus lanes "
             "will open next month. The report published by the transport ministry shows "
             "a twelve percent drop in travel time."},
    {"id": "n2", "batch": 1, "publisher": "P1", "truth": "REAL",
     "title": "University study on sleep",
     "text": "A university study published this week reported that students who sleep eight "
             "hours score higher. The data was announced by a spokesperson."},
    {"id": "n3", "batch": 1, "publisher": "P1", "truth": "REAL",
     "title": "BREAKING: Harbour bridge reopens",
     "text": "BREAKING! The harbour bridge reopened this morning after repair work. Engineers "
             "inspected the structure and the road authority said traffic is back to normal."},
    {"id": "n4", "batch": 1, "publisher": "P2", "truth": "FAKE",
     "title": "Miracle cure banned by authorities",
     "text": "SHOCKING secret exposed! A miracle cure is banned by authorities. Share this "
             "urgent message with everyone before it is deleted!"},
    {"id": "n5", "batch": 1, "publisher": "P2", "truth": "FAKE",
     "title": "Leaked memo proves moon hoax",
     "text": "A leaked anonymous memo exposes the hoax, guaranteed 100 percent proof. "
             "Forward this to ten friends."},
    {"id": "n6", "batch": 2, "publisher": "P2", "truth": "FAKE",
     "title": "Water supply poisoned",
     "text": "Unbelievable! The entire city water supply is poisoned and officials cover it up. "
             "Share now!"},
    {"id": "n7", "batch": 2, "publisher": "P1", "truth": "FAKE",
     "title": "Mayor to resign tonight",
     "text": "Sources say the mayor will resign tonight and the council will vote on a "
             "replacement, a source close to the matter reported."},
]
BY_ID = {n["id"]: n for n in NEWS}
