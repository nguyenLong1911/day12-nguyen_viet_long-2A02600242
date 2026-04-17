"""Mock LLM for offline lab execution."""
import random
import time


MOCK_RESPONSES = {
    "default": [
        "Day 12 production agent is running with mock LLM.",
        "Request received and processed successfully in lab mode.",
        "This is a mock response for deployment practice.",
    ],
    "deploy": ["Deployment publishes your service for public access."],
    "docker": ["Docker packages app and dependencies in one reproducible image."],
    "redis": ["Redis enables shared state across scaled stateless instances."],
}


def ask(question: str, delay: float = 0.1) -> str:
    time.sleep(delay)
    text = question.lower()
    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in text:
            return random.choice(responses)
    return random.choice(MOCK_RESPONSES["default"])
