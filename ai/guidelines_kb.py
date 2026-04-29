"""
Species-specific pet care knowledge base used by the RAG care assistant.

Retrieval works by keyword matching: if a KB key appears as a substring of the
lowercased task title or question, that guideline is included in the prompt
context. Unknown species fall back to "other".
"""

CARE_GUIDELINES: dict[str, dict[str, dict]] = {
    "dog": {
        "walk": {
            "min_duration_minutes": 20,
            "recommended_frequency": "daily",
            "notes": (
                "Dogs need at least 20–30 minutes of walking per day. "
                "Larger or more active breeds need 45–60 minutes. "
                "Consistent daily walks support physical and mental health. "
                "Skipping more than one day in a row is not recommended."
            ),
            "sources": ["ASPCA Dog Care", "AKC Exercise Guidelines"],
        },
        "feeding": {
            "min_duration_minutes": 5,
            "recommended_frequency": "daily (twice)",
            "notes": (
                "Adult dogs typically eat twice daily. Puppies need 3–4 meals per day. "
                "Always provide fresh water. Avoid feeding immediately before or after "
                "vigorous exercise to reduce the risk of bloat."
            ),
            "sources": ["ASPCA Nutrition", "AKC Feeding Guide"],
        },
        "grooming": {
            "min_duration_minutes": 15,
            "recommended_frequency": "weekly",
            "notes": (
                "Short-haired breeds: brush every 1–2 weeks. "
                "Long-haired breeds: brush daily or every few days to prevent matting. "
                "Regular grooming also helps you spot skin issues or parasites early."
            ),
            "sources": ["AKC Grooming Guide"],
        },
        "training": {
            "min_duration_minutes": 10,
            "recommended_frequency": "daily",
            "notes": (
                "Short, frequent training sessions (10–15 minutes) are more effective "
                "than long ones. Use positive reinforcement. Daily practice maintains "
                "good behavior and strengthens the human-dog bond."
            ),
            "sources": ["APDT Training Guidelines"],
        },
        "medication": {
            "min_duration_minutes": 5,
            "recommended_frequency": "daily",
            "notes": (
                "Never skip prescribed medications. Give at the same time each day "
                "to maintain consistent blood levels. Contact your vet if a dose is missed "
                "rather than doubling up."
            ),
            "sources": ["AVMA Medication Guidelines"],
        },
        "bath": {
            "min_duration_minutes": 20,
            "recommended_frequency": "monthly",
            "notes": (
                "Most dogs need bathing every 4–6 weeks. Overbathing strips natural "
                "skin oils and can cause dryness or irritation. Always use dog-specific "
                "shampoo; human shampoo disrupts a dog's skin pH."
            ),
            "sources": ["AKC Grooming Guide"],
        },
        "vet": {
            "min_duration_minutes": 30,
            "recommended_frequency": "yearly",
            "notes": (
                "Healthy adult dogs need annual wellness exams. Puppies under one year "
                "and senior dogs (7+ years) typically need visits every 6 months. "
                "Keep vaccinations and parasite prevention up to date."
            ),
            "sources": ["AVMA Preventive Care Guidelines"],
        },
        "play": {
            "min_duration_minutes": 15,
            "recommended_frequency": "daily",
            "notes": (
                "Dogs benefit from at least 30 minutes of play or exercise daily in "
                "addition to structured walks. Interactive play provides mental stimulation "
                "and reduces destructive behaviors caused by boredom."
            ),
            "sources": ["ASPCA Dog Care"],
        },
    },
    "cat": {
        "feeding": {
            "min_duration_minutes": 5,
            "recommended_frequency": "daily (twice)",
            "notes": (
                "Adult cats typically eat twice daily. Kittens under six months need "
                "3–4 meals per day. Always provide fresh water; many cats prefer a "
                "water fountain over a bowl. Measure portions to avoid obesity."
            ),
            "sources": ["ASPCA Cat Care", "Cornell Feline Health Center"],
        },
        "litter": {
            "min_duration_minutes": 5,
            "recommended_frequency": "daily",
            "notes": (
                "Scoop the litter box at least once daily; twice daily is ideal for "
                "multi-cat households. Do a full litter change weekly. Cats may refuse "
                "dirty boxes and eliminate elsewhere. Aim for one box per cat plus one extra."
            ),
            "sources": ["ASPCA Cat Care"],
        },
        "grooming": {
            "min_duration_minutes": 10,
            "recommended_frequency": "weekly",
            "notes": (
                "Short-haired cats: brush weekly to reduce shedding and hairballs. "
                "Long-haired cats: brush daily to prevent painful matting. "
                "Most cats do not need baths unless they get into something."
            ),
            "sources": ["ASPCA Cat Care"],
        },
        "play": {
            "min_duration_minutes": 15,
            "recommended_frequency": "daily",
            "notes": (
                "Cats need 15–20 minutes of interactive play daily for physical and "
                "mental health. Indoor cats especially benefit from stimulating play "
                "with wand toys or puzzle feeders. Spread sessions throughout the day."
            ),
            "sources": ["Cornell Feline Health Center"],
        },
        "vet": {
            "min_duration_minutes": 30,
            "recommended_frequency": "yearly",
            "notes": (
                "Healthy adult cats need annual wellness exams. Senior cats (7+ years) "
                "should visit every 6 months. Indoor cats still need regular checkups "
                "and vaccinations. Dental health should be assessed at each visit."
            ),
            "sources": ["AVMA Preventive Care Guidelines", "Cornell Feline Health Center"],
        },
        "medication": {
            "min_duration_minutes": 5,
            "recommended_frequency": "daily",
            "notes": (
                "Give medications at consistent times each day. Some cats are easier "
                "to medicate with pills hidden in a small treat or pill pocket. "
                "Contact your vet if a dose is missed rather than adjusting the dose yourself."
            ),
            "sources": ["AVMA Medication Guidelines"],
        },
    },
    "other": {
        "feeding": {
            "min_duration_minutes": 5,
            "recommended_frequency": "daily",
            "notes": (
                "Most small animals need fresh food and water daily. Research your "
                "species' specific dietary needs carefully — requirements vary widely. "
                "Remove uneaten perishable food promptly to prevent spoilage."
            ),
            "sources": ["ASPCA Small Animal Care"],
        },
        "cleaning": {
            "min_duration_minutes": 15,
            "recommended_frequency": "weekly",
            "notes": (
                "Enclosure cleaning prevents odor, bacteria, and disease. Spot-clean "
                "daily by removing waste. Do a thorough full clean weekly or as needed. "
                "Use species-safe, fragrance-free cleaning products and rinse thoroughly."
            ),
            "sources": ["ASPCA Small Animal Care"],
        },
        "handling": {
            "min_duration_minutes": 10,
            "recommended_frequency": "daily",
            "notes": (
                "Regular, gentle handling reduces stress and builds trust. Start with "
                "short sessions (5 minutes) and gradually increase as the animal grows "
                "comfortable. Always support the animal's body and avoid sudden movements."
            ),
            "sources": ["ASPCA Small Animal Care"],
        },
    },
}


def retrieve_guidelines(species: str, task_title: str) -> list[dict]:
    """Return matching care guidelines for a species and task title.

    Checks whether any KB keyword appears as a substring of the lowercased
    task_title. Falls back to "other" if the species is not in the KB.
    Always returns a list (empty if nothing matches).
    """
    title_lower = task_title.lower()
    species_lower = species.lower()

    if species_lower in CARE_GUIDELINES:
        species_key = species_lower
        species_kb = CARE_GUIDELINES[species_lower]
    else:
        species_key = "other"
        species_kb = CARE_GUIDELINES.get("other", {})

    results = []
    for keyword, guideline in species_kb.items():
        if keyword in title_lower:
            results.append({"key": f"{species_key}/{keyword}", **guideline})
    return results
