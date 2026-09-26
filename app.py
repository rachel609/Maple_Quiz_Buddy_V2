"""
Maple Quiz Buddy V2 - Main CLI Entry Point

Purpose: Run the quiz flow via LangGraph state machine from the command line.
         For MCP usage, run mcp_server/server.py instead.
Inputs: User interaction via CLI.
Outputs: Quiz results, feedback, score history.
Dependencies: All project modules, LangGraph.
"""
import sys
import config
from personality.style_selector import run_onboarding
from personality.buddy_prompts import generate_system_prompt
from rag.vector_store import load_vector_store
from quiz.question_generator import generate_questions
from quiz.grader import grade_quiz, clear_wrong_answers
from quiz.review_manager import run_review_session, has_wrong_answers, get_wrong_count
from memory.score_tracker import save_score, get_progress_summary, get_attempt_count, get_analytics


def run_quick_compare():
    """Quick test: generate questions and auto-answer in sandbox mode."""
    print("[Quick Test Mode - Sandbox]\n")

    load_vector_store()
    questions = generate_questions(5)
    print(f"Generated {len(questions)} questions:\n")

    for i, q in enumerate(questions, 1):
        print(f"  Q{i}: {q['question']}")
        print(f"      Answer: {q['answer']}) {q['options'][q['answer']]}")

    answers = [q["answer"] for q in questions]
    answers[0] = "A" if answers[0] != "A" else "B"

    result = grade_quiz(questions, answers)
    save_score(result["score"], result["total"])

    print(f"\nScore: {result['score']}/{result['total']} ({result['percentage']*100:.0f}%)")
    print(f"Passed: {result['passed']}")
    print(f"\nAnalytics: {get_analytics()}")
    print("\nQuick test passed!")


def main():
    """Main CLI application entry point."""
    if "--test" in sys.argv:
        run_quick_compare()
        return

    if "--mcp" in sys.argv:
        print("Starting MCP server...")
        import asyncio
        from mcp_server.server import main as mcp_main
        asyncio.run(mcp_main())
        return

    # Step 1: Onboarding
    preferences = run_onboarding()
    style = preferences["style"]
    language = preferences["language"]
    system_prompt = generate_system_prompt(style, language)

    # Step 2: Initialize RAG
    if config.is_sandbox():
        print("[Sandbox Mode] Using mock data.\n")
    print("Preparing study materials...")
    load_vector_store()
    print("Ready!\n")

    clear_wrong_answers()

    # Step 3: Quiz loop
    while True:
        if get_attempt_count() >= config.MAX_ATTEMPTS:
            print(f"\nMaximum {config.MAX_ATTEMPTS} attempts reached.")
            break

        attempt = get_attempt_count() + 1
        print(f"\n{'='*50}")
        print(f"  QUIZ ATTEMPT #{attempt}")
        print(f"  {config.QUESTIONS_PER_QUIZ} questions -- 75% to pass")
        print(f"{'='*50}\n")

        questions = generate_questions(
            num_questions=config.QUESTIONS_PER_QUIZ,
            system_prompt=system_prompt,
        )
        if not questions:
            print("Error: Could not generate questions.")
            break

        user_answers = []
        for i, q in enumerate(questions, 1):
            print(f"\nQuestion {i}/{len(questions)}: {q['question']}")
            for letter, text in q["options"].items():
                print(f"  {letter}) {text}")

            while True:
                answer = input("\nYour answer (A/B/C/D): ").strip().upper()
                if answer in ("A", "B", "C", "D"):
                    break
                print("Please enter A, B, C, or D.")

            user_answers.append(answer)

            is_correct = answer == q["answer"]
            if is_correct:
                print("-> Correct!")
            else:
                print(f"-> Wrong. Correct answer: {q['answer']}) {q['options'][q['answer']]}")

        result = grade_quiz(questions, user_answers)
        save_score(result["score"], result["total"])

        pct = result["percentage"] * 100
        print(f"\n{'='*50}")
        if result["passed"]:
            print(f"  PASSED! Score: {result['score']}/{result['total']} ({pct:.0f}%)")
        else:
            print(f"  NOT PASSED. Score: {result['score']}/{result['total']} ({pct:.0f}%)")
        print(f"{'='*50}")

        if has_wrong_answers():
            answer = input(f"\nYou got {get_wrong_count()} wrong. Review them? (y/n): ").strip().lower()
            if answer in ("y", "yes"):
                run_review_session()

        answer = input("\nTake another quiz? (y/n): ").strip().lower()
        if answer not in ("y", "yes"):
            break
        clear_wrong_answers()

    print(get_progress_summary())
    print("Thank you for using Maple Quiz Buddy V2! Good luck on your citizenship test!\n")


if __name__ == "__main__":
    main()
