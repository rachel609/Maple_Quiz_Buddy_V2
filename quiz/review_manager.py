"""
Review Manager - Wrong answer review and reshuffled re-quiz.

Purpose: Let users review wrong answers and retry them.
Inputs: Wrong answers from grader.
Outputs: Review session results.
Dependencies: config, quiz.grader.
"""
import random
from quiz.grader import load_wrong_answers, clear_wrong_answers


def get_review_questions() -> list:
    """Get wrong answers formatted as review questions, shuffled."""
    wrong = load_wrong_answers()
    if not wrong:
        return []

    questions = []
    for w in wrong:
        q = {
            "question": w["question"],
            "options": {},
            "answer": w["correct_answer"],
            "source_text": w.get("source_text", ""),
            "topic": w.get("topic", ""),
        }
        questions.append(q)

    random.shuffle(questions)
    return questions


def has_wrong_answers() -> bool:
    """Check if there are any wrong answers to review."""
    return len(load_wrong_answers()) > 0


def get_wrong_count() -> int:
    """Get the number of wrong answers."""
    return len(load_wrong_answers())


def run_review_session() -> dict:
    """
    Run a CLI review session for wrong answers.
    Returns {'reviewed': int, 'corrected': int, 'still_wrong': list}.
    """
    wrong = load_wrong_answers()
    if not wrong:
        return {"reviewed": 0, "corrected": 0, "still_wrong": []}

    random.shuffle(wrong)
    corrected = 0
    still_wrong = []

    print(f"\n--- Review Mode: {len(wrong)} question(s) ---\n")

    for i, w in enumerate(wrong, 1):
        print(f"Review {i}/{len(wrong)}: {w['question']}")
        print(f"  Correct answer: {w['correct_answer']}) {w['correct_text']}")
        if w.get("source_text"):
            print(f"  Source: {w['source_text'][:150]}...")

        answer = input("\nType the correct letter to confirm (A/B/C/D): ").strip().upper()
        if answer == w["correct_answer"]:
            print("-> Correct!")
            corrected += 1
        else:
            print(f"-> Still wrong. Answer is {w['correct_answer']}.")
            still_wrong.append(w)
        print()

    clear_wrong_answers()
    if still_wrong:
        from quiz.grader import _save_wrong_answers
        _save_wrong_answers(still_wrong)

    return {"reviewed": len(wrong), "corrected": corrected, "still_wrong": still_wrong}


if __name__ == "__main__":
    print(f"Wrong answers to review: {get_wrong_count()}")
    if has_wrong_answers():
        result = run_review_session()
        print(f"Reviewed: {result['reviewed']}, Corrected: {result['corrected']}")
