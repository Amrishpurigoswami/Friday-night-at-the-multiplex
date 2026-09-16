from cinema_pricing.importer import import_price_list


def test_importer_normalizes_prices_and_reports_duplicates_and_rejections():
    report = import_price_list(
        [
            {"name": " silver ", "price": "₹180.00"},
            {"name": "GOLD", "price": "250"},
            {"name": " gold ", "price": "25,000 paise"},
            {"name": "Recliner", "price": ""},
            {"name": "Balcony", "price": "-50"},
            {"name": "", "price": "100"},
            {"tier_name": "Box", "price": "0"},
        ]
    )

    assert [(item.normalized_name, item.price_paise) for item in report.imported] == [
        ("Silver", 18000),
        ("Gold", 25000),
    ]
    assert len(report.deduplicated) == 1
    assert [item.reason for item in report.rejected] == [
        "blank price",
        "negative price",
        "blank seat-class name",
        "zero price",
    ]


def test_importer_accepts_sequence_rows_and_rounds_rupees_half_up():
    report = import_price_list([["recliner", "400.005"], ["box", "99 paise"]])

    assert [item.price_paise for item in report.imported] == [40001, 99]


def test_importer_accepts_tier_name_column():
    report = import_price_list([{"tier_name": "Gold", "price": "₹250"}])

    assert report.imported[0].normalized_name == "Gold"