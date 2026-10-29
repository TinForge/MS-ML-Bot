# Tests for the profile editor window, on copies of the shipped profiles in a temporary folder

import os
import shutil
import tempfile
import unittest
from tkinter import Tk
from unittest import mock

from data import profiles, values
from gui import profile_editor

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "profiles")  # Not your edited profiles


class ProfileEditorTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        for name in ("swordsman", "spearman"):
            shutil.copy(os.path.join(FIXTURES, name + ".toml"), self.folder)
        patcher = mock.patch.object(profiles, "folder", self.folder)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.folder)
        self.tk = Tk()
        self.tk.withdraw()
        self.addCleanup(self.tk.destroy)

    def text(self, name="swordsman"):
        with open(os.path.join(self.folder, name + ".toml"), encoding="utf-8") as f:
            return f.read()

    def open(self, name="swordsman"):
        return profile_editor.ProfileEditor(self.tk, name)

    def attack(self, editor, name):
        return next(s for s in editor.attacks if s.fields["name"].value() == name)

    def test_saving_unchanged_keeps_the_file_as_it_was(self):
        before = self.text()
        self.open().save()
        self.assertEqual(self.text(), before)

    def test_switching_off_an_attack_keeps_comments(self):
        editor = self.open()
        power = self.attack(editor, "Power attack")
        power.fields["enabled"].vars[0].set(False)
        editor.profile_fields[("gone_delay",)].vars[0].set("0.75")
        with mock.patch.object(values, "bot_profile", "swordsman"), mock.patch.object(values, "bot_profile_version", 3):
            editor.save()
            self.assertEqual(values.bot_profile_version, 4)  # The bot reloads it
        text = self.text()
        self.assertIn("enabled = false", text)
        self.assertIn("gone_delay = 0.75", text)
        self.assertIn("# Attacks are tried top to bottom", text)
        self.assertIn("min_mobs = 2             # Only when at least this many mobs are in reach", text)
        self.assertNotIn("Power attack", [a.name for a in profiles.load("swordsman").attacks])
        self.assertEqual(editor.status["text"], "Saved")

    def test_reordering_and_removing_attacks(self):
        editor = self.open()
        editor.move(editor.attacks, 2, -1)  # Basic attack above the power attack
        self.assertEqual([s.fields["name"].value() for s in editor.attacks], ["Mobbing attack", "Basic attack", "Power attack"])
        editor.remove(editor.attacks, 0)
        editor.save()
        self.assertEqual([a.name for a in profiles.load("swordsman").attacks], ["Basic attack", "Power attack"])

    def test_typed_values_survive_reordering(self):
        editor = self.open()
        self.attack(editor, "Basic attack").fields["hit_time"].vars[0].set("0.27")
        editor.move(editor.attacks, 2, -1)
        self.assertEqual(self.attack(editor, "Basic attack").fields["hit_time"].value(), 0.27)

    def test_adding_an_attack(self):
        editor = self.open()
        editor.add(editor.attacks, profile_editor.ATTACK_FIELDS)
        new = editor.attacks[-1]
        new.fields["name"].vars[0].set("Lightning")
        new.fields["key"].vars[0].set("X")
        new.fields["range_x"].vars[1].set("150")
        editor.save()
        attack = profiles.load("swordsman").attack_named("Lightning")
        self.assertEqual((attack.key, attack.range_x), ("X", (0, 150)))

    def test_invalid_values_are_reported_and_not_saved(self):
        before = self.text()
        editor = self.open()
        self.attack(editor, "Basic attack").fields["hit_time"].vars[0].set("fast")
        editor.save()
        self.assertEqual((editor.status["text"], self.text()), ("Hit time (s) must be a number", before))
        self.attack(editor, "Basic attack").fields["hit_time"].vars[0].set("0.3")
        for section in editor.attacks:
            section.fields["enabled"].vars[0].set(False)
        editor.save()
        self.assertIn("at least one enabled", editor.status["text"])  # The same checks as loading
        self.assertEqual(self.text(), before)

    def test_mouse_wheel_over_a_dropdown_scrolls_instead_of_changing_it(self):  # It used to move an attack's key along by one per step
        from tkinter.ttk import Combobox
        editor = self.open()
        self.tk.update()
        basic = self.attack(editor, "Basic attack")

        def widgets(w):
            for child in w.winfo_children():
                yield child
                yield from widgets(child)

        box = next(w for w in widgets(editor.window) if isinstance(w, Combobox) and str(w.cget("textvariable")) == str(basic.fields["key"].vars[0]))
        for _ in range(3):
            box.event_generate("<MouseWheel>", delta=-120)
            self.tk.update()
        self.assertEqual(basic.fields["key"].value(), "Ctrl")

    def test_profiles_with_mobility_and_comments(self):  # The spearman has a dash and a comment on most lines
        before = self.text("spearman")
        editor = self.open("spearman")
        self.assertEqual(editor.mobility[0].fields["type"].value(), "dash")
        editor.save()
        self.assertEqual(self.text("spearman"), before)
        editor.remove(editor.mobility, 0)
        editor.save()
        self.assertEqual(profiles.load("spearman").mobility, [])


if __name__ == "__main__":
    unittest.main()
