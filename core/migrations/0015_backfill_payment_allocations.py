from decimal import Decimal

from django.db import migrations
from django.db.models import Q


def backfill_payment_allocations(apps, schema_editor):
    Company = apps.get_model("core", "companies")
    Invoice = apps.get_model("core", "Invoices")
    Payment = apps.get_model("core", "CompanyPayment")
    Allocation = apps.get_model("core", "PaymentAllocation")

    for company in Company.objects.all():
        Allocation.objects.filter(payment__company=company).delete()

        invoices = list(Invoice.objects.filter(company=company).order_by("date_of_issue", "id"))
        payments = list(Payment.objects.filter(company=company, active=True).order_by("payment_date", "id"))

        remaining_by_invoice = {
            invoice.id: Decimal(invoice.amount or Decimal("0.00"))
            for invoice in invoices
        }

        for payment in payments:
            remaining_payment = Decimal(payment.amount or Decimal("0.00"))
            if remaining_payment <= 0:
                continue

            for invoice in invoices:
                remaining_invoice = remaining_by_invoice[invoice.id]
                if remaining_invoice <= 0:
                    continue
                if remaining_payment <= 0:
                    break

                allocated_amount = min(remaining_payment, remaining_invoice)
                if allocated_amount <= 0:
                    continue

                Allocation.objects.create(
                    payment=payment,
                    invoice=invoice,
                    amount=allocated_amount,
                )
                remaining_by_invoice[invoice.id] = remaining_invoice - allocated_amount
                remaining_payment -= allocated_amount

        for invoice in invoices:
            invoice.status = remaining_by_invoice[invoice.id] <= 0
            invoice.save(update_fields=["status"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_alter_members_gender_alter_members_mitroo_type_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_payment_allocations, migrations.RunPython.noop),
    ]
