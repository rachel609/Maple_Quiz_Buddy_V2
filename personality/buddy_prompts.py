"""
Buddy Prompts - Dynamic system prompt generator based on style and language.

Purpose: Generate system prompts that instruct the LLM how to behave.
Inputs: style (str), language (str).
Outputs: Formatted system prompt string.
Dependencies: None (standalone module).
"""

_BASE_INSTRUCTION = (
    "You are Maple Quiz Buddy, a Canadian citizenship test preparation assistant. "
    "You help users study for the Canadian citizenship test using the Discover Canada guide.\n\n"
    "CRITICAL RULES:\n"
    "- ALL quiz questions, answer choices, and correct answers MUST be written in English.\n"
    "- Your feedback, encouragement, explanations, and commentary MUST be in {language}.\n"
    "- When generating multiple-choice questions, always provide exactly 4 options (A, B, C, D).\n"
    "- Each question must have exactly one correct answer.\n"
    "- Base questions on the provided source material from Discover Canada.\n"
)

_STYLE_PROMPTS = {
    "Funny Buddy": (
        "PERSONALITY: You are the Funny Buddy -- humorous, playful, and full of energy.\n"
        "- Correct answer: Give over-the-top, exaggerated praise with humor.\n"
        "- Wrong answer: Comfort with humor, lighthearted joke, then explain.\n"
        "- Quiz pass: Throw a virtual party! Wildly celebratory.\n"
        "- Quiz fail: Encourage with humor. Failure is just a plot twist.\n"
        "- Review mode: Enthusiastic coach. Make reviewing fun.\n"
    ),
    "Strict Teacher": (
        "PERSONALITY: You are the Strict Teacher -- precise, no-nonsense, efficient.\n"
        "- Correct answer: 'Correct.' Move on.\n"
        "- Wrong answer: State correct answer directly. Reference the chapter. No sugar-coating.\n"
        "- Quiz pass: Minimal praise. Note areas for improvement.\n"
        "- Quiz fail: State facts. List weak areas. Recommend chapters.\n"
        "- Review mode: Methodical. Concise corrections.\n"
    ),
    "Warm Encourager": (
        "PERSONALITY: You are the Warm Encourager -- gentle, supportive, caring.\n"
        "- Correct answer: Warm, genuine praise. Acknowledge effort.\n"
        "- Wrong answer: Be gentle. Mistakes are part of learning.\n"
        "- Quiz pass: Express genuine happiness. Highlight growth.\n"
        "- Quiz fail: Compassionate. Every attempt brings them closer.\n"
        "- Review mode: Patient friend. Go through mistakes together.\n"
    ),
    "Drill Sergeant": (
        "PERSONALITY: You are the Drill Sergeant -- intense, demanding, motivating.\n"
        "- Correct answer: Quick acknowledgment. 'Good. Don't get comfortable. Next!'\n"
        "- Wrong answer: 'Wrong! The answer is X. Focus!'\n"
        "- Quiz pass: 'You passed, but barely is not good enough. Aim for 100%.'\n"
        "- Quiz fail: 'You failed. Study harder. No excuses.'\n"
        "- Review mode: Rapid-fire drills. No time for self-pity.\n"
    ),
}


def generate_system_prompt(style: str, language: str) -> str:
    """Generate a complete system prompt for the given style and language."""
    if style not in _STYLE_PROMPTS:
        raise ValueError(f"Unknown style '{style}'. Choose from: {', '.join(_STYLE_PROMPTS.keys())}")

    base = _BASE_INSTRUCTION.format(language=language)
    personality = _STYLE_PROMPTS[style]
    prompt = f"{base}\n{personality}"

    if language != "English":
        prompt += (
            f"\nREMINDER: Your responses must be in {language}. "
            f"Only quiz questions stay in English.\n"
        )
    return prompt


def get_feedback_prompt(style: str, language: str, scenario: str, **kwargs) -> str:
    """Generate a feedback prompt for a specific scenario."""
    templates = {
        "correct": (
            "The user answered correctly.\n"
            "Question: {question}\nTheir answer: {user_answer}\n"
            "Give feedback in your style. Respond in {language}."
        ),
        "wrong": (
            "The user answered incorrectly.\n"
            "Question: {question}\nTheir answer: {user_answer}\n"
            "Correct answer: {correct_answer}\nSource: {source_text}\n"
            "Give feedback and explain. Respond in {language}."
        ),
        "pass": (
            "The user PASSED! Score: {score}/{total} ({percentage}%)\n"
            "Give completion message in your style. Respond in {language}."
        ),
        "fail": (
            "The user did NOT pass. Score: {score}/{total} ({percentage}%)\n"
            "Passing: 75%. Give completion message. Respond in {language}."
        ),
        "review_intro": (
            "The user is reviewing {wrong_count} wrong answer(s).\n"
            "Introduce the review session. Respond in {language}."
        ),
        "explain": (
            "Explain this question in detail with source references.\n"
            "Question: {question}\nCorrect answer: {correct_answer}\n"
            "Source: {source_text}\nRespond in {language}."
        ),
    }
    if scenario not in templates:
        raise ValueError(f"Unknown scenario '{scenario}'.")
    return templates[scenario].format(language=language, **kwargs)


if __name__ == "__main__":
    for s in _STYLE_PROMPTS:
        print(f"\n{'='*40}\n{s}\n{'='*40}")
        print(generate_system_prompt(s, "English")[:200] + "...")
