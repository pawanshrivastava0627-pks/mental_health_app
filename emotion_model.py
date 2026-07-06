# emotion_model.py
# Robust rule + VADER-based emotion detection for short user text
# Returns one of: "Very Happy", "Happy", "Neutral", "Sad"

import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

# Keyword lists for strong overrides (all lowercase)
VERY_HAPPY_KEYWORDS = {
    "ecstatic","over the moon","elated","thrilled","on cloud nine",
    "amazing","awesome","fantastic","great news","celebrate","won","victory"
}

HAPPY_KEYWORDS = {
    "happy","glad","cheerful","good","content","smile","smiling",
    "joy","positive","blessed","thankful","grateful","excited"
}

SAD_KEYWORDS = {
    "sad","depressed","lonely","broken","cry","crying","hurt","hurtful",
    "angry","mad","fight","fighting","argue","argued","upset","annoyed",
    "tired","exhausted","stressed","stress","pain","hopeless","down"
}

# Negative context words that can invert the meaning
NEGATION_WORDS = {"not", "no", "never", "none", "nobody", "nothing", 
                 "neither", "nowhere", "hardly", "scarcely", "barely",
                 "doesn't", "isn't", "wasn't", "shouldn't", "wouldn't",
                 "couldn't", "won't", "can't", "don't"}

# normalize text (remove extra spaces, common punctuation)
def _clean_text(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    # replace common punctuation with spaces
    t = re.sub(r"[^\w\s']", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _has_negation_context(text: str, keyword: str) -> bool:
    """
    Check if a keyword appears in a negative context.
    Looks for negation words before the keyword.
    """
    words = text.split()
    try:
        keyword_index = words.index(keyword)
        # Check 1-3 words before the keyword for negation
        for i in range(max(0, keyword_index-3), keyword_index):
            if i < len(words) and words[i] in NEGATION_WORDS:
                return True
    except ValueError:
        # Keyword not found as exact word (might be part of larger word)
        pass
    
    # Also check for common negation patterns
    negation_patterns = [
        f"not {keyword}",
        f"no {keyword}",
        f"never {keyword}",
        f"n't {keyword}"
    ]
    
    for pattern in negation_patterns:
        if pattern in text:
            return True
            
    return False

def detect_emotion(text: str) -> str:
    """
    Detects mood from text and returns one of:
    "Very Happy", "Happy", "Neutral", "Sad"
    Uses keyword overrides first (with negation checking), then VADER compound score.
    """
    if not text or not text.strip():
        return "Neutral"

    s = _clean_text(text)

    # 1) Check for explicit mixed/neutral phrases first
    mixed_neutral_phrases = {
        "but not happy", "but not sad", "but not angry", "but not excited",
        "not happy but", "not sad but", "not bad but", "not good but",
        "so so", "so-so", "meh", "average", "alright", "okay", "fine",
        "could be better", "could be worse"
    }
    
    for phrase in mixed_neutral_phrases:
        if phrase in s:
            return "Neutral"

    # 2) Strong keyword overrides (explicit phrases) with negation checking
    # Check multi-word phrases first
    for phrase in VERY_HAPPY_KEYWORDS:
        if phrase in s and not _has_negation_context(s, phrase):
            return "Very Happy"
    
    for phrase in HAPPY_KEYWORDS:
        if phrase in s and not _has_negation_context(s, phrase):
            return "Happy"
    
    for phrase in SAD_KEYWORDS:
        if phrase in s and not _has_negation_context(s, phrase):
            return "Sad"

    # 3) Special case: if text has both positive and negative elements, lean neutral
    vs = _analyzer.polarity_scores(s)
    comp = vs.get("compound", 0.0)
    
    # If there's significant positive AND negative sentiment, classify as Neutral
    if vs['pos'] > 0.2 and vs['neg'] > 0.2:
        return "Neutral"

    # 4) Fallback to VADER compound score with wider neutral range
    if comp >= 0.50:
        return "Very Happy"
    elif comp >= 0.20:
        return "Happy"
    elif comp <= -0.50:
        return "Sad"
    elif comp <= -0.30:
        return "Sad"
    else:
        return "Neutral"