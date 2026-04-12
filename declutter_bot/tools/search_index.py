def search_index(index: dict, query: str) -> list:
    """
    Simple keyword search across:
    - name
    - extension
    - category
    - path

    Returns a list of matching file entries.
    """

    query = query.lower()
    results = []

    for entry in index.values():
        haystack = " ".join([
            entry.get("name", ""),
            entry.get("extension", ""),
            entry.get("category", ""),
            entry.get("path", ""),
        ]).lower()

        if query in haystack:
            results.append(entry)

    return results
