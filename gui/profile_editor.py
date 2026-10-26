# Window for editing a bot profile: every setting and attack, attacks switched on/off, reordered, added or removed.
# Saves to profiles/<name>.toml keeping its comments (tomlkit), after the same checks as loading, and the bot reloads it

import os
import re

import tomlkit
from tkinter import *
from tkinter.ttk import *

from data import profiles, values
from gui import scrolling
from tools import keyboard

KEYS = list(keyboard.BIND_NAMES)

# Each field: (key in the file, label, kind, default). kind is text, float, int, bool, pair ([min, max]), optional_int (blank: not
# set), or a list of choices. A field left at its default isn't added to the file
PROFILE_FIELDS = [
    (("description",), "Description", "text", ""),
    (("behaviour",), "Behaviour", list(profiles.BEHAVIOURS), "melee"),
    (("gone_delay",), "No-bar wait (s)", "float", 0.5),
    (("keys", "jump"), "Jump key", KEYS, "Alt"),
    (("keys", "loot"), "Loot key", KEYS, "Z"),
    (("movement", "platform_range"), "Platform jump range", "int", 50),
    (("movement", "platform_height"), "Platform jump height", "int", 100),
    (("ranged", "keep_distance"), "Keep distance (ranged)", "int", 0),
]
ATTACK_FIELDS = [
    ("enabled", "Enabled", "bool", True),
    ("name", "Name", "text", "New attack"),
    ("key", "Key", KEYS, "Ctrl"),
    ("range_x", "Range x: min, max", "pair", [0, 75]),
    ("range_y", "Range y: min, max", "pair", [-30, 25]),
    ("hit_time", "Hit time (s)", "float", 0.35),
    ("cooldown", "Cooldown (s)", "float", 0),
    ("min_health", "Min target health (0-1)", "float", 0),
    ("min_mobs", "Min mobs in reach", "int", 1),
    ("hit_range", "Hit range (blank: range x max)", "optional_int", None),
    ("opener", "First hit only", "bool", False),
    ("jump_attack", "Jump attack", "bool", False),
    ("jump_reach", "Jump reach", "int", 75),
]
MOBILITY_FIELDS = [
    ("type", "Type", list(profiles.MOBILITY_TYPES), "dash"),
    ("key", "Key (not for flash jump)", [""] + KEYS, ""),
    ("min_distance", "Used beyond distance", "int", 350),
]


def text(value):  # A setting as shown in an entry
    if value is None:
        return ""
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)


class Field:  # One setting: a label and an entry, checkbox or list, read back as the right type
    def __init__(self, parent, row, label, kind, value):
        self.label, self.kind = label, kind
        Label(parent, text=label).grid(sticky=W, row=row, column=0, padx=5, pady=2)
        if kind == "bool":
            self.vars = [BooleanVar(value=bool(value))]
            Checkbutton(parent, variable=self.vars[0]).grid(sticky=W, row=row, column=1, padx=5, pady=2)
        elif kind == "pair":
            self.vars = [StringVar(value=text(v)) for v in value]
            frame = Frame(parent)
            frame.grid(sticky=W, row=row, column=1, padx=5, pady=2)
            for var in self.vars:
                Entry(frame, textvariable=var, width=6).pack(side=LEFT, padx=(0, 4))
        elif isinstance(kind, list):
            self.vars = [StringVar(value=value)]
            Combobox(parent, textvariable=self.vars[0], values=kind, state="readonly", width=11).grid(sticky=W, row=row, column=1, padx=5, pady=2)
        else:
            self.vars = [StringVar(value=text(value))]
            Entry(parent, textvariable=self.vars[0], width=24 if kind == "text" else 8).grid(sticky=W, row=row, column=1, padx=5, pady=2)

    def raw(self):  # As typed, for rebuilding the field after attacks are reordered
        values_ = [var.get() for var in self.vars]
        return values_ if self.kind == "pair" else values_[0]

    def value(self):  # Raises ValueError with the field's name if what's typed isn't valid
        if self.kind in ("bool", "text") or isinstance(self.kind, list):
            return self.vars[0].get()
        if self.kind == "pair":
            return [number(var.get(), self.label) for var in self.vars]
        typed = self.vars[0].get().strip()
        if self.kind == "optional_int" and typed == "":
            return None
        value = number(typed, self.label)
        if self.kind in ("int", "optional_int"):
            if value != int(value):
                raise ValueError("%s must be a whole number" % self.label)
            return int(value)
        return float(value)


def number(typed, label):
    try:
        value = float(typed)
    except ValueError:
        raise ValueError("%s must be a number" % label)
    return int(value) if value.is_integer() else value


REQUIRED = {"name", "key", "range_x", "range_y", "type"}  # Written even at their defaults: loading needs them


def put(table, key, value, default):  # Sets a value in a tomlkit table, keeping the comment on its line
    old = table.get(key)
    if old is None and value == default and key not in REQUIRED:
        return  # Left at the default: no need to add it
    if value is None:
        if key in table:
            del table[key]
        return
    new = tomlkit.item(value)
    if old is not None and hasattr(old, "trivia"):
        new.trivia.indent, new.trivia.comment_ws, new.trivia.comment = old.trivia.indent, old.trivia.comment_ws, old.trivia.comment
    table[key] = new


class Section:  # One attack or mobility entry: its fields, and the file table it came from (None for a new one)
    def __init__(self, table, raw):
        self.table, self.raw, self.fields = table, raw, {}


class ProfileEditor:
    def __init__(self, master, name):
        self.name = name
        self.path = os.path.join(profiles.folder, name + ".toml")
        with open(self.path, encoding="utf-8") as f:
            self.doc = tomlkit.parse(f.read())
        self.window = Toplevel(master)
        self.window.title("Profile: %s" % name)
        self.window.geometry("460x720")
        bottom = Frame(self.window)  # Packed first so the scroll area can't push it out of the window
        bottom.pack(side=BOTTOM, fill=X, padx=5, pady=5)
        self.status = Label(bottom, wraplength=270)
        self.status.pack(side=LEFT, padx=5)
        Button(bottom, text="Close", command=self.window.destroy).pack(side=RIGHT, padx=2)
        Button(bottom, text="Save", command=self.save).pack(side=RIGHT, padx=2)
        content = Frame(self.window)
        content.pack(side=TOP, fill=BOTH, expand=True)
        _, _, self.body = scrolling.scrollable(content)

        self.profile_fields = {}
        frame = LabelFrame(self.body, text="Profile")
        frame.pack(fill=X, padx=5, pady=5)
        for row, (path, label, kind, default) in enumerate(PROFILE_FIELDS):
            self.profile_fields[path] = Field(frame, row, label, kind, self.lookup(path, default))
        self.attacks = [Section(t, None) for t in self.doc.get("attacks", [])]
        self.mobility = [Section(t, None) for t in self.doc.get("mobility", [])]
        self.lists = Frame(self.body)
        self.lists.pack(fill=X)
        self.build_lists()

    def lookup(self, path, default):
        table = self.doc
        for key in path[:-1]:
            table = table.get(key, {})
        return table.get(path[-1], default)

    # --- Attacks and mobility, rebuilt whenever one is moved, added or removed ---

    def build_lists(self):
        for child in self.lists.winfo_children():
            child.destroy()
        for i, section in enumerate(self.attacks):
            self.build_section(section, i, self.attacks, ATTACK_FIELDS, "Attack %d (tried in this order)" % (i + 1))
        Button(self.lists, text="Add attack", command=lambda: self.add(self.attacks, ATTACK_FIELDS)).pack(anchor=W, padx=5, pady=(0, 10))
        for i, section in enumerate(self.mobility):
            self.build_section(section, i, self.mobility, MOBILITY_FIELDS, "Mobility %d" % (i + 1))
        Button(self.lists, text="Add mobility", command=lambda: self.add(self.mobility, MOBILITY_FIELDS)).pack(anchor=W, padx=5, pady=(0, 10))

    def build_section(self, section, index, sections, fields, title):
        frame = LabelFrame(self.lists, text=title)
        frame.pack(fill=X, padx=5, pady=5)
        buttons = Frame(frame)
        buttons.grid(sticky=W, row=0, column=0, columnspan=2, padx=5, pady=(2, 4))
        Button(buttons, text="Up", width=5, command=lambda: self.move(sections, index, -1)).pack(side=LEFT, padx=(0, 4))
        Button(buttons, text="Down", width=5, command=lambda: self.move(sections, index, 1)).pack(side=LEFT, padx=(0, 4))
        Button(buttons, text="Remove", command=lambda: self.remove(sections, index)).pack(side=LEFT)
        section.fields = {}
        for row, (key, label, kind, default) in enumerate(fields, start=1):
            if section.raw is not None:  # Rebuilt: as it was typed
                value = section.raw[key]
            else:
                value = section.table.get(key, default) if section.table is not None else default
                value = list(value) if kind == "pair" else value
            section.fields[key] = Field(frame, row, label, kind, value)

    def remember(self):  # What's typed in every attack and mobility entry, before they're rebuilt
        for section in self.attacks + self.mobility:
            section.raw = {key: field.raw() for key, field in section.fields.items()}

    def move(self, sections, index, step):
        if 0 <= index + step < len(sections):
            self.remember()
            sections[index], sections[index + step] = sections[index + step], sections[index]
            self.build_lists()

    def remove(self, sections, index):
        self.remember()
        del sections[index]
        self.build_lists()

    def add(self, sections, fields):
        self.remember()
        sections.append(Section(None, None))
        self.build_lists()

    # --- Saving ---

    def save(self):
        try:
            self.apply()
            profiles.from_dict(self.name, self.doc.unwrap())  # The same checks as loading it
        except (ValueError, profiles.ProfileError) as e:
            self.status.configure(text=str(e), foreground="red")
            return
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(re.sub(r"\n{3,}", "\n\n", tomlkit.dumps(self.doc)))  # Reordered entries can bring extra blank lines
        if values.bot_profile == self.name:
            values.bot_profile_version += 1  # The bot reloads it
        self.status.configure(text="Saved", foreground="green")

    def apply(self):  # Writes what's in the window into the tomlkit document; raises ValueError for a field that isn't valid
        for (path, _, _, default), field in zip(PROFILE_FIELDS, self.profile_fields.values()):
            table = self.doc
            for key in path[:-1]:
                if key not in table:
                    if field.value() == default:
                        break
                    table[key] = tomlkit.table()
                table = table[key]
            else:
                put(table, path[-1], field.value(), default)
        for key, sections, fields in (("attacks", self.attacks, ATTACK_FIELDS), ("mobility", self.mobility, MOBILITY_FIELDS)):
            unchanged = [s.table for s in sections] == list(self.doc.get(key, []))  # Same entries in the same order: edit in place
            for section in sections:
                table = section.table if section.table is not None else tomlkit.table()
                for field_key, _, _, default in fields:
                    value = section.fields[field_key].value()
                    put(table, field_key, None if field_key == "key" and value == "" else value, default)
                section.table = table
            if unchanged and sections:
                continue
            if sections:
                entries = tomlkit.aot()
                for section in sections:
                    entries.append(section.table)
                self.doc[key] = entries
            elif key in self.doc:
                del self.doc[key]
