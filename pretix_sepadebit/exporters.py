import csv
import io
import zipfile
import pytz
from datetime import datetime

from django.utils.translation import gettext as _, gettext_lazy, pgettext_lazy
from pretix.base.exporter import BaseExporter
from pretix.base.models import Order, OrderPosition, Question, OrderPayment

from pretix_sepadebit.payment import DPSGSepaDebit
from pretix.base.settings import SettingsSandbox

class DebitList(BaseExporter):
    identifier = "debitlistcsv"
    verbose_name = gettext_lazy("DPSG: List of all SEPA debits (CSVs)")
    category = pgettext_lazy("export_category", "Invoices")
    description = gettext_lazy(
        "Download a spreadsheet of all SEPA debits that have been made. Includes mandate export, SEPA address export and Diamant invoice export as csv files in a zip archive."
    )

    def __init__(self, event, organizer, progress_callback=lambda v: None):
        super().__init__(event, organizer, progress_callback)
        self.settings = SettingsSandbox('payment', DPSGSepaDebit.identifier, event)
    def render(self, form_data: dict):
        mandate_export_headers = ['Satzart', 'VKZ', 'Kontonummer', 'Mandatsbezeichnung', 'Mandatsnummer', 'BIC', 'IBAN_Nummer', 'Unterschrift_am', 'Status', 'Mandatstyp', 'Einmalmandat', 'Standardmandat', 'BankImDebAnlegen', 'Glaeubiger_ID', 'Glaeubiger_Name', 'Letzte_Verwendung_am'
        ]

        sepa_address_headers = ['Kontonummer', 'Name 1', 'Straße', 'PLZ', 'Ort', 'E-Mail Adresse', 'Land']

        diamant_invoice_headers =['KZ', 'Datum', 'Rechnung', 'Kunde', 'SAKO', 'Belegung', 'Wert1', 'Steuersatz', 'Steuer', 'KSt', 'KTr', 'KZ2', 'Wert_KR', 'Waehrung', 'Wert2', 'Konsolidierung']

        mandate_export_file = io.StringIO()
        sepa_address_file = io.StringIO()
        diamant_invoice_file = io.StringIO()

        mandate_export_writer = csv.DictWriter(mandate_export_file, quoting=csv.QUOTE_NONNUMERIC, delimiter=",", fieldnames=mandate_export_headers)
        sepa_address_writer = csv.DictWriter(sepa_address_file, quoting=csv.QUOTE_NONNUMERIC, delimiter=",", fieldnames=sepa_address_headers)
        diamant_invoice_writer = csv.DictWriter(diamant_invoice_file, quoting=csv.QUOTE_NONNUMERIC, delimiter=",", fieldnames=diamant_invoice_headers)

        mandates = OrderPayment.objects.filter(order__event=self.event).filter(provider=DPSGSepaDebit.identifier).filter(state=OrderPayment.PAYMENT_STATE_CONFIRMED).select_related("sepadebit_due")

        tz = pytz.timezone(self.event.settings.timezone)

        sako = self.settings.get('diamant_nominal_account')
        belegung = self.settings.get('diamant_description')
        kst = self.settings.get('diamant_nominal_account')
        ktr = self.settings.get('diamant_cost_object')
        prefix = self.settings.get('reference_prefix')

        mandate_exports = []
        sepa_addresses = []
        diamant_invoices = []

        for mandate in mandates:
            if not mandate.order.invoices.exists():
                print('No invoice found for order ' + mandate.order.code)
                continue
            last_invoice = mandate.order.invoices.last()
            invoice_no = last_invoice.invoice_no
            common_key = prefix + invoice_no[-4:]

            full_invoice_no = last_invoice.full_invoice_no

            mandate_export = {}
            mandate_export['Kontonummer'] = common_key
            mandate_export['Satzart'] = "PM"
            mandate_export['VKZ'] = "0"
            mandate_export['Mandatsbezeichnung'] = mandate.info_data['account']
            mandate_export['Mandatsnummer'] = mandate.info_data['reference']
            mandate_export['BIC'] = mandate.info_data['bic']
            mandate_export['IBAN_Nummer'] = mandate.info_data['iban']
            mandate_export['Unterschrift_am'] = mandate.created.astimezone(tz).strftime('%Y%m%d')
            mandate_export['Status'] = "A"
            mandate_export['Mandatstyp'] = "CORE"
            mandate_export['Einmalmandat'] = "J"
            mandate_export['Standardmandat'] = "N"
            mandate_export['BankImDebAnlegen'] = "J"
            mandate_export['Letzte_Verwendung_am'] = ""
            mandate_export['Glaeubiger_ID'] = ""
            mandate_export['Glaeubiger_Name'] = ""
            mandate_exports.append(mandate_export)

            sepa_address = {}
            sepa_address['Kontonummer'] = common_key
            sepa_address['Name 1'] = mandate.order.invoice_address.name
            sepa_address['Straße'] = mandate.order.invoice_address.street
            sepa_address['PLZ'] = mandate.order.invoice_address.zipcode
            sepa_address['Ort'] = mandate.order.invoice_address.city
            sepa_address['Land'] = mandate.order.invoice_address.country
            sepa_address['E-Mail Adresse'] = mandate.order.email
            sepa_addresses.append(sepa_address)

            diamant_invoice = {}
            diamant_invoice['Kunde'] = common_key
            diamant_invoice['KZ'] = 'L'
            diamant_invoice['Datum'] = mandate.sepadebit_due.date.strftime('%Y%m%d')
            diamant_invoice['Rechnung'] = full_invoice_no
            diamant_invoice['SAKO'] = sako
            diamant_invoice['Belegung'] = belegung + ' - ' + full_invoice_no
            diamant_invoice['Wert1'] = mandate.order.total
            diamant_invoice['Steuersatz'] = 0
            diamant_invoice['Steuer'] = 0
            diamant_invoice['KSt'] = kst
            diamant_invoice['KTr'] = ktr
            diamant_invoice['KZ2'] = 1
            diamant_invoice['Wert_KR'] = mandate.order.total * -1
            diamant_invoice['Waehrung'] = 'EUR'
            diamant_invoice['Wert2'] = mandate.order.total
            diamant_invoice['Konsolidierung'] = ''
            diamant_invoices.append(diamant_invoice)

        mandate_export_writer.writeheader()
        for row in mandate_exports:
            mandate_export_writer.writerow(row)

        sepa_address_writer.writeheader()
        for row in sepa_addresses:
            sepa_address_writer.writerow(row)

        diamant_invoice_writer.writeheader()
        for row in diamant_invoices:
            diamant_invoice_writer.writerow(row)

        archive = io.BytesIO()
        with zipfile.ZipFile(archive, mode='w') as zip_archive:
            zip_archive.writestr('diamant_invoice.csv', diamant_invoice_file.getvalue())
            zip_archive.writestr('sepa_address.csv', sepa_address_file.getvalue())
            zip_archive.writestr('mandate_export.csv', mandate_export_file.getvalue())

        return ('sepaexports.zip', 'application/zip', archive.getbuffer())
