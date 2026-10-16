"""Salary figures over a sample of search results. Pure functions."""
from statistics import median, quantiles


def _midpoint(pay: dict) -> float:
    low, high = pay["min"], pay["max"]
    if low is not None and high is not None:
        return (low + high) / 2
    return float(low if low is not None else high)


def summarize(jobs: list[dict]) -> dict:
    """Group the jobs that publish a salary by pay unit.

    A posting counts at the midpoint of its range, or at its floor/cap when only one is
    given. Quartiles need at least four postings, otherwise they are left out.
    """
    by_unit: dict[str, list[float]] = {}
    for job in jobs:
        if job["pay"]:
            by_unit.setdefault(job["pay"]["unit"], []).append(_midpoint(job["pay"]))
    out = {}
    for unit, values in by_unit.items():
        values.sort()
        entry = {"count": len(values), "min": round(values[0]), "median": round(median(values)),
                 "max": round(values[-1])}
        if len(values) >= 4:
            q1, _, q3 = quantiles(values, n=4)
            entry["p25"], entry["p75"] = round(q1), round(q3)
        out[unit] = entry
    undisclosed = sum(1 for j in jobs if not j["pay"])
    return {
        "sampled": len(jobs),
        "undisclosed_share": round(undisclosed / len(jobs), 2) if jobs else 0,
        "by_unit": out,
    }
