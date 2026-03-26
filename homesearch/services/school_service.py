"""School rating extraction from homeharvest data rows."""


def get_school_rating_from_row(row: dict) -> tuple[int | None, str]:
    """Extract school rating from a homeharvest DataFrame row if present.

    Returns (rating_1_to_10, district_name). Returns (None, "") on failure.
    """
    for col in ["schools_rating", "elementary_school_score", "school_score", "rating"]:
        val = row.get(col)
        if val is not None:
            try:
                rating = int(float(val))
                if 1 <= rating <= 10:
                    district = str(row.get("school_name", row.get("elementary_school", "")) or "")
                    return rating, district
            except (ValueError, TypeError):
                pass
    return None, ""
