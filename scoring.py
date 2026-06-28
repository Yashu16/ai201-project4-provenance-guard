SIGNAL1_WEIGHT = 0.40  # Groq LLM (semantic)
SIGNAL2_WEIGHT = 0.60  # Stylometric (structural)


def combine_scores(signal1_score: float, signal2_score: float) -> float:
    """
    Weighted average of both signals per spec:
    40% semantic (LLM), 60% stylometric (python script).
    Returns a float 0.0-1.0.
    """
    combined = (SIGNAL1_WEIGHT * signal1_score) + (SIGNAL2_WEIGHT * signal2_score)
    return round(combined, 4)


def get_verdict(confidence: float) -> tuple[str, str]:
    """
    Maps confidence score to (verdict, transparency_label) per uncertainty thresholds:
    [0.00 - 0.35] -> high_confidence_human
    [0.36 - 0.64] -> uncertain
    [0.65 - 1.00] -> high_confidence_ai
    """
    if confidence <= 0.35:
        return (
            "high_confidence_human",
            "Verified Human Creator: Our automated system has analyzed the content's "
            "structure, semantics and stylistics pattern and are highly confident that "
            "this was written entirely by a human."
        )
    elif confidence <= 0.64:
        return (
            "uncertain",
            "Uncertain Attribution: Our automated system has analyzed given text but is "
            "unable to confidently say that this is human-written due to mixed signals. "
            "We are improving our systems in this regard, thank you for your patience!"
        )
    else:
        return (
            "high_confidence_ai",
            "AI-generated Content: This uploaded text was analyzed by our system and we "
            "have detected AI written structure and semantics. If you are the creator and "
            "believe this classification is a mistake, you can submit your appeal and it "
            "will be reviewed by our moderators."
        )
