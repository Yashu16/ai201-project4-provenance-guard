from signals.signal1_semantic import get_semantic_score
from signals.signal2_stylometric import get_stylometric_score

samples = [
    ("AI-like text",
     "The relationship between memory and identity is one that has fascinated "
     "philosophers for centuries. While we often assume that our memories define "
     "who we are, the reality is far more nuanced. Each recollection is not a "
     "perfect recording but a reconstruction, shaped by our emotions, biases, "
     "and the passage of time. Understanding this distinction is crucial if we "
     "are to develop a more honest relationship with our own past."),

    ("Human-like text",
     "idk man i just wrote this at 2am and it felt right. maybe the ending sucks "
     "but that's how i felt when i finished it. the dog in stanza 3 is real btw"),
]

print(f"{'Sample':<20} {'Signal1 (LLM)':<16} {'Signal2 (Style)':<18} {'Agree?'}")
print("-" * 65)

for label, text in samples:
    s1 = get_semantic_score(text)
    s2 = get_stylometric_score(text)
    agree = "YES" if (s1 > 0.5) == (s2 > 0.5) else "NO — diverge"
    print(f"{label:<20} {s1:<16.3f} {s2:<18.3f} {agree}")
