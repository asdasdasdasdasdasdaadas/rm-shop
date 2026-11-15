import io
import unittest
import xml.dom.minidom
import zipfile

from app import stats_export, xlsx


class XlsxWriter(unittest.TestCase):
    def test_valid_package_with_numbers_and_text(self):
        data = xlsx.build([("Подарки", [[("Итоги", "title")], [("Кто", "head"), ("₽", "head")], ["Админ", 1500], ["<&>", 2.5]]),
                           ("Подарки", [["дубль"]]), ("a/b:c*?", [])])
        z = zipfile.ZipFile(io.BytesIO(data))
        for name in z.namelist():
            xml.dom.minidom.parseString(z.read(name))
        book = z.read("xl/workbook.xml").decode()
        self.assertIn('name="Подарки"', book)
        self.assertIn('name="Подарки 2"', book)
        self.assertNotIn("/", book.split("<sheets>")[1].split("name=")[3].split('"')[1])
        sheet = z.read("xl/worksheets/sheet1.xml").decode()
        self.assertIn("<v>1500</v>", sheet)
        self.assertIn("&lt;&amp;&gt;", sheet)


class Layout(unittest.TestCase):
    def test_scalars_tables_and_labels(self):
        rows = stats_export.layout({"ok": True, "users_total": 5, "items": [{"kind": "broadcast", "sent": 3}]},
                                   kinds={"broadcast": "Рассылка"})
        flat = [[c[0] if isinstance(c, tuple) else c for c in r] for r in rows]
        self.assertIn(["Пользователей всего", 5], flat)
        self.assertIn(["Тип", "Отправлено"], flat)
        self.assertIn(["Рассылка", 3], flat)
        self.assertNotIn("ok", str(flat))

    def test_own_column_names_stay(self):
        self.assertEqual(stats_export._label("Подключили VPN"), "Подключили VPN")
        self.assertEqual(stats_export._label("clicked_at"), "Нажал")
        self.assertEqual(stats_export._label("new_thing"), "New thing")


if __name__ == "__main__":
    unittest.main()
