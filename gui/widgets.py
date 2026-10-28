# Widget updates that only reach Tk when something changed. Setting a label's text or image, even to what it already shows, makes
# Tk lay out and redraw the window: done for every label on every pass of the GUI loop, that took ~80 ms a pass

_unset = object()


def update(widget, **options):  # Like widget.configure(**options), skipping the options that are already showing
    shown = widget.__dict__.setdefault("_shown", {})
    changed = {key: value for key, value in options.items() if shown.get(key, _unset) is not value and shown.get(key, _unset) != value}
    if changed:
        widget.configure(**changed)
        shown.update(changed)
