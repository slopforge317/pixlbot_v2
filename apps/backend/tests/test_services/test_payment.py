import json

from services.payment import build_receipt_provider_data


def test_build_receipt_provider_data_matches_invoice_total() -> None:
    provider_data = build_receipt_provider_data(
        description="Пополнение баланса PixlBot",
        amount_kopeks=19900,
    )

    receipt = json.loads(provider_data)["receipt"]
    item = receipt["items"][0]
    assert item["amount"] == {"value": "199.00", "currency": "RUB"}
    assert item["quantity"] == "1.00"
    assert item["payment_subject"] == "service"
    assert item["payment_mode"] == "full_payment"
    assert receipt["tax_system_code"] == 2
