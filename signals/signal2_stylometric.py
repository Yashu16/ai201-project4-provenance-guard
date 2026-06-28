import re
import math


def get_stylometric_score(text: str) -> float:
    """
    Analyzes structural/stylometric patterns to detect AI-generated text.
    Returns a float 0.0-1.0: 1.0 = highly likely AI, 0.0 = highly likely human.

    Features (weighted):
    - Sentence length variance  (50%) — strongest signal: AI is uniform, humans are chaotic
    - Formal phrase patterns    (30%) — AI cliché openers and transitions
    - Punctuation density       (20%) — AI uses commas/semicolons heavily
    """
    sentences = _split_sentences(text)
    if len(sentences) < 2:
        return 0.5

    # --- Feature 1: Sentence length variance (weight 0.50) ---
    lengths = [len(s.split()) for s in sentences]
    mean_len = sum(lengths) / len(lengths)
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    # AI texts typically have std_dev 2-5, human texts 6-15+
    # std_dev=2 -> ~0.75, std_dev=6+ -> ~0.0
    uniformity_score = max(0.0, min(1.0, 1.0 - (std_dev / 8.0)))

    # --- Feature 2: Formal AI phrase patterns (weight 0.30) ---
    # These are high-precision markers — humans rarely write like this
    ai_phrases = [
        r'\bit is important to note\b',
        r'\bit is worth noting\b',
        r'\bfurthermore\b',
        r'\bmoreover\b',
        r'\bin conclusion\b',
        r'\bin summary\b',
        r'\bit is essential to\b',
        r'\bvarious (sectors|stakeholders|aspects|factors)\b',
        r'\bensure (responsible|effective|proper)\b',
        r'\bparadigm shift\b',
        r'\bit is equally\b',
        r'\bnot only .{0,40} but also\b',
        r'\bwhen it comes to\b',
        r'\bplays a (crucial|vital|key|important) role\b',
    ]
    text_lower = text.lower()
    hits = sum(1 for p in ai_phrases if re.search(p, text_lower))
    # 2+ hits = very likely AI, normalize against phrase list length
    phrase_score = min(1.0, hits / 2.0)

    # --- Feature 3: Punctuation density (weight 0.20) ---
    words = text.split()
    if words:
        punct_count = sum(1 for ch in text if ch in ",:;")
        punct_density = punct_count / len(words)
        # AI tends toward 0.15-0.30 commas/semicolons per word
        # Normalize: 0.20+ is AI-like
        punct_score = max(0.0, min(1.0, punct_density / 0.20))
    else:
        punct_score = 0.5

    combined = (0.35 * uniformity_score) + (0.45 * phrase_score) + (0.20 * punct_score)
    return round(combined, 4)


def _split_sentences(text: str) -> list:
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p for p in parts if p]


if __name__ == "__main__":
    samples = [
        ("1. Clearly AI",
         "Artificial intelligence represents a transformative paradigm shift in modern society. "
         "It is important to note that while the benefits of AI are numerous, it is equally "
         "essential to consider the ethical implications. Furthermore, stakeholders across "
         "various sectors must collaborate to ensure responsible deployment."),
        ("2. Clearly human",
         "ok so i finally tried that new ramen place downtown and honestly? "
         "underwhelming. the broth was fine but they put WAY too much sodium in it and "
         "i was thirsty for like three hours after. my friend got the spicy version and "
         "said it was better. probably won't go back unless someone drags me there"),
        ("3. Formal human",
         "The relationship between monetary policy and asset price inflation has been "
         "extensively studied in the literature. Central banks face a fundamental tension "
         "between their mandate for price stability and the unintended consequences of "
         "prolonged low interest rates on equity and real estate valuations."),
        ("4. Lightly edited AI",
         "I've been thinking a lot about remote work lately. There are genuine tradeoffs — "
         "flexibility and no commute on one side, isolation and blurred work-life boundaries "
         "on the other. Studies show productivity varies widely by individual and role type."),
    ]
    for label, text in samples:
        score = get_stylometric_score(text)
        print(f"[{label}] score={score:.3f}")
