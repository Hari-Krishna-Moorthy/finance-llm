from app.services.ingestion import parse_hdfc_statement, parse_sbi_statement


def test_parse_hdfc_statement_uses_hdfc_template():
    df = parse_hdfc_statement("uploads/339ad2dfea614a82bd9cf20d76c00c48_Acct Statement_7808_27052026_18.18.47.xls")

    assert not df.empty
    assert {"Date", "Description", "Withdrawal", "Deposit"}.issubset(df.columns)


def test_parse_sbi_statement_uses_passworded_template():
    df = parse_sbi_statement("uploads/216b200fafe7456686f4c2eba0fd0b64_AccountStatement_27052026_18341.xlsx", password="HARI30082001")

    assert not df.empty
    assert {"Date", "Description", "Debit", "Credit", "Balance"}.issubset(df.columns)
