"""
Grader - Grade quiz answers and log wrong answers.

Purpose: Compare user answers against correct answers, track wrong ones.
Inputs: List of questions, list of user answers.
Outputs: Grade result dict with score, total, percentage, passed, wrong list.
Dependencies: config.
"""
import json
import os
from datetime import date
import config


def grade_quiz(questions: list, user_answers: list) -> dict:
    """
    Grade a set of answers against the question bank.
    Returns {'score': int, 'total': int, 'percentage': float, 'passed': bool, 'wrong': list}.
    """
    score = 0
    wrong = []

    for q, user_ans in zip(questions, user_answers):
        if user_ans.upper() == q["answer"].upper():
            score += 1
        else:
            wrong.append({
                "question": q["question"],
                "user_answer": user_ans,
                "correct_answer": q["answer"],
                "correct_text": q["options"].get(q["answer"], ""),
                "source_text": q.get("source_text", ""),
                "topic": q.get("topic", ""),
                "date": str(date.today()),
            })

    total = len(questions)
    percentage = score / total if total > 0 else 0.0

    _save_wrong_answers(wrong)

    return {
        "score": score,
        "total": total,
        "percentage": percentage,
        "passed": percentage >= config.PASSING_SCORE,
        "wrong": wrong,
    }


def grade_single(question: dict, user_answer: str) -> dict:
    """Grade a single question. Returns {'correct': bool, 'correct_answer': str, ...}."""
    correct = user_answer.upper() == question["answer"].upper()
    result = {
        "correct": correct,
        "correct_answer": question["answer"],
        "correct_text": question["options"].get(question["answer"], ""),
        "question": question["question"],
        "user_answer": user_answer.upper(),
    }
    if not correct:
        wrong_entry = {
            "question": question["question"],
            "user_answer": user_answer.upper(),
            "correct_answer": question["answer"],
            "correct_text": question["options"].get(question["answer"], ""),
            "source_text": question.get("source_text", ""),
            "topic": question.get("topic", ""),
            "date": str(date.today()),
        }
        _save_wrong_answers([wrong_entry])
    return result


def _save_wrong_answers(wrong_list: list) -> None:
    """Append wrong answers to the persistent log."""
    if not wrong_list:
        return
    existing = load_wrong_answers()
    existing.extend(wrong_list)
    try:
        os.makedirs(os.path.dirname(config.WRONG_ANSWERS_PATH), exist_ok=True)
        with open(config.WRONG_ANSWERS_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Warning] Could not save wrong answers: {e}")


def load_wrong_answers() -> list:
    """Load all wrong answers from the log."""
    try:
        with open(config.WRONG_ANSWERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def clear_wrong_answers() -> None:
    """Clear the wrong answers log."""
    try:
        with open(config.WRONG_ANSWERS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
    except Exception:
        pass


def get_wrong_by_topic() -> dict:
    """Group wrong answers by topic. Returns {topic: [wrong_entries]}."""
    wrong = load_wrong_answers()
    by_topic = {}
    for w in wrong:
        topic = w.get("topic", "Unknown")
        by_topic.setdefault(topic, []).append(w)
    return by_topic


if __name__ == "__main__":
    from quiz.question_generator import generate_questions
    questions = generate_questions(3)
    answers = [q["answer"] for q in questions]
    answers[0] = "X"
    result = grade_quiz(questions, answers)
    print(f"Score: {result['score']}/{result['total']} ({result['percentage']*100:.0f}%)")
    print(f"Passed: {result['passed']}, Wrong: {len(result['wrong'])}")
