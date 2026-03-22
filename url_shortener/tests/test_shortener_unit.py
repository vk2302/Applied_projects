from unittest.mock import MagicMock

from app.services.shortener import generate_short_code


def test_generate_short_code_returns_string():
    db = MagicMock()
    query_mock = db.query.return_value
    filter_mock = query_mock.filter.return_value
    filter_mock.first.return_value = None

    code = generate_short_code(db, length=6)

    assert isinstance(code, str)
    assert len(code) == 6


def test_generate_short_code_retries_if_code_exists(mocker):
    db = MagicMock()

    existing_link = object()

    query_mock = db.query.return_value
    filter_mock = query_mock.filter.return_value
    filter_mock.first.side_effect = [existing_link, None]

    mocked_choice = mocker.patch(
        "app.services.shortener.secrets.choice",
        side_effect=["A", "A", "A", "A", "A", "A", "B", "B", "B", "B", "B", "B"],
    )

    code = generate_short_code(db, length=6)

    assert code == "BBBBBB"
    assert filter_mock.first.call_count == 2
