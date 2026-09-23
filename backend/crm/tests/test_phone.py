from django.test import SimpleTestCase

from crm.phone import contact_links, extract_phones, links_for_stored, normalize_phone_digits, phones_from_fields


class PhoneNormalizeTests(SimpleTestCase):
    def test_russian_with_spaces_and_name(self):
        self.assertEqual(normalize_phone_digits("+7 916 123 45 67 Иван"), "79161234567")
        self.assertEqual(extract_phones("+7 916 123 45 67 Иван"), ["79161234567"])
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
        self.assertEqual(extract_phones("Customer"), [])

    def test_two_phones_on_separate_lines(self):
        text = "Мессенджеры на +380935440435\n597009966"
        self.assertEqual(normalize_phone_digits(text), "380935440435")
        self.assertEqual(extract_phones(text), ["380935440435", "995597009966"])

    def test_two_phones_separated_by_space(self):
        self.assertEqual(
            extract_phones("555111222 555333444"),
            ["995555111222", "995555333444"],
        )

    def test_phones_from_contact_and_nickname(self):
        self.assertEqual(
            phones_from_fields("Анна +995555111222", "555333444 @cake"),
            ["995555111222", "995555333444"],
        )

    def test_phones_from_fields_dedup(self):
        self.assertEqual(
            phones_from_fields("+995555111222", "555111222"),
            ["995555111222"],
        )


class PhoneTrickyCasesTests(SimpleTestCase):
    def test_extract_cases(self):
        cases = [
            ("599 09 51 06", ["995599095106"]),
            ("599\u00a009\u00a051\u00a006", ["995599095106"]),
            ("599\u202f09\u202f51\u202f06", ["995599095106"]),
            ("599\u200b09\u200b51\u200b06", ["995599095106"]),
            ("599–09–51–06", ["995599095106"]),
            ("599-09-51-06", ["995599095106"]),
            ("599.09.51.06", ["995599095106"]),
            ("(599) 09 51 06", ["995599095106"]),
            ("(599) 09-51-06", ["995599095106"]),
            ("＋599 09 51 06", ["995599095106"]),
            ("+599 09 51 06", ["995599095106"]),
            ("５９９ ０９ ５１ ０６", ["995599095106"]),
            ("тел: 599 09 51 06", ["995599095106"]),
            ("599 09 51 06 Марина", ["995599095106"]),
            ("599 09 51 06 (жена)", ["995599095106"]),
            ("599 09 51 06 доб. 12", ["995599095106"]),
            ("555 11 12 22", ["995555111222"]),
            ("593 28 35", ["9955932835"]),
            ("32 2 12 34 56", ["995322123456"]),
            ("422 27 12 34", ["995422271234"]),
            ("995599095106", ["995599095106"]),
            ("995 599 09 51 06", ["995599095106"]),
            ("995 599095106", ["995599095106"]),
            ("995 59 90 95 106", ["995599095106"]),
            ("+995 599 09 51 06", ["995599095106"]),
            ("+995599095106", ["995599095106"]),
            ("+995 (599) 09-51-06", ["995599095106"]),
            ("(+995) 599 09 51 06", ["995599095106"]),
            ("00995 599 09 51 06", ["995599095106"]),
            ("00 995 599 09 51 06", ["995599095106"]),
            ("380935440435", ["380935440435"]),
            ("380 93 544 04 35", ["380935440435"]),
            ("380 935440435", ["380935440435"]),
            ("+380 93 544 04 35", ["380935440435"]),
            ("+380935440435", ["380935440435"]),
            ("00 380 93 544 04 35", ["380935440435"]),
            ("37491123456", ["37491123456"]),
            ("374 91 123456", ["37491123456"]),
            ("+374 91 123456", ["37491123456"]),
            ("905551112233", ["905551112233"]),
            ("90 555 111 22 33", ["905551112233"]),
            ("+90 555 111 22 33", ["905551112233"]),
            ("14155552671", ["14155552671"]),
            ("1 415 555 2671", ["14155552671"]),
            ("+1 415 555 2671", ["14155552671"]),
            ("8 (916) 123-45-67", ["79161234567"]),
            ("8(916)123-45-67", ["79161234567"]),
            ("+7 (916) 123-45-67", ["79161234567"]),
            ("7 (916) 123-45-67", ["79161234567"]),
            ("8-916-123-45-67", ["79161234567"]),
            ("+7-916-123-45-67", ["79161234567"]),
            ("916 123 45 67", ["79161234567"]),
            ("00 7 916 123 45 67", ["79161234567"]),
            ("599 09 51 06 / 555 11 22 33", ["995599095106", "995555112233"]),
            ("599095106/555111222", ["995599095106", "995555111222"]),
            ("599 09 51 06 555 11 22 33", ["995599095106", "995555112233"]),
            ("599095106, 555 111 222", ["995599095106", "995555111222"]),
            (
                "+995 599 09 51 06 и 8 916 123 45 67",
                ["995599095106", "79161234567"],
            ),
            (
                "Марина 599 09 51 06, муж +7 (916) 123-45-67",
                ["995599095106", "79161234567"],
            ),
            (
                "Мессенджеры: 599 09 51 06 / +380 93 544 04 35",
                ["995599095106", "380935440435"],
            ),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(extract_phones(text), expected)

    def test_spaced_georgian_mobile_links(self):
        self.assertEqual(
            contact_links("599 09 51 06"),
            {
                "e164": "+995599095106",
                "tel": "tel:+995599095106",
                "whatsapp": "https://wa.me/995599095106",
                "telegram": "https://t.me/+995599095106",
            },
        )

    def test_country_code_is_not_prefixed_again(self):
        self.assertEqual(normalize_phone_digits("380935440435"), "380935440435")
        self.assertEqual(normalize_phone_digits("995 599 09 51 06"), "995599095106")
        self.assertNotIn("995995", normalize_phone_digits("995599095106"))
        self.assertFalse(normalize_phone_digits("380 93 544 04 35").startswith("995"))

    def test_nickname_spaced_phone_and_foreign_contact(self):
        self.assertEqual(
            phones_from_fields(
                "клиент 380 93 544 04 35",
                "599 09 51 06",
            ),
            ["380935440435", "995599095106"],
        )

    def test_same_georgian_number_with_and_without_code(self):
        self.assertEqual(
            phones_from_fields("599 09 51 06", "+995 599 09 51 06"),
            ["995599095106"],
        )


class TelegramNicknameTests(SimpleTestCase):
    def test_links_and_nicks(self):
        cases = [
            ("https://t.me/yashechka_ph", ["tg:yashechka_ph"]),
            ("http://t.me/yashechka_ph", ["tg:yashechka_ph"]),
            ("https://www.t.me/yashechka_ph", ["tg:yashechka_ph"]),
            ("t.me/yashechka_ph", ["tg:yashechka_ph"]),
            ("https://telegram.me/yashechka_ph/", ["tg:yashechka_ph"]),
            ("https://t.me/yashechka_ph?start=1", ["tg:yashechka_ph"]),
            ("@yashechka_ph", ["tg:yashechka_ph"]),
            ("ник @yashechka_ph.", ["tg:yashechka_ph"]),
            ("user@gmail.com", []),
            ("https://t.me/joinchat/AAAA", []),
            ("https://t.me/+995599095106", ["995599095106"]),
            (
                "https://t.me/yashechka_ph 599 09 51 06",
                ["tg:yashechka_ph", "995599095106"],
            ),
            (
                "599 09 51 06 https://t.me/yashechka_ph",
                ["995599095106", "tg:yashechka_ph"],
            ),
            ("@cake", []),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(phones_from_fields(text, ""), expected)

    def test_from_contact_and_nickname(self):
        self.assertEqual(
            phones_from_fields("Анна 599 09 51 06", "https://t.me/yashechka_ph"),
            ["995599095106", "tg:yashechka_ph"],
        )
        self.assertEqual(
            phones_from_fields("https://t.me/Yashechka_ph", "@yashechka_ph"),
            ["tg:Yashechka_ph"],
        )

    def test_telegram_nick_links_only_telegram(self):
        self.assertEqual(
            links_for_stored("tg:yashechka_ph"),
            {
                "e164": "@yashechka_ph",
                "tel": None,
                "whatsapp": None,
                "telegram": "https://t.me/yashechka_ph",
            },
        )
