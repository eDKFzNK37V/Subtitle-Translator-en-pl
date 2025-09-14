import language_tool_python
import re

# Extended glossary for subtitle translation with enhanced conversational patterns
ENHANCED_GLOSSARY = {
    # Common terms
    "White Hearts": "Białe Serca",
    "savior": "zbawiciel", 
    "Hero": "Bohater",
    "leader": "przywódca",
    "raid": "nalot",
    
    # Gaming/RPG terms
    "guild": "gildia",
    "quest": "zadanie",
    "dungeon": "loch",
    "boss": "boss",
    "level up": "awansować",
    "character": "postać",
    "player": "gracz",
    "item": "przedmiot",
    "weapon": "broń",
    "armor": "zbroja",
    "spell": "zaklęcie",
    "magic": "magia",
    "health": "zdrowie",
    "mana": "mana",
    "experience": "doświadczenie",
    
    # Enhanced dialogue expressions for natural flow
    "you know": "wiesz",
    "I mean": "to znaczy",
    "by the way": "a propos",
    "come on": "no dalej",
    "let's go": "chodźmy",
    "wait up": "czekaj",
    "hold on": "poczekaj",
    "never mind": "nieważne",
    "no way": "nie ma mowy",
    "for real": "na serio",
    "oh my god": "o mój Boże",
    "what the hell": "co do diabła",
    "damn it": "cholera",
    "seriously": "serio",
    "honestly": "szczerze",
    "obviously": "oczywiście",
    "actually": "właściwie",
    "basically": "w sumie",
    "definitely": "na pewno",
    "probably": "pewnie",
    "maybe": "może",
    "whatever": "nieważne",
    "anyway": "w każdym razie",
    "somehow": "jakoś",
    "somewhere": "gdzieś",
    "everything": "wszystko",
    "nothing": "nic",
    "something": "coś",
    "anything": "cokolwiek",
    
    # Common conversational transitions
    "listen": "słuchaj",
    "look": "słuchaj",
    "hey": "hej",
    "well": "no",
    "so": "więc",
    "okay": "dobrze",
    "right": "tak",
    "sure": "jasne",
    "fine": "dobrze",
    "great": "świetnie",
    "perfect": "idealnie",
    "exactly": "dokładnie",
    "absolutely": "absolutnie",
    "totally": "całkowicie",
    "completely": "zupełnie",
    
    # Formal/business terms
    "meeting": "spotkanie",
    "presentation": "prezentacja",
    "project": "projekt",
    "deadline": "termin",
    "budget": "budżet",
    "client": "klient",
    "customer": "klient",
    "manager": "menadżer",
    "team": "zespół",
    "department": "dział",
    
    # Technology terms
    "computer": "komputer",
    "software": "oprogramowanie",
    "hardware": "sprzęt",
    "internet": "internet",
    "website": "strona internetowa",
    "database": "baza danych",
    "server": "serwer",
    "network": "sieć",
    "system": "system",
    "application": "aplikacja",
    
    # Enhanced phrases for natural flow with improved patterns
    "I don't know": "nie wiem",
    "I think": "myślę",
    "I believe": "wierzę",
    "I'm sure": "jestem pewny",
    "of course": "oczywiście",
    "absolutely": "absolutnie",
    "definitely": "zdecydowanie",
    "probably": "prawdopodobnie",
    "maybe": "może",
    "perhaps": "być może",
    
    # Common problematic formal constructions to natural equivalents
    "I would like to inform you": "powiem ci",
    "I need to tell you that": "słuchaj",
    "I want you to know": "musisz wiedzieć",
    "I have to say that": "powiem ci",
    "Let me tell you": "słuchaj",
    "I should mention": "powinienem powiedzieć",
    "It's important to note": "ważne że",
    "I'd like to point out": "chcę pokazać",
    "Allow me to explain": "wyjaśnię",
    "I need to clarify": "wyjaśnię",
    
    # Reverse mapping for English → Polish problematic patterns
    "chciałbym powiedzieć": "powiem",
    "muszę przyznać": "przyznaję",
    "wydaje mi się": "myślę",
    "obawiam się": "niestety",
    "w związku z tym": "dlatego",
    "w rezultacie": "przez to",
    "w konsekwencji": "więc",
    "na pewno": "pewnie",
    "prawdopodobnie": "pewnie",
    "zupełnie nie": "wcale nie",
    "bardzo dziękuję": "dzięki",
    "jestem wdzięczny": "dzięki",
    "byłbym wdzięczny": "byłoby miło",
}

# Context-sensitive glossary rules
CONTEXT_GLOSSARY = {
    # Different translations based on context
    "game": {
        "gaming": "gra",
        "sports": "mecz", 
        "default": "gra"
    },
    "play": {
        "gaming": "grać",
        "sports": "grać",
        "theater": "grać",
        "music": "grać",
        "default": "grać"
    },
    "level": {
        "gaming": "poziom", 
        "education": "poziom",
        "building": "piętro",
        "default": "poziom"
    }
}

# DIACRITIC_DICT = {}
# with open(r"components/polish_words_with_specials.txt", encoding="utf-8") as f:
#     for line in f:
#         word = line.strip()
#         if word:
#             DIACRITIC_DICT[word.lower()] = word

tool_pl = language_tool_python.LanguageTool('pl-PL')
tool_en = language_tool_python.LanguageTool('en-US')

def get_context_from_text(text: str) -> str:
    """
    Determine context from text content for context-sensitive glossary.
    """
    text_lower = text.lower()
    
    # Gaming context
    gaming_keywords = ["game", "play", "player", "level", "boss", "quest", "guild", "character"]
    if any(keyword in text_lower for keyword in gaming_keywords):
        return "gaming"
    
    # Sports context  
    sports_keywords = ["team", "match", "score", "win", "lose", "championship", "tournament"]
    if any(keyword in text_lower for keyword in sports_keywords):
        return "sports"
        
    # Business context
    business_keywords = ["meeting", "client", "project", "deadline", "budget", "presentation"]
    if any(keyword in text_lower for keyword in business_keywords):
        return "business"
        
    # Technology context
    tech_keywords = ["computer", "software", "internet", "database", "server", "system"]
    if any(keyword in text_lower for keyword in tech_keywords):
        return "technology"
    
    return "default"

def apply_context_sensitive_glossary(text: str, context: str = "") -> str:
    """
    Apply context-sensitive glossary translations.
    """
    if context is None:
        context = get_context_from_text(text)
    
    result = text
    for term, contexts in CONTEXT_GLOSSARY.items():
        if context in contexts:
            translation = contexts[context]
        else:
            translation = contexts.get("default", term)
        
        # Apply translation with word boundaries
        pattern = rf"\b{re.escape(term)}\b"
        result = re.sub(pattern, translation, result, flags=re.IGNORECASE)
    
    return result