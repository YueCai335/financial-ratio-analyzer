"""Health warnings: a set of fixed, explainable threshold rules.

Deliberately no model, no prediction. Each rule's threshold and reasoning
are written together, so every warning can be traced back to exactly which
number crossed which line.

Thresholds are generic rules of thumb, not industry-specific — a known
limitation: retailers routinely run a current ratio below 1 (riding
supplier payment terms is their business model, not a danger sign), a 70%
gross margin is normal for software but a 30% margin is solid for
manufacturing. A rigorous version would compare against the industry
median rather than a fixed number; that's out of scope for now.
"""

# (ratio name, direction, threshold, message shown when triggered)
# direction "below" = warn when under the threshold, "above" = warn when over
RULES = [
    (
        "current_ratio",
        "below",
        1.0,
        "Current ratio below 1: liabilities due within a year exceed assets "
        "that can be converted to cash within a year, indicating short-term "
        "repayment pressure",
    ),
    (
        "quick_ratio",
        "below",
        0.5,
        "Quick ratio below 0.5: liquid current assets, excluding inventory, "
        "cover less than half of short-term liabilities",
    ),
    (
        "debt_to_assets",
        "above",
        0.7,
        "Debt-to-assets above 70%: most of the company's assets are funded "
        "by debt, leaving little cushion against rate increases or "
        "operating swings",
    ),
    (
        "net_margin",
        "below",
        0.0,
        "Net margin is negative: the company posted a loss this year",
    ),
    (
        "gross_margin",
        "below",
        0.1,
        "Gross margin below 10%: little room left after direct costs, "
        "almost no room to cut prices",
    ),
]


def check(computed_ratios: dict) -> list[dict]:
    """Takes computed ratios and returns the list of triggered warnings.
    Returns an empty list if nothing is triggered.
    """
    warnings = []
    for key, direction, threshold, reason in RULES:
        value = computed_ratios.get(key)
        if value is None:
            continue
        triggered = value < threshold if direction == "below" else value > threshold
        if triggered:
            warnings.append(
                {
                    "ratio": key,
                    "value": value,
                    "threshold": threshold,
                    "message": reason,
                }
            )
    return warnings
