# GUI Section for Control

from tkinter import *
from tkinter.ttk import *

from gui import profile_editor, references
from data import values, profiles
from process import bot
from tools.persistent import save_data


class BotPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Bot", borderwidth=1, relief=GROOVE)
        #
        Label(self, text="Profile", font=references.var_font).grid(sticky=W, row=0, column=1, padx=0, pady=5)
        names = profiles.available()
        saved = save_data.bot_profile.read()
        self.profile_name = StringVar(value=saved if saved in names else (names[0] if names else ""))
        picker = Frame(self)  # The dropdown, with the button that opens its profile in the editor
        picker.grid(sticky=E, row=0, column=2, padx=0, pady=5)
        self.profile_picker = Combobox(picker, textvariable=self.profile_name, values=names, state="readonly", width=12)
        self.profile_picker.pack(side=RIGHT)
        Button(picker, text="Edit", width=5, command=lambda: self.edit_profile()).pack(side=RIGHT, padx=(0, 4))
        self.editor = None  # The open profile editor, so Edit brings it forward instead of opening another
        self.profile_picker.bind("<<ComboboxSelected>>", lambda event: self.on_profile_selected())  # Also fires when re-picking the same one, which reloads it
        self.on_profile_selected()
        #
        self.profile_info = Label(self, foreground="gray", wraplength=340)  # Profile description, or why it couldn't load
        self.profile_info.grid(sticky=W, row=1, column=0, columnspan=3, padx=10, pady=(0, 5))
        #
        self.potion_active = Label(self, image=references.red_icon)
        self.potion_active.grid(row=2, column=0, padx=15, pady=5)
        Label(self, text="Auto Potion", font=references.var_font).grid(sticky=W, row=2, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_potion()).grid(sticky=E, row=2, column=2, padx=0, pady=0)
        #
        self.looting_active = Label(self, image=references.red_icon)
        self.looting_active.grid(row=3, column=0, padx=15, pady=5)
        Label(self, text="Auto Looting", font=references.var_font).grid(sticky=W, row=3, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_looting()).grid(sticky=E, row=3, column=2, padx=0, pady=0)
        #
        self.human_input = Label(self, image=references.red_icon)
        self.human_input.grid(row=4, column=0, padx=15, pady=5)
        Label(self, text="Human Key Presses", font=references.var_font).grid(sticky=W, row=4, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_human_input()).grid(sticky=E, row=4, column=2, padx=0, pady=0)
        #
        self.random_behaviour = Label(self, image=references.red_icon)
        self.random_behaviour.grid(row=5, column=0, padx=15, pady=5)
        Label(self, text="Random Behaviour", font=references.var_font).grid(sticky=W, row=5, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_random_behaviour()).grid(sticky=E, row=5, column=2, padx=0, pady=0)
        #
        self.grid_columnconfigure(2, weight=1, uniform="column")
        self.pack(fill=X)


    def on_profile_selected(self):
        values.bot_profile = self.profile_name.get()
        values.bot_profile_version += 1
        save_data.bot_profile.save(values.bot_profile)

    def edit_profile(self):
        name = self.profile_name.get()
        if not name:
            return
        if self.editor is not None and self.editor.window.winfo_exists() and self.editor.name == name:
            self.editor.window.lift()
            return
        if self.editor is not None and self.editor.window.winfo_exists():
            self.editor.window.destroy()  # Another profile was open: show the one picked now
        self.editor = profile_editor.ProfileEditor(self.winfo_toplevel(), name)

    def toggle_looting(self):
        values.looting_active = not values.looting_active

    def toggle_random_behaviour(self):
        values.randomizer_active = not values.randomizer_active

    def toggle_potion(self):
        values.potion_active = not values.potion_active

    def toggle_human_input(self):  # Randomised, person-like key timing; off: exact, instant presses (more responsive)
        values.human_input = not values.human_input

    def refresh(self):
        if values.bot_profile_error is not None:
            self.profile_info.configure(text=values.bot_profile_error, foreground="red")
        elif bot.instance is not None and bot.instance.profile is not None:
            self.profile_info.configure(text=bot.instance.profile.description, foreground="gray")
        else:
            self.profile_info.configure(text="No profiles in profiles/" if not self.profile_picker["values"] else "", foreground="gray")
        self.looting_active.configure(image=self.status_icon(values.looting_active, values.bot_active))
        self.random_behaviour.configure(image=self.status_icon(values.randomizer_active, values.bot_active))
        self.potion_active.configure(image=self.status_icon(values.potion_active, True))  # Works without botting
        self.human_input.configure(image=self.status_icon(values.human_input, values.bot_active))

    def status_icon(self, enabled, running):  # Yellow when enabled but waiting on the Botting process
        if not enabled:
            return references.red_icon
        return references.green_icon if running else references.yellow_icon
