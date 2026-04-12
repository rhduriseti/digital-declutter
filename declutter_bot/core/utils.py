# ---------------------------------------------------------
# SEED MAP — subject → keywords
# Your daughter will own and expand this!
# ---------------------------------------------------------

SEED_MAP = {
    "math": [
        "math", "algebra", "calculus", "calc", "geometry", "trigonometry",
        "trig", "statistics", "stats", "arithmetic", "equation", "polynomial",
        "derivative", "integral", "matrix", "linear", "quadratic"
    ],
    "biology": [
        "bio", "biology", "cell", "dna", "rna", "genetics", "evolution",
        "photosynthesis", "mitosis", "meiosis", "ecosystem", "organism",
        "anatomy", "physiology", "bacteria", "virus", "protein", "enzyme"
    ],
    "chemistry": [
        "chem", "chemistry", "element", "compound", "reaction", "molecule",
        "atom", "periodic", "acid", "base", "bond", "electron", "proton",
        "neutron", "stoichiometry", "mole", "solution", "titration"
    ],
    "physics": [
        "physics", "force", "motion", "velocity", "acceleration", "gravity",
        "energy", "momentum", "wave", "optics", "electricity", "magnetism",
        "thermodynamics", "quantum", "relativity", "newton", "friction"
    ],
    "english": [
        "english", "essay", "grammar", "literature", "poem", "poetry",
        "novel", "thesis", "shakespeare", "writing", "reading", "vocab",
        "vocabulary", "metaphor", "narrative", "rhetoric", "analysis",
        "summary", "paragraph", "argument"
    ],
    "history": [
        "history", "hist", "war", "revolution", "civilization", "ancient",
        "medieval", "colonial", "wwi", "wwii", "ww1", "ww2", "civil",
        "empire", "democracy", "constitution", "amendment", "timeline"
    ],
    "geography": [
        "geography", "geo", "map", "continent", "country", "climate",
        "biome", "latitude", "longitude", "population", "migration",
        "region", "topography", "river", "mountain", "ocean"
    ],
    "computer_science": [
        "cs", "code", "coding", "programming", "algorithm", "python",
        "java", "javascript", "html", "css", "database", "software",
        "hardware", "network", "binary", "function", "loop", "variable"
    ],
    "economics": [
        "econ", "economics", "supply", "demand", "market", "inflation",
        "gdp", "trade", "budget", "fiscal", "monetary", "microeconomics",
        "macroeconomics", "capitalism", "investment", "stock"
    ],
    "psychology": [
        "psych", "psychology", "behavior", "cognitive", "emotion",
        "memory", "learning", "perception", "personality", "disorder",
        "therapy", "freud", "experiment", "stimulus", "response"
    ],
    "spanish": [
        "spanish", "espanol", "vocab", "conjugation", "subjunctive",
        "hablar", "tener", "ser", "estar", "preterite", "imperfect"
    ],
    "french": [
        "french", "francais", "conjugaison", "grammaire", "parler",
        "etre", "avoir", "passe", "imparfait"
    ],
    "art": [
        "art", "drawing", "painting", "sketch", "design", "color",
        "composition", "perspective", "portrait", "sculpture", "artwork"
    ],
    "music": [
        "music", "theory", "note", "chord", "rhythm", "melody",
        "harmony", "tempo", "instrument", "sheet", "scale", "pitch"
    ],
    "pe": [
        "pe", "health", "fitness", "exercise", "nutrition", "muscle",
        "cardio", "sport", "workout", "physical"
    ],
}

# ---------------------------------------------------------
# KEYWORD_TO_SUBJECT — inverted lookup built from SEED_MAP
# Maps each keyword → its subject for fast O(1) lookup
# e.g. "dna" → "biology", "calc" → "math"
# ---------------------------------------------------------

KEYWORD_TO_SUBJECT: dict[str, str] = {
    keyword: subject
    for subject, keywords in SEED_MAP.items()
    for keyword in keywords
}

# ---------------------------------------------------------
# CATEGORY_MAP — file extension → broad file type
# ---------------------------------------------------------

CATEGORY_MAP = {
    # Documents
    ".txt": "documents",
    ".pdf": "documents",
    ".doc": "documents",
    ".docx": "documents",
    ".rtf": "documents",
    ".odt": "documents",
    ".ppt": "documents",
    ".pptx": "documents",
    ".xls": "documents",
    ".xlsx": "documents",
    ".csv": "documents",
    ".md": "documents",

    # Images
    ".jpg": "images",
    ".jpeg": "images",
    ".png": "images",
    ".gif": "images",
    ".bmp": "images",
    ".tiff": "images",
    ".svg": "images",
    ".heic": "images",

    # Videos
    ".mp4": "videos",
    ".mov": "videos",
    ".avi": "videos",
    ".mkv": "videos",
    ".wmv": "videos",
    ".flv": "videos",

    # Audio
    ".mp3": "audio",
    ".wav": "audio",
    ".aac": "audio",
    ".flac": "audio",
    ".m4a": "audio",
    ".ogg": "audio",

    # Code
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".java": "code",
    ".c": "code",
    ".cpp": "code",
    ".cs": "code",
    ".html": "code",
    ".css": "code",
    ".json": "code",
    ".xml": "code",
    ".yaml": "code",
    ".yml": "code",
    ".sh": "code",

    # Archives
    ".zip": "archives",
    ".rar": "archives",
    ".7zip": "archives",
    ".tar": "archives",
    ".gz": "archives",

    # Apps / executables
    ".exe": "applications",
    ".dmg": "applications",
    ".pkg": "applications",
    ".app": "applications",

    # Design files
    ".psd": "design",
    ".ai": "design",
    ".sketch": "design",
    ".fig": "design",

    # Misc
    ".iso": "disk_images",
    ".db": "databases",
}
