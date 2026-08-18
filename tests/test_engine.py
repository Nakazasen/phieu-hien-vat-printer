import pytest

from core.slip_printer_engine import (
    calculate_total_qty,
    format_string_qty,
    normalize_lot,
    validate_revision,
)


def test_calculate_total_qty():
    assert calculate_total_qty("10", "001/003") == "30"
    assert calculate_total_qty("10.5", "002/002") == "21"
    assert calculate_total_qty("5", "004") == "20"
    
    with pytest.raises(ValueError):
        calculate_total_qty("-5", "002")
        
    with pytest.raises(ValueError):
        calculate_total_qty("abc", "002")

def test_validate_revision():
    assert validate_revision("01") == "01"
    assert validate_revision("99") == "99"
    
    with pytest.raises(ValueError):
        validate_revision("1")
        
    with pytest.raises(ValueError):
        validate_revision("00")
        
    with pytest.raises(ValueError):
        validate_revision("100")

def test_format_string_qty():
    assert format_string_qty(1) == "000000010000"
    assert format_string_qty(180) == "000001800000"
    assert format_string_qty("25") == "000000250000"

def test_normalize_lot():
    assert normalize_lot(None) == "          "
    assert normalize_lot("") == "          "
    assert normalize_lot("Lot123") == "Lot123"
