import re

_CONVERSATIONAL_RE = re.compile(
    r'^\s*('
    r'hi+|hello+|hey+|salam|salaam|assalam|assalamualaikum'
    r'|how are you|how r u|how do you do'
    r'|good morning|good afternoon|good evening|good night'
    r'|thanks?|thank you|shukriya|jazakallah'
    r'|ok|okay|got it|understood|sure|great|nice|cool'
    r'|bye|goodbye|take care|see you'
    r'|who are you|what are you|what can you do|what is qanoon'
    r'|help|can you help'
    r')\s*[!\?\.]*\s*$',
    re.IGNORECASE,
)


def is_conversational(question: str) -> bool:
    return bool(_CONVERSATIONAL_RE.match(question.strip()))