import pytest
from apps.core.utils import mask_phone_number, mask_email


class TestMaskPhoneNumber:
    def test_masks_standard_kenyan_number(self):
        result = mask_phone_number('0712345678')
        assert result == '0712***678'

    def test_masks_longer_number(self):
        result = mask_phone_number('254712345678')
        assert result == '2547***678'

    def test_returns_short_number_unchanged(self):
        result = mask_phone_number('123')
        assert result == '123'


class TestMaskEmail:
    def test_masks_standard_email(self):
        result = mask_email('john.doe@example.com')
        assert result == 'joh***@example.com'

    def test_masks_short_local_part(self):
        result = mask_email('ab@example.com')
        assert result == 'a***@example.com'

    def test_returns_invalid_email_unchanged(self):
        result = mask_email('invalid-email')
        assert result == 'invalid-email'

    def test_returns_empty_string_unchanged(self):
        result = mask_email('')
        assert result == ''