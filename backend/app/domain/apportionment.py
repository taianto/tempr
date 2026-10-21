from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from math import isfinite


def hamilton_apportion(weights: Mapping[str, float], total: int) -> dict[str, int]:
    """Allocate ``total`` integer places in proportion to non-negative weights."""
    
    exact: dict[str, Fraction] = {}
    for category, raw_weight in weights.items():
        try:
            value = Decimal(str(raw_weight))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("weights must be finite non-negative numbers") from exc
        
        if not value.is_finite() or value < 0:
            raise ValueError("weights must be finite non-negative numbers")
        
        exact[category] = Fraction(value)

    weight_total = sum(exact.values(), Fraction(0))
    if weight_total == 0:
        raise ValueError("at least one weight must be positive")

    quotas = {name: weight * total / weight_total for name, weight in exact.items()}
    seats = {name: quota.numerator // quota.denominator for name, quota in quotas.items()}
    remaining = total - sum(seats.values())
    # Descending category name makes equal remainders deterministic and matches
    # the existing classification normalization convention.
    order = sorted(quotas, key=lambda name: (quotas[name] - seats[name], name), reverse=True)
    for category in order[:remaining]:
        seats[category] += 1
    return seats
