from django.test import SimpleTestCase

from crm.phone import contact_links, normalize_phone_digits


class PhoneNormalizeTests(SimpleTestCase):
    def test_russian_with_spaces_and_name(self):
        self.assertEqual(normalize_phone_digits("+7 916 123 45 67 Иван"), "79161234567")
        self.assertEqual(
            contact_links("+7 916 123 45 67 Иван"),
            {
                "e164": "+79161234567",
                "tel": "tel:+79161234567",
                "whatsapp": "https://wa.me/79161234567",
                "telegram": "https://t.me/+79161234567",
            },
        )

    def test_local_georgian_without_country_code(self):
        self.assertEqual(normalize_phone_digits("5932835"), "9955932835")
        self.assertEqual(
            contact_links("5932835"),
            {
                "e164": "+9955932835",
                "tel": "tel:+9955932835",
                "whatsapp": "https://wa.me/9955932835",
                "telegram": "https://t.me/+9955932835",
            },
        )

    def test_russian_eight_prefix(self):
        self.assertEqual(normalize_phone_digits("8 916 123 45 67"), "79161234567")

    def test_georgian_international(self):
        self.assertEqual(normalize_phone_digits("+995555111222"), "995555111222")

    def test_no_phone(self):
        self.assertIsNone(normalize_phone_digits("Customer"))
        self.assertIsNone(contact_links("Customer"))

    def test_two_phones_on_separate_lines(self):
        self.assertEqual(
            normalize_phone_digits("Мессенджеры на +380935440435\n597009966"),
            "380935440435",
        )
