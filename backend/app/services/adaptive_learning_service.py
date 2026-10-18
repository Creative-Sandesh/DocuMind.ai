"""Evidence-gated topic assessment and quiz difficulty adjustments."""

DIFFICULTIES = ("beginner", "intermediate", "advanced")


def assess_topic(profile: dict) -> dict:
    """Classify objective answer history without treating provisional feedback as a score."""
    if profile["evidence"] != "supported":
        return {"status": "insufficient_evidence", "status_reason":
                "Complete at least two attempts and five scored objective answers before identifying a weak topic."}
    mastery = profile["mastery_percent"]
    recent = profile["recent_accuracy_percent"]
    if mastery is not None and mastery < 60:
        return {"status": "weak", "status_reason": f"Mastery is {mastery}%, below the 60% practice threshold."}
    if recent is not None and recent < 50 and profile["incorrect_answers"] >= 2:
        return {"status": "weak", "status_reason":
                f"Recent accuracy is {recent}% with at least two incorrect answers."}
    if mastery is not None and mastery >= 80 and recent is not None and recent >= 80:
        return {"status": "strong", "status_reason": "Mastery and recent accuracy are both at least 80%."}
    return {"status": "developing", "status_reason": "Performance is mixed; keep practicing at the current level."}


def recommend_difficulty(status: str, current: str) -> dict:
    """Move at most one level; sparse evidence and mixed results keep the chosen level."""
    index = DIFFICULTIES.index(current)
    if status == "weak":
        target = DIFFICULTIES[max(0, index - 1)]
        reason = "Supported weak-topic evidence suggests one easier level."
    elif status == "strong":
        target = DIFFICULTIES[min(len(DIFFICULTIES) - 1, index + 1)]
        reason = "Supported strong performance suggests one harder level."
    elif status == "developing":
        target = current
        reason = "Mixed performance keeps the selected level."
    else:
        target = current
        reason = "More scored answers are needed; the selected level is unchanged."
    return {"selected_difficulty": current, "effective_difficulty": target, "reason": reason}
