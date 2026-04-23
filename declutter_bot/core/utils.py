# ---------------------------------------------------------
# SEED MAP — subject → keywords
# Rules: each keyword appears in at most one subject.
# Your daughter will own and expand this!
# ---------------------------------------------------------

SEED_MAP = {
    "math": [
        "math", "mathematics", "algebra", "calculus", "calc", "geometry",
        "trigonometry", "trig", "statistics", "stats", "arithmetic",
        "equation", "polynomial", "derivative", "integral", "matrix",
        "quadratic", "logarithm", "probability", "theorem", "proof",
        "fraction", "decimal", "graphing", "slope", "coordinate",
        "inequality", "coefficient", "exponent", "factoring", "parabola",
    ],
    "biology": [
        "biology", "bio", "cell", "dna", "rna", "genetics", "evolution",
        "photosynthesis", "mitosis", "meiosis", "ecosystem", "organism",
        "anatomy", "physiology", "bacteria", "virus", "protein", "enzyme",
        "chromosome", "gene", "mutation", "species", "taxonomy",
        "respiration", "osmosis", "diffusion", "nucleus", "membrane",
        "chloroplast", "mitochondria", "ribosome", "natural selection",
    ],
    "chemistry": [
        "chemistry", "chem", "element", "compound", "reaction", "molecule",
        "atom", "periodic table", "acid", "base", "bond", "electron",
        "proton", "neutron", "stoichiometry", "mole", "solution",
        "titration", "oxidation", "reduction", "catalyst", "equilibrium",
        "enthalpy", "entropy", "covalent", "ionic", "valence", "isotope",
        "radioactive", "organic chemistry",
    ],
    "physics": [
        "physics", "force", "motion", "velocity", "acceleration", "gravity",
        "momentum", "wave", "optics", "electricity", "magnetism",
        "thermodynamics", "quantum", "relativity", "newton", "friction",
        "torque", "pressure", "density", "projectile", "circuit",
        "voltage", "current", "resistance", "electromagnetic", "nuclear",
    ],
    "english": [
        "english", "grammar", "shakespeare", "literary analysis",
        "figurative language", "metaphor", "simile", "alliteration",
        "symbolism", "characterization", "protagonist", "antagonist",
        "rhetoric", "syntax", "diction", "tone", "mood", "annotation",
        "close reading", "textual evidence", "literary device",
        "iambic pentameter", "sonnet", "hamlet", "macbeth", "othello",
        "thesis", "theme", "foreshadowing", "irony", "imagery",
    ],
    "history": [
        "history", "hist", "war", "revolution", "civilization", "ancient",
        "medieval", "colonial", "wwi", "wwii", "ww1", "ww2", "civil war",
        "empire", "constitution", "amendment", "timeline", "dynasty",
        "renaissance", "reformation", "enlightenment", "industrial revolution",
        "cold war", "holocaust", "slavery", "manifest destiny", "imperialism",
        "treaty", "declaration", "founding fathers", "monarchy", "feudalism",
        "crusades", "colonialism",
    ],
    "geography": [
        "geography", "geo", "map", "continent", "country",
        "biome", "latitude", "longitude", "population", "migration",
        "region", "topography", "river", "mountain", "ocean",
        "cartography", "hemisphere", "equator", "urban", "rural",
        "demographic", "peninsula", "island", "plateau", "delta",
        "tectonic", "monsoon", "savanna", "tundra", "rainforest",
    ],
    "computer_science": [
        "computer science", "cs", "coding", "programming", "algorithm",
        "python", "java", "javascript", "html", "css", "database",
        "software", "hardware", "network", "binary", "loop", "variable",
        "debugging", "recursion", "object oriented", "data structure",
        "array", "linked list", "sorting", "compiler", "boolean",
        "conditional", "iteration", "api", "git", "machine learning",
        "artificial intelligence", "cybersecurity",
    ],
    "economics": [
        "economics", "econ", "supply", "demand", "market", "inflation",
        "gdp", "trade", "budget", "fiscal", "monetary", "microeconomics",
        "macroeconomics", "capitalism", "investment", "stock", "scarcity",
        "opportunity cost", "elasticity", "subsidy", "tariff", "recession",
        "unemployment", "interest rate", "currency", "entrepreneur",
        "profit", "consumer", "producer",
    ],
    "psychology": [
        "psychology", "psych", "behavior", "cognitive", "emotion",
        "memory", "perception", "personality", "disorder", "therapy",
        "freud", "stimulus", "response", "conditioning", "reinforcement",
        "attachment", "neuroscience", "mental health", "depression",
        "anxiety", "motivation", "consciousness", "conformity",
        "obedience", "milgram", "pavlov",
    ],
    "spanish": [
        "spanish", "espanol", "hablar", "tener", "ser", "estar",
        "preterite", "imperfect", "subjunctive", "conjugation",
        "reflexive verb", "vocabulario", "gramatica", "lectura",
        "hispanohablante", "presente", "futuro", "condicional",
    ],
    "french": [
        "french", "francais", "parler", "etre", "avoir",
        "passe compose", "imparfait", "subjonctif", "conjugaison",
        "grammaire", "vocabulaire", "francophone", "present",
        "futur", "conditionnel", "imperatif",
    ],
    "art": [
        "art", "drawing", "painting", "sketch", "color theory",
        "composition", "perspective", "portrait", "sculpture", "artwork",
        "watercolor", "acrylic", "charcoal", "shading", "texture",
        "art history", "impressionism", "abstract", "digital art",
        "printmaking", "ceramics", "collage", "still life",
    ],
    "music": [
        "music", "music theory", "chord", "rhythm", "melody",
        "harmony", "tempo", "instrument", "sheet music", "scale",
        "pitch", "treble clef", "bass clef", "time signature",
        "dynamics", "notation", "symphony", "orchestra", "ensemble",
        "rehearsal", "sonata", "opus", "audition",
    ],
    "pe": [
        "pe", "physical education", "fitness", "exercise", "nutrition",
        "muscle", "cardio", "sport", "workout", "wellness",
        "flexibility", "endurance", "heart rate", "calories",
        "hydration", "stretching", "athletic", "olympic",
    ],
    "science": [
        "science", "sci", "experiment", "lab report", "hypothesis",
        "observation", "scientific method", "investigation",
        "dependent variable", "independent variable", "control group",
        "measurement", "accuracy", "precision", "error analysis",
    ],
    "social_studies": [
        "social studies", "civics", "civic", "government", "society",
        "community", "culture", "citizenship", "policy", "justice",
        "human rights", "diversity", "global issues", "current events",
        "political", "election", "voting", "legislation",
        "executive branch", "judicial branch", "legislative branch",
        "bill of rights", "immigration", "poverty", "inequality", "activism",
    ],
    "environmental_science": [
        "environmental science", "environment", "climate change",
        "sustainability", "pollution", "carbon footprint", "fossil fuel",
        "renewable energy", "solar energy", "wind energy", "deforestation",
        "conservation", "habitat", "greenhouse gas", "biodiversity",
        "recycling", "emissions", "ozone", "acid rain", "water cycle",
        "carbon cycle", "ecological", "food web", "endangered species",
        "invasive species", "food desert",
    ],
    "writing": [
        "writing", "essay", "composition", "draft", "revision", "narrative",
        "persuasive", "argumentative", "expository", "descriptive",
        "speech", "debate", "journal", "creative writing", "story",
        "poem", "poetry", "screenplay", "dialogue", "outline",
        "introduction", "conclusion", "thesis statement", "body paragraph",
        "transition", "editing", "proofreading", "citation", "bibliography",
    ],
    "reading": [
        "reading", "read aloud", "comprehension", "book report",
        "chapter", "novel", "article", "nonfiction", "fiction",
        "fluency", "decoding", "phonics", "summarizing", "main idea",
        "supporting details", "inference", "context clues",
        "author purpose", "point of view", "genre", "literature",
        "vocabulary", "book",
    ],
    "personal": [
        "talent show", "club", "extracurricular", "permission slip",
        "field trip", "signup", "sign up", "volunteer", "fundraiser",
        "yearbook", "graduation", "prom", "homecoming", "team roster",
        "newsletter", "multicultural", "spirit week", "assembly",
        "ceremony", "recipe", "chore", "diary", "cruise",
        "expenses", "waiver", "tryout", "practice schedule",
        "game schedule", "announcements",
    ],
}

# ---------------------------------------------------------
# SUBJECT_DESCRIPTIONS — natural language sentences for Group C
# sentence-transformers embeds these; richer sentences → better accuracy.
# ---------------------------------------------------------

SUBJECT_DESCRIPTIONS = {
    "math": (
        "Mathematics class covering algebra, calculus, geometry, statistics, "
        "equations, functions, derivatives, integrals, and numerical problem solving."
    ),
    "biology": (
        "Biology class covering cells, DNA, genetics, evolution, photosynthesis, "
        "ecosystems, anatomy, physiology, and living organisms."
    ),
    "chemistry": (
        "Chemistry class covering elements, compounds, chemical reactions, molecules, "
        "atoms, the periodic table, stoichiometry, acids, and bases."
    ),
    "physics": (
        "Physics class covering forces, motion, energy, electricity, magnetism, "
        "waves, thermodynamics, circuits, and Newton's laws."
    ),
    "english": (
        "English language arts class covering grammar, literary analysis, Shakespeare, "
        "figurative language, rhetoric, close reading, and textual evidence."
    ),
    "history": (
        "History class covering wars, revolutions, ancient and modern civilizations, "
        "political movements, historical figures, timelines, and primary sources."
    ),
    "geography": (
        "Geography class covering maps, continents, countries, climate zones, biomes, "
        "population distribution, and physical and human geography."
    ),
    "computer_science": (
        "Computer science class covering coding, programming, algorithms, data structures, "
        "software development, debugging, and computational thinking."
    ),
    "economics": (
        "Economics class covering supply and demand, markets, inflation, GDP, fiscal "
        "policy, trade, entrepreneurship, and microeconomics and macroeconomics."
    ),
    "psychology": (
        "Psychology class covering human behavior, cognition, emotion, memory, "
        "personality, mental health disorders, and psychological theories."
    ),
    "spanish": (
        "Spanish language class covering vocabulary, verb conjugation, grammar, "
        "reading comprehension, and Hispanic culture and conversation."
    ),
    "french": (
        "French language class covering vocabulary, verb conjugation, grammar, "
        "reading comprehension, and French culture and conversation."
    ),
    "art": (
        "Art class covering drawing, painting, color theory, composition, perspective, "
        "art history, sculpture, and visual design techniques."
    ),
    "music": (
        "Music class covering music theory, notes, chords, rhythm, melody, "
        "instruments, sheet music, ensemble performance, and composition."
    ),
    "pe": (
        "Physical education class covering fitness, exercise, nutrition, sports, "
        "wellness, strength, endurance, and physical health."
    ),
    "science": (
        "General science class covering the scientific method, lab experiments, "
        "hypothesis, observations, data collection, variables, and conclusions."
    ),
    "social_studies": (
        "Social studies class covering civics, government, society, culture, "
        "human rights, global issues, current events, and citizenship."
    ),
    "environmental_science": (
        "Environmental science class covering climate change, sustainability, pollution, "
        "ecosystems, renewable energy, biodiversity, and conservation."
    ),
    "writing": (
        "Writing class covering essay composition, creative writing, narratives, "
        "persuasive arguments, drafts, revision, poetry, and citation."
    ),
    "reading": (
        "Reading class covering comprehension, vocabulary, fiction and nonfiction texts, "
        "book reports, summarizing, inference, and literary analysis."
    ),
    "personal": (
        "Personal, extracurricular, or school event files — schedules, permission slips, "
        "club sign-ups, talent shows, sports rosters, field trips, family documents, "
        "and non-academic content."
    ),
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


def format_size(size_bytes: int) -> str:
    """Return a human-readable file size string (e.g. 1.2 MB, 3.4 GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    else:
        return f"{size_bytes / 1024 ** 3:.2f} GB"
