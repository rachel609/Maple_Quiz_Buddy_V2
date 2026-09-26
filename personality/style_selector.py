"""
Style Selector - Onboarding module for user interaction preferences.

Purpose: Collect the user's preferred interaction style and language.
Inputs: User input via CLI or MCP tool call.
Outputs: A dict with keys 'style' (str) and 'language' (str).
Dependencies: None (standalone module).
"""

STYLES = {
    "1": "Funny Buddy",
    "2": "Strict Teacher",
    "3": "Warm Encourager",
    "4": "Drill Sergeant",
}

LANGUAGES = {
    "1": "English",
    "2": "Chinese",
    "3": "French",
    "4": "Korean",
}

STYLE_DESCRIPTIONS = {
    "Funny Buddy": "Humorous and playful. Over-the-top praise when correct, funny comfort when wrong.",
    "Strict Teacher": "Precise and no-nonsense. Short feedback, straight to the point.",
    "Warm Encourager": "Gentle and supportive. Like a friend cheering you on.",
    "Drill Sergeant": "High-pressure motivator. Pushes you to do better, no excuses.",
}

VALID_STYLE_NAMES = set(STYLES.values())


def validate_style(style: str) -> str:
    """Validate and return a style name. Accepts number keys or full names."""
    if style in STYLES:
        return STYLES[style]
    if style in VALID_STYLE_NAMES:
        return style
    raise ValueError(f"Unknown style '{style}'. Choose from: {', '.join(VALID_STYLE_NAMES)}")


def validate_language(language: str) -> str:
    """Validate and return a language name. Accepts number keys or full names."""
    if language in LANGUAGES:
        return LANGUAGES[language]
    if language.strip():
        return language.strip()
    raise ValueError("Language cannot be empty.")


def run_onboarding() -> dict:
    """Run the full CLI onboarding flow. Returns {'style': str, 'language': str}."""
    print("\n========================================")
    print("   Welcome to Maple Quiz Buddy V2!")
    print("   Canadian Citizenship Test Prep")
    print("========================================\n")
    print("Pick your quiz buddy style:\n")

    for key, name in STYLES.items():
        print(f"  {key}. {name} -- {STYLE_DESCRIPTIONS[name]}")

    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        if choice in STYLES:
            style = STYLES[choice]
            print(f"\n-> You picked: {style}")
            break
        print("Invalid choice. Please enter a number between 1 and 4.")

    print("\nChoose the language for feedback and encouragement:")
    print("(Quiz questions are always in English)\n")
    for key, name in LANGUAGES.items():
        print(f"  {key}. {name}")
    print("  5. Other (type your own)")

    while True:
        choice = input("\nEnter your choice (1-5): ").strip()
        if choice in LANGUAGES:
            language = LANGUAGES[choice]
            break
        if choice == "5":
            custom = input("Type your preferred language: ").strip()
            if custom:
                language = custom
                break
            print("Language cannot be empty. Try again.")
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")

    print(f"\n-> Feedback language: {language}")
    print(f"\nStarting quiz with {style} style in {language}.\n")
    return {"style": style, "language": language}


if __name__ == "__main__":
    result = run_onboarding()
    print(f"Onboarding result: {result}")
