from decimal import ROUND_HALF_UP, Decimal


def to_german_number_presentation(number, decimal_places=None, grouping=True):
    import locale

    locale.setlocale(locale.LC_NUMERIC, "de_DE.utf8")
    if isinstance(number, Decimal):
        if decimal_places:
            number = number.quantize(
                Decimal("0.{}1".format("0" * (decimal_places - 1))),
                rounding=ROUND_HALF_UP,
            )
        return "{:n}".format(number)
    return locale.format(
        "%.{}f".format(decimal_places) if decimal_places else "%f",
        number,
        grouping=grouping,
    )
