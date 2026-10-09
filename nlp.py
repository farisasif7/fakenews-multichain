"""
nlp.py - lightweight OFF-CHAIN NLP + reinforcement-style learner (no pip needed).

Mirrors the paper's feature groups: fake score, real score, sim_matched
(similarity to the backlog of previously confirmed fake news).

Learning ("reinforcement"): after the validators' verdict is written on-chain it
is used as the reward signal.  Correct prediction -> reward +1, no change.
Wrong prediction -> reward -1, word weights are pushed towards the true label.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_FILE = os.path.join(HERE, "nlp_weights.json")

# + = fake-leaning word, - = real-leaning word
SEED = {
    "shocking": 1, "miracle": 1, "secret": 1, "leaked": 1, "hoax": 1,
    "unbelievable": 1, "cure": 1, "exposed": 1, "conspiracy": 1, "banned": 1,
    "urgent": 1, "anonymous": 1, "forward": 1, "share": 1, "guaranteed": 1,
    "cover": 1, "breaking": 1,
    "according": -1, "officials": -1, "reported": -1, "ministry": -1,
    "study": -1, "published": -1, "statement": -1, "confirmed": -1,
    "data": -1, "percent": -1, "university": -1, "announced": -1,
    "report": -1, "spokesperson": -1, "statistics": -1,
}
STOP = set("the and for are was were that this with from have has had not but you your "
           "they them their will been its into out all can who how why what when".split())


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9']+", text.lower()) if len(t) > 2 and t not in STOP]


class Detector:
    def __init__(self, path=WEIGHTS_FILE):
        self.path = path
        self.w = dict(SEED)
        if os.path.exists(path):
            with open(path) as f:
                self.w = json.load(f)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.w, f, indent=1, sort_keys=True)

    def features(self, text, backlog=()):
        toks = tokens(text)
        fake = sum(self.w[t] for t in toks if self.w.get(t, 0) > 0)
        real = sum(-self.w[t] for t in toks if self.w.get(t, 0) < 0)
        # style cues: exclamation marks and SHOUTING words are typical of fake news
        fake += min(text.count("!"), 3) * 0.5
        fake += min(sum(1 for w in text.split() if len(w) > 3 and w.isupper()), 3) * 0.5
        sim = 0.0
        st = set(toks)
        for b in backlog:
            sb = set(tokens(b))
            if st and sb:
                sim = max(sim, len(st & sb) / float(len(st | sb)))
        return {"fake_score": round(fake, 2), "real_score": round(real, 2),
                "sim_matched": round(sim, 2)}

    def predict(self, text, backlog=()):
        f = self.features(text, backlog)
        margin = f["fake_score"] - f["real_score"] + 4 * f["sim_matched"]
        label = "FAKE" if margin > 0 else "REAL"
        return label, round(min(1.0, abs(margin) / 3.0), 2), f

    def feedback(self, text, true_label, backlog=(), lr=0.5):
        """Reward -1/+1.  Returns the reward received."""
        pred, _, _ = self.predict(text, backlog)
        if pred == true_label:
            return +1
        target = 1 if true_label == "FAKE" else -1
        for t in set(tokens(text)):
            self.w[t] = self.w.get(t, 0) + lr * target
        return -1
