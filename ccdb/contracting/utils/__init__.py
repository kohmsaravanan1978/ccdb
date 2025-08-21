import logging

logger = logging.getLogger(__name__)

# Aktuell müssen existierende Verträge auf unterschiedliche Rechnungen aufgeteilt werden.
#   Grund 1: Kunde will es so
#   Grund 2: Verträge sind gemischt aus 0% und 19% Ust.

# Dies wird aktuell von der CCDB nicht unterstützt. Aus diesem Grund wurde ein virtueller Nummernkreis eingeführt
# um die Vertragsposten auf andere (virtuelle) Verträge zu verteilen.
# Abstimmung zwischen NG/SOB:
#     1.) Posten eines Vertrags, der 0% Vertragposten werden in die Vertragsnummer 888<Vertragsnummer> verschoben
#     2.) Ein Vertrag kann weiter Verträge haben um die CCDB dazu zu bringen getrennte Abrechnungen durchzuführen
#           Beispiel: Vertrag 126987
#           Dazu können weitere Verträge 991126987, 992126987, ... existieren


def sanitize_contract_number(contract_number):
    if contract_number < 999999:
        return contract_number
    contract_number_str = str(contract_number)
    if contract_number_str.startswith("99") or contract_number_str.startswith("888"):
        return int(contract_number_str[3:])
    logger.warning(
        f"Got contract number {contract_number}, and dont know what to do! Skipping transformation"
    )
    return contract_number
