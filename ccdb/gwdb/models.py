from django.db import models
from django.db.models import deletion


class GwCbsVertrag(models.Model):
    parent_id = models.PositiveIntegerField(blank=True, null=True)
    firma = models.PositiveIntegerField()
    projekt = models.CharField(max_length=16)
    buchungskontoid = models.ForeignKey(
        "GwCbsBuchungskonto",
        db_column="buchungskontoId",
        on_delete=deletion.PROTECT,
        related_name="contracts",
    )  # Field name made lowercase.
    created_user_id = models.CharField(max_length=36, blank=True, null=True)
    modified_user_id = models.CharField(max_length=36, blank=True, null=True)
    midwife_user_id = models.CharField(max_length=36, blank=True, null=True)
    provision_customer_id = models.PositiveIntegerField(blank=True, null=True)
    ticket_id = models.PositiveIntegerField(blank=True, null=True)
    vname = models.CharField(max_length=100)
    kommentar = models.TextField()
    kunden_referenz_nummer = models.CharField(max_length=32, blank=True, null=True)
    erstellt = models.DateTimeField()
    beginn = models.DateField()
    letzte_rechnung = models.DateField()
    letzte_aenderung = models.DateTimeField()
    ende = models.DateField()
    ausgelaufen = models.IntegerField()
    ausgelaufen_ticket_id = models.PositiveIntegerField(blank=True, null=True)
    naechste_rechnung = models.DateField()
    frist = models.DateField()
    rechnungsintervall = models.IntegerField()
    kuend_frist = models.IntegerField()
    beginn_laufzeit = models.PositiveIntegerField()
    verlaengerung = models.IntegerField()
    rechnungsintervall_anpassung = models.PositiveIntegerField()
    rechnungsende_anpassung = models.PositiveIntegerField()
    zuletzt_gedruckt = models.DateField()
    unterzeichnet = models.IntegerField()
    unterzeichnet_am = models.DateField()
    gekuendigt = models.IntegerField()
    gekuendigt_am = models.DateTimeField()
    gekuendigt_ticket_id = models.PositiveIntegerField(blank=True, null=True)
    gekuendigt_kundenticket_id = models.PositiveIntegerField(blank=True, null=True)
    anlagen = models.CharField(max_length=255)
    t_vertrag_name = models.CharField(max_length=255)
    t_vertrag_beschr = models.CharField(max_length=255)
    t_postenbez = models.CharField(max_length=255)
    gw_iz_privileges_realm_id = models.PositiveIntegerField(blank=True, null=True)
    freigeschalten = models.IntegerField()
    freigeschalten_am = models.DateTimeField()
    suspended = models.PositiveIntegerField()
    suspended_reason = models.CharField(max_length=255, blank=True, null=True)
    einzelrechnung = models.PositiveIntegerField()
    alte_vertragsnummer_gwag = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "gw_cbs_vertrag"


class GwCbsVertragPosten(models.Model):
    deleted = models.PositiveIntegerField()
    vertragid = models.ForeignKey(
        GwCbsVertrag,
        models.DO_NOTHING,
        db_column="vertragid",
        related_name="gwcbsvertragposten_set",
    )
    vorlageid = models.IntegerField()
    reihenfolge = models.IntegerField()
    typ = models.CharField(max_length=20)
    name = models.CharField(max_length=60)
    beschreibung = models.TextField()
    preis = models.FloatField()
    gw_dsl_public_ippool_ip = models.CharField(
        unique=True, max_length=15, blank=True, null=True
    )
    gw_dsl_public_subnetpool_net = models.CharField(
        max_length=15, blank=True, null=True
    )
    freitraffic = models.PositiveIntegerField()
    abgerechnet = models.CharField(max_length=1)
    abgerechnetam = models.DateField(
        db_column="abgerechnetAm", blank=True, null=True
    )  # Field name made lowercase.
    subnet_size = models.PositiveIntegerField()
    vpn_id = models.PositiveIntegerField(blank=True, null=True)
    gw_ppp_accounts_id = models.PositiveIntegerField(unique=True, blank=True, null=True)
    gw_ip_subnets_id = models.PositiveIntegerField(blank=True, null=True)
    gw_nodes_id = models.PositiveIntegerField(blank=True, null=True)
    sparte = models.ForeignKey(
        "GwCbsVertragPostenSparten", db_column="sparte_id", on_delete=models.PROTECT
    )
    field_sparte_id = models.PositiveIntegerField(
        db_column="_sparte_id", blank=True, null=True
    )  # Field renamed because it started with '_'.
    tixi_device_id = models.PositiveIntegerField(unique=True, blank=True, null=True)
    # discountscale = models.ForeignKey(GwCbsDiscountscales, models.DO_NOTHING, blank=True, null=True)
    tixi_anpassungsposition_eeg2014 = models.PositiveIntegerField(blank=True, null=True)
    cs_building_id = models.CharField(max_length=20, blank=True, null=True)
    easybill_product_id = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "gw_cbs_vertrag_posten"


class GwCbsVertragPostenSparten(models.Model):
    deleted = models.DateTimeField(blank=True, null=True)
    fibu_konto = models.IntegerField()
    gruppe = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=8)
    midwife_user_id = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "gw_cbs_vertrag_posten_sparten"


class GwCbsBuchungskonto(models.Model):
    buchungskontoid = models.AutoField(
        db_column="buchungskontoId", primary_key=True
    )  # Field name made lowercase.
    kundeid = models.PositiveIntegerField(
        db_column="kundeId"
    )  # Field name made lowercase.
    active = models.CharField(max_length=1)
    kontostand = models.FloatField()
    zahlungsart = models.CharField(max_length=13)
    zustellung = models.ForeignKey(
        "GwZustellung",
        models.DO_NOTHING,
        db_column="zustellung",
        related_name="buchnungskonto",
    )
    zahlungsfrist = models.IntegerField()
    mwst = models.CharField(max_length=1)
    ust_id_nr = models.CharField(max_length=32, blank=True, null=True)
    ueberweisungsfrist = models.IntegerField()
    gwkonto = models.ForeignKey("self", models.DO_NOTHING, related_name="ugwkontos")
    gwkonto_dtaus_path = models.CharField(max_length=32, blank=True, null=True)
    bemerkung = models.TextField(blank=True, null=True)
    faelligkeitstyp = models.CharField(max_length=1)
    old_gwkonto_id = models.PositiveIntegerField()
    iban_elv_konto = models.PositiveIntegerField(blank=True, null=True)
    field_elv_vorhanden = models.IntegerField(
        db_column="_elv_vorhanden"
    )  # Field renamed because it started with '_'.
    ebics_account = models.CharField(max_length=32, blank=True, null=True)
    source_id = models.PositiveIntegerField(blank=True, null=True)
    creditor_id = models.CharField(max_length=32, blank=True, null=True)
    invoice_approval_by = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "gw_cbs_buchungskonto"


class GwCbsBuchungskontoKonto(models.Model):
    kontoid = models.AutoField(
        db_column="kontoId", primary_key=True
    )  # Field name made lowercase.
    buchungskonto = models.OneToOneField(
        GwCbsBuchungskonto,
        db_column="buchungskontoId",
        on_delete=deletion.PROTECT,
        blank=True,
        null=True,
    )
    inhaber = models.CharField(max_length=255, blank=True, null=True)
    kreditinstitut = models.CharField(max_length=255, blank=True, null=True)
    blz = models.CharField(max_length=100, blank=True, null=True)
    kontonummer = models.CharField(max_length=100, blank=True, null=True)
    geloescht = models.CharField(max_length=1)
    notizen = models.TextField()

    class Meta:
        managed = False
        db_table = "gw_cbs_buchungskonto_konto"


class GwCbsBuchungskontoSepaelv(models.Model):
    buchungskonto = models.OneToOneField(
        "GwCbsBuchungskonto",
        db_column="buchungskonto_id",
        primary_key=True,
        on_delete=models.PROTECT,
    )
    created = models.DateTimeField()
    modified = models.DateTimeField(blank=True, null=True)
    deleted = models.DateTimeField(blank=True, null=True)
    requested = models.DateTimeField(blank=True, null=True)
    request_document_id = models.PositiveIntegerField(blank=True, null=True)
    confirmed = models.DateTimeField(blank=True, null=True)
    confirm_document_id = models.PositiveIntegerField(blank=True, null=True)
    revoked = models.DateTimeField(blank=True, null=True)
    revoke_document_id = models.PositiveIntegerField(blank=True, null=True)
    first_used = models.DateTimeField(blank=True, null=True)
    last_used = models.DateTimeField(blank=True, null=True)
    mandatstyp = models.CharField(max_length=6)
    mandatsreferenz = models.CharField(max_length=35)
    kreditinstitut = models.CharField(max_length=64)
    bic = models.CharField(max_length=11)
    iban = models.CharField(max_length=34)
    kontoinhaber = models.CharField(max_length=150)
    anschrift = models.CharField(max_length=150)
    plz = models.CharField(max_length=20)
    ort = models.CharField(max_length=100)
    bundesland = models.CharField(max_length=100)
    land = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "gw_cbs_buchungskonto_sepaelv"


class GwCbsVertragPostenEasybillprodukte(models.Model):
    number = models.CharField(max_length=255)
    cost_price = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    export_cost1 = models.CharField(max_length=255, blank=True, null=True)
    export_cost2 = models.CharField(max_length=255, blank=True, null=True)
    export_identifier = models.CharField(max_length=255, blank=True, null=True)
    export_identifier_extended = models.CharField(max_length=255, blank=True, null=True)
    group_id = models.CharField(max_length=255, blank=True, null=True)
    login_id = models.CharField(max_length=255, blank=True, null=True)
    note = models.CharField(max_length=255, blank=True, null=True)
    price_type = models.CharField(max_length=255, blank=True, null=True)
    quantity = models.CharField(max_length=255, blank=True, null=True)
    sale_price = models.CharField(max_length=255, blank=True, null=True)
    sale_price2 = models.CharField(max_length=255, blank=True, null=True)
    sale_price3 = models.CharField(max_length=255, blank=True, null=True)
    sale_price4 = models.CharField(max_length=255, blank=True, null=True)
    sale_price5 = models.CharField(max_length=255, blank=True, null=True)
    sale_price6 = models.CharField(max_length=255, blank=True, null=True)
    sale_price7 = models.CharField(max_length=255, blank=True, null=True)
    sale_price8 = models.CharField(max_length=255, blank=True, null=True)
    sale_price9 = models.CharField(max_length=255, blank=True, null=True)
    sale_price10 = models.CharField(max_length=255, blank=True, null=True)
    stock = models.CharField(max_length=255, blank=True, null=True)
    stock_count = models.CharField(max_length=255, blank=True, null=True)
    stock_limit = models.CharField(max_length=255, blank=True, null=True)
    stock_limit_notify = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    unit = models.CharField(max_length=255, blank=True, null=True)
    vat_percent = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "gw_cbs_vertrag_posten_easybillprodukte"


class GwAamVorgang(models.Model):
    firma = models.PositiveIntegerField(null=True)
    deleted = models.DateTimeField(null=True)
    status = models.IntegerField()
    buchungskontoId = models.IntegerField(null=True)

    class Meta:
        managed = False
        db_table = "gw_aam_vorgang"


class GwAamLieferschein(models.Model):
    vorgang = models.ForeignKey(
        "gwAamVorgang", db_column="vorgang", on_delete=models.PROTECT
    )

    class Meta:
        managed = False
        db_table = "gw_aam_lieferschein"


class GwAamLieferscheinPosten(models.Model):
    lieferschein = models.ForeignKey(
        "gwAamLieferschein", db_column="lieferschein", on_delete=models.PROTECT
    )
    vorlage_id = models.PositiveIntegerField(null=True)
    reihenfolge = models.PositiveIntegerField(null=True)
    typ = models.CharField(max_length=255, blank=True, null=True)
    von = models.DateField(null=True)
    bis = models.DateField(null=True)
    anzahl = models.FloatField(null=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    beschreibung = models.TextField()
    optionen = models.CharField(max_length=255, blank=True, null=True)
    preis = models.FloatField(null=False)

    class Meta:
        managed = False
        db_table = "gw_aam_lieferschein_posten"


class GwCbsCreditmemos(models.Model):
    created = models.DateTimeField(null=True)
    modified = models.DateTimeField(null=True)
    created_user_id = models.CharField(max_length=36, blank=True, null=True)
    modified_user_id = models.CharField(max_length=36, blank=True, null=True)
    bookingaccount = models.ForeignKey(
        "GwCbsBuchungskonto",
        db_column="bookingaccount_id",
        on_delete=models.PROTECT,
    )
    credit_invoice_item_id = models.IntegerField(null=True)
    debit_invoice_item_id = models.IntegerField(null=True)
    billing_not_before = models.DateField(null=True)
    approved = models.DateTimeField(null=True)
    approved_user_id = models.CharField(max_length=36, blank=True, null=True)
    ticket_id = models.IntegerField(null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    von = models.DateField(null=True, db_column="from")
    bis = models.DateField(null=True, db_column="to")
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    amount = models.FloatField(null=False)
    price = models.FloatField(null=False)
    reason = models.TextField()

    class Meta:
        managed = False
        db_table = "gw_cbs_creditmemos"


class GwCbsRechnungenPositionen(models.Model):
    created = models.DateTimeField(null=True)
    buchungskonto = models.ForeignKey(
        "GwCbsBuchungskonto",
        on_delete=models.PROTECT,
        db_column="buchungskonto_id",
    )
    rechnung = models.ForeignKey(
        "GwCbsRechnungen", on_delete=models.PROTECT, db_column="rechnungId"
    )
    typ = models.CharField(max_length=255, blank=True, null=True)
    von = models.DateField(null=True)
    bis = models.DateField(null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    beschreibung = models.TextField()
    anzahl = models.FloatField(null=False)
    preis = models.FloatField(null=False)
    referenztyp = models.CharField(max_length=255, blank=True, null=True)
    referenz = models.IntegerField()

    class Meta:
        managed = False
        db_table = "gw_cbs_rechnungen_positionen"


class GwCbsRechnungen(models.Model):
    kundeid = models.IntegerField()
    buchungskonto = models.ForeignKey(
        "GwCbsBuchungskonto",
        db_column="buchungskontoId",
        on_delete=models.PROTECT,
    )
    transaction = models.ForeignKey(
        "GwCbsBuchungskontoTransaktionen",
        db_column="transaction_id",
        on_delete=models.PROTECT,
    )

    state_id = models.IntegerField()
    datum = models.DateTimeField(null=True)
    zahlungsziel = models.DateField(null=True)
    betrag = models.FloatField(null=False)
    mwst = models.FloatField(null=False)

    delivery_id = models.PositiveIntegerField(blank=True, null=True)
    gw_pdf_id = models.PositiveIntegerField(blank=True, null=True)
    storniert = models.IntegerField()

    def get_csv_data_array_for_bill_positions(self):
        from django.db import connections

        with connections["billing"].cursor() as cursor:
            cursor.execute(
                "SELECT * FROM v_steuerberater_export WHERE `Rechnung-Nummer`={bill_pk}".format(
                    bill_pk=self.id
                )
            )
            res = list()
            data = cursor.fetchall()
            for entry in data:
                res_item = list(entry)
                res_item[0] = res_item[0].strftime("%d.%m.%Y")
                res += [res_item]
            return res

    class Meta:
        managed = False
        db_table = "gw_cbs_rechnungen"


class GwCbsBuchungskontoTransaktionen(models.Model):
    transaktionid = models.AutoField(
        db_column="transaktionId", primary_key=True
    )  # Field name made lowercase.
    buchungskontoid = models.PositiveIntegerField(
        db_column="buchungskontoId"
    )  # Field name made lowercase.
    betrag = models.FloatField()
    bezahlt = models.FloatField()
    art = models.CharField(max_length=5)
    sepa_transaction_type = models.CharField(max_length=4, blank=True, null=True)
    datum_erstellt = models.DateTimeField()
    datum_buchungstag = models.DateField()
    datum_wertstellung = models.DateTimeField()
    verwendungszweck = models.CharField(max_length=255)
    datum_dtaus = models.DateTimeField(blank=True, null=True)
    datum_rueckbuchung = models.DateTimeField(blank=True, null=True)
    tracking_id = models.CharField(max_length=16)
    ebics_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    ebics_payment_id = models.CharField(max_length=64, blank=True, null=True)
    ebics_statuscode = models.CharField(max_length=4, blank=True, null=True)
    ebics_statusreasoncode = models.CharField(max_length=4, blank=True, null=True)
    bezahlt_tmp = models.FloatField(
        db_column="bezahlt_TMP"
    )  # Field name made lowercase.
    hbcilog = models.TextField()
    sepa1810dup = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "gw_cbs_buchungskonto_transaktionen"


class GwZustellung(models.Model):
    zustellungid = models.AutoField(
        db_column="zustellungId", primary_key=True
    )  # Field name made lowercase.
    zustellung_email = models.CharField(max_length=1)
    zustellung_post = models.CharField(max_length=1)
    zustellung_per_hand = models.CharField(max_length=1)
    zustellung_email_an = models.CharField(max_length=255)
    zustellung_post_an = models.TextField()
    zustellung_per_hand_an = models.CharField(max_length=255)
    zugestellt_email_am = models.DateTimeField(blank=True, null=True)
    zugestellt_post_am = models.DateTimeField(blank=True, null=True)
    zugestellt_per_hand_am = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "gw_zustellung"
