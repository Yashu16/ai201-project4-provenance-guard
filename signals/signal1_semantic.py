import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not set in environment")
        _client = Groq(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are an AI-authorship detection expert. Analyze the provided text and return a single float score between 0.0 and 1.0.

Score meaning:
- 0.0 = almost certainly human-written
- 1.0 = almost certainly AI-generated

Look for these AI writing patterns:
- Overuse of transitional contrast phrases like "not only X, but Y" or "not just X — but also Y"
- Unnaturally consistent sentence rhythm and length
- Generic, hedged phrasing (e.g., "It is important to note", "In conclusion")
- Absence of personal voice, idiosyncratic word choice, or genuine emotional messiness
- Cliché structural patterns: problem → solution → conclusion

Respond with ONLY a JSON object in this exact format, nothing else:
{"score": 0.72}"""


def get_semantic_score(text: str) -> float:
    """
    Sends text to Groq and returns a float 0.0–1.0.
    1.0 = highly likely AI-written, 0.0 = highly likely human-written.
    Raises on API or parse errors so the caller can handle them.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        temperature=0.0,
        max_tokens=32,
    )

    raw = response.choices[0].message.content.strip()

    import json
    parsed = json.loads(raw)
    score = float(parsed["score"])

    if not (0.0 <= score <= 1.0):
        raise ValueError(f"Score out of range: {score}")

    return score


if __name__ == "__main__":
    # Quick manual test — run: python -m signals.signal1_semantic
    samples = [
        ("AI-like text",
         "It is important to note that artificial intelligence is not just transforming "
         "industries, but also reshaping the very fabric of human creativity. In conclusion, "
         "we must embrace these changes while remaining vigilant."),
        ("Human-like text",
         "idk man i just wrote this at 2am and it felt right. maybe the ending sucks "
         "but that's how i felt when i finished it. the dog in stanza 3 is real btw"),
    ]
    for label, text in samples:
        score = get_semantic_score(text)
        print(f"[{label}] score={score:.3f}")
