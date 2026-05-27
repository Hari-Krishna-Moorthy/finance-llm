from app.services.ingestion import _extract_upi_id


def test_extract_upi_id_from_description():
    description = "UPI-JAIGURU-JAIGURU2992@OKHDFCBANK-CNRB0000033-120882152208-UPI"
    assert _extract_upi_id(description) == "UPI-JAIGURU-JAIGURU2992"
