"""
Name normalization for joining Birthing-Friendly registry rows to
HCAHPS facility records.

The BF registry has no CCN. HCAHPS has the CCN. Tool 1 joins them by
facility name. Most NY rows match after light normalization; a handful
need targeted rules. Extend `normalize` empirically — add a rule only
when a real unmatched pair demands it.

Run as a script for a side-by-side diagnostic on the local data:

    .venv\\Scripts\\python src\\name_matching.py
"""

def normalize(name: str) -> str:
    """Normalize a hospital name for cross-source equality matching.

    Uppercases, strips apostrophes (including the literal escaped
    backslash-apostrophe present in some BF rows), strips periods,
    strips leading/trailing whitespace. Internal whitespace is left
    intact — collapsing it created a false collision between two
    distinct HCAHPS facilities sharing a branded name (Garnet Health
    Medical Center Catskills) that differ only in a single vs double
    space.
    """
    if name is None:
        return ""
    s = name.upper()
    s = s.replace("\\'", "")
    s = s.replace("'", "")
    s = s.replace(".", "")
    return s.strip()


if __name__ == "__main__":
    import csv
    from pathlib import Path

    DATA_DIR = Path(__file__).resolve().parent.parent / "data"
    BF_PATH = DATA_DIR / "Birthing_Friendly_Hospitals_Geocoded.csv"
    HCAHPS_PATH = DATA_DIR / "HCAHPS-Hospital-NY.csv"

    with HCAHPS_PATH.open(newline="", encoding="utf-8") as f:
        hcahps_names = sorted({row["Facility Name"] for row in csv.DictReader(f)})
    hcahps_normed = {normalize(n): n for n in hcahps_names}

    with BF_PATH.open(newline="", encoding="utf-8") as f:
        bf_ny = [row for row in csv.DictReader(f) if row["state"] == "NY"]

    matched, unmatched = [], []
    for row in bf_ny:
        key = normalize(row["name"])
        if key in hcahps_normed:
            matched.append((row["name"], hcahps_normed[key]))
        else:
            unmatched.append(row["name"])

    print(f"NY BF rows:  {len(bf_ny)}")
    print(f"Matched:     {len(matched)}")
    print(f"Unmatched:   {len(unmatched)}")
    print()
    print("Unmatched BF names:")
    for n in unmatched:
        print(f"  - {n!r}")
    print()
    print(f"HCAHPS facilities total: {len(hcahps_names)}")
    print("First 30 HCAHPS names for visual scan:")
    for n in hcahps_names[:30]:
        print(f"  - {n!r}")
