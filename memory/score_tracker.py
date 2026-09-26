"""
Score Tracker - Multi-attempt score tracking and progress analysis.

Purpose: Save quiz scores, track progress across attempts, generate summaries.
Inputs: Score data per attempt.
Outputs: Score history, progress summaries, analytics.
Dependencies: config.
"""
import json
import os
from datetime import date, datetime
import config


def save_score(score: int, total: int) -> dict:
    """Save a quiz score to the log. Returns the saved entry."""
    history = get_score_history()
    attempt = len(history) + 1
    entry = {
        "attempt": attempt,
        "date": str(date.today()),
        "timestamp": datetime.now().isoformat(),
        "score": score,
        "total": total,
        "percentage": round(score / total, 4) if total > 0 else 0.0,
        "passed": (score / total) >= config.PASSING_SCORE if total > 0 else False,
    }
    history.append(entry)

    try:
        os.makedirs(os.path.dirname(config.SCORE_LOG_PATH), exist_ok=True)
        with open(config.SCORE_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Warning] Could not save score: {e}")

    return entry


def get_score_history() -> list:
    """Load all score entries from the log."""
    try:
        with open(config.SCORE_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def get_attempt_count() -> int:
    """Get the total number of quiz attempts."""
    return len(get_score_history())


def get_best_score() -> dict:
    """Get the best score entry. Returns empty dict if no history."""
    history = get_score_history()
    if not history:
        return {}
    return max(history, key=lambda x: x.get("percentage", 0))


def get_latest_score() -> dict:
    """Get the most recent score entry."""
    history = get_score_history()
    return history[-1] if history else {}


def get_analytics() -> dict:
    """Generate study analytics from score history."""
    history = get_score_history()
    if not history:
        return {
            "total_attempts": 0,
            "average_score": 0.0,
            "best_percentage": 0.0,
            "worst_percentage": 0.0,
            "pass_rate": 0.0,
            "trend": "no data",
            "improvement": 0.0,
        }

    percentages = [h["percentage"] for h in history]
    passes = sum(1 for h in history if h.get("passed", False))

    trend = "stable"
    if len(percentages) >= 2:
        if percentages[-1] > percentages[-2]:
            trend = "improving"
        elif percentages[-1] < percentages[-2]:
            trend = "declining"

    improvement = percentages[-1] - percentages[0] if len(percentages) >= 2 else 0.0

    return {
        "total_attempts": len(history),
        "average_score": round(sum(percentages) / len(percentages), 4),
        "best_percentage": max(percentages),
        "worst_percentage": min(percentages),
        "pass_rate": round(passes / len(history), 4),
        "trend": trend,
        "improvement": round(improvement, 4),
        "history": history,
    }


def predict_readiness() -> dict:
    """Predict exam readiness based on score history."""
    analytics = get_analytics()
    if analytics["total_attempts"] == 0:
        return {"ready": False, "confidence": 0.0, "message": "No quiz attempts yet. Take a quiz first!"}

    avg = analytics["average_score"]
    trend = analytics["trend"]
    best = analytics["best_percentage"]

    confidence = avg * 0.5 + best * 0.3
    if trend == "improving":
        confidence += 0.1
    elif trend == "declining":
        confidence -= 0.05

    confidence = min(max(confidence, 0.0), 1.0)
    ready = confidence >= 0.7

    if ready:
        message = f"You look ready! Confidence: {confidence*100:.0f}%. Average: {avg*100:.0f}%."
    elif confidence >= 0.5:
        message = f"Almost there! Confidence: {confidence*100:.0f}%. Keep practicing weak areas."
    else:
        message = f"Need more practice. Confidence: {confidence*100:.0f}%. Focus on fundamentals."

    return {"ready": ready, "confidence": round(confidence, 4), "message": message}


def get_progress_summary() -> str:
    """Generate a human-readable progress summary."""
    history = get_score_history()
    if not history:
        return "No quiz attempts yet."

    lines = ["\n--- Score History ---"]
    for h in history:
        pct = h["percentage"] * 100
        status = "PASS" if h.get("passed") else "FAIL"
        lines.append(f"  Attempt {h['attempt']}: {h['score']}/{h['total']} ({pct:.0f}%) [{status}] - {h['date']}")

    analytics = get_analytics()
    lines.append(f"\n  Average: {analytics['average_score']*100:.0f}%")
    lines.append(f"  Best: {analytics['best_percentage']*100:.0f}%")
    lines.append(f"  Trend: {analytics['trend']}")
    lines.append("-------------------\n")
    return "\n".join(lines)


def compare_attempts(attempt_a: int, attempt_b: int) -> dict:
    """Compare two quiz attempts."""
    history = get_score_history()
    a = next((h for h in history if h["attempt"] == attempt_a), None)
    b = next((h for h in history if h["attempt"] == attempt_b), None)

    if not a or not b:
        return {"error": f"Attempt {attempt_a if not a else attempt_b} not found."}

    return {
        "attempt_a": a,
        "attempt_b": b,
        "score_change": b["score"] - a["score"],
        "percentage_change": round(b["percentage"] - a["percentage"], 4),
        "improved": b["percentage"] > a["percentage"],
    }


if __name__ == "__main__":
    save_score(15, 20)
    save_score(17, 20)
    print(get_progress_summary())
    print(f"Analytics: {get_analytics()}")
    print(f"Readiness: {predict_readiness()}")
