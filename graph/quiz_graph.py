"""
Quiz Graph - LangGraph state machine for the quiz flow.

Purpose: Define the quiz flow as a LangGraph StateGraph with nodes for
         onboarding, question generation, answering, grading, and review.
Inputs: User preferences and answers via state dict.
Outputs: Quiz results, scores, review data.
Dependencies: langgraph, all quiz/rag/personality/memory modules.
"""
from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph, END

from personality.buddy_prompts import generate_system_prompt
from rag.vector_store import load_vector_store, search
from quiz.question_generator import generate_questions
from quiz.grader import grade_single, grade_quiz, clear_wrong_answers, load_wrong_answers
from memory.score_tracker import save_score, get_analytics


class QuizState(TypedDict, total=False):
    """State schema for the quiz graph."""
    # User preferences
    style: str
    language: str
    system_prompt: str

    # Quiz session
    topic: Optional[str]
    num_questions: int
    questions: list
    current_index: int
    user_answers: list
    current_question: Optional[dict]

    # Grading
    grade_result: Optional[dict]
    last_feedback: Optional[dict]

    # Flow control
    action: str
    error: Optional[str]


def onboard_node(state: QuizState) -> dict:
    """Set up the quiz session with user preferences."""
    style = state.get("style", "Warm Encourager")
    language = state.get("language", "English")
    system_prompt = generate_system_prompt(style, language)
    return {"system_prompt": system_prompt, "style": style, "language": language}


def load_pdf_node(state: QuizState) -> dict:
    """Initialize the RAG vector store."""
    try:
        load_vector_store()
        return {"error": None}
    except Exception as e:
        return {"error": f"Failed to load study material: {e}"}


def generate_quiz_node(state: QuizState) -> dict:
    """Generate quiz questions."""
    num = state.get("num_questions", 10)
    topic = state.get("topic")
    system_prompt = state.get("system_prompt", "")

    questions = generate_questions(
        num_questions=num,
        topic=topic,
        system_prompt=system_prompt,
    )

    if not questions:
        return {"error": "Could not generate questions.", "questions": []}

    return {
        "questions": questions,
        "current_index": 0,
        "user_answers": [],
        "current_question": questions[0] if questions else None,
        "error": None,
    }


def present_question_node(state: QuizState) -> dict:
    """Present the current question."""
    idx = state.get("current_index", 0)
    questions = state.get("questions", [])

    if idx >= len(questions):
        return {"current_question": None, "action": "grade_all"}

    return {"current_question": questions[idx]}


def answer_node(state: QuizState) -> dict:
    """Process the user's answer for the current question."""
    idx = state.get("current_index", 0)
    questions = state.get("questions", [])
    answers = state.get("user_answers", [])
    current_answer = state.get("action", "")

    if not current_answer or current_answer.upper() not in ("A", "B", "C", "D"):
        return {"error": "Invalid answer. Please provide A, B, C, or D."}

    question = questions[idx]
    feedback = grade_single(question, current_answer)

    new_answers = answers + [current_answer.upper()]
    new_idx = idx + 1

    return {
        "user_answers": new_answers,
        "current_index": new_idx,
        "last_feedback": feedback,
        "error": None,
    }


def grade_all_node(state: QuizState) -> dict:
    """Grade the complete quiz."""
    questions = state.get("questions", [])
    answers = state.get("user_answers", [])

    result = grade_quiz(questions, answers)
    save_score(result["score"], result["total"])

    return {"grade_result": result, "current_question": None}


def summary_node(state: QuizState) -> dict:
    """Generate the quiz summary."""
    result = state.get("grade_result", {})
    analytics = get_analytics()

    return {
        "grade_result": {
            **result,
            "analytics": analytics,
        }
    }


def review_node(state: QuizState) -> dict:
    """Prepare wrong answers for review."""
    wrong = load_wrong_answers()
    if not wrong:
        return {"questions": [], "action": "done"}

    review_questions = []
    for w in wrong:
        review_questions.append({
            "question": w["question"],
            "options": {},
            "answer": w["correct_answer"],
            "source_text": w.get("source_text", ""),
            "topic": w.get("topic", ""),
        })

    return {
        "questions": review_questions,
        "current_index": 0,
        "user_answers": [],
        "current_question": review_questions[0] if review_questions else None,
    }


def should_continue(state: QuizState) -> str:
    """Decide the next step after answering a question."""
    idx = state.get("current_index", 0)
    questions = state.get("questions", [])

    if idx >= len(questions):
        return "grade_all"
    return "present_question"


def should_review(state: QuizState) -> str:
    """Decide whether to review wrong answers."""
    action = state.get("action", "")
    if action == "review":
        return "review"
    return "end"


def build_quiz_graph() -> StateGraph:
    """Build and compile the quiz state graph."""
    graph = StateGraph(QuizState)

    graph.add_node("onboard", onboard_node)
    graph.add_node("load_pdf", load_pdf_node)
    graph.add_node("generate_quiz", generate_quiz_node)
    graph.add_node("present_question", present_question_node)
    graph.add_node("answer", answer_node)
    graph.add_node("grade_all", grade_all_node)
    graph.add_node("summary", summary_node)
    graph.add_node("review", review_node)

    graph.set_entry_point("onboard")
    graph.add_edge("onboard", "load_pdf")
    graph.add_edge("load_pdf", "generate_quiz")
    graph.add_edge("generate_quiz", "present_question")
    graph.add_edge("present_question", "answer")
    graph.add_conditional_edges("answer", should_continue)
    graph.add_edge("grade_all", "summary")
    graph.add_conditional_edges("summary", should_review, {"review": "review", "end": END})
    graph.add_edge("review", "present_question")

    return graph.compile()


if __name__ == "__main__":
    app = build_quiz_graph()
    result = app.invoke({
        "style": "Warm Encourager",
        "language": "English",
        "num_questions": 3,
        "action": "B",
    })
    print(f"Graph result keys: {list(result.keys())}")
    print(f"Questions generated: {len(result.get('questions', []))}")
