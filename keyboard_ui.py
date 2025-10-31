# --------------------------- Stock layout factories --------------------------- #
def _row(chars: str) -> List[Key]:
    """Helper to convert a string of characters into Key objects with matching ids/labels."""
    return [Key(id=f"Key{c.upper()}" if c.isalpha() else c, label=c) for c in chars]

def make_qwerty() -> KeyboardLayout:
    """Return a standard QWERTY layout with common control keys."""
    kb = KeyboardLayout(name="qwerty", layout_meta={"variant": "en-us"})
    kb.add_row(_row("qwertyuiop"), align="stagger")
    kb.add_row(_row("asdfghjkl"), align="stagger")
    kb.add_row([*_row("zxcvbnm"), Key(id="Backspace", label="⌫", group="control", width=2.0, meta={"action": "backspace"})])
    kb.add_row([
        Key(id="Shift", label="⇧", group="control", width=1.5, meta={"action": "shift"}),
        Key(id="Space", label="Space", group="control", width=4.0, meta={"action": "space", "text": " "}),
        Key(id="Enter", label="Enter", group="control", width=2.0, meta={"action": "enter"}),
    ])
    return kb

def make_abc() -> KeyboardLayout:
    """Return an ABC-ordered alphabet layout for accessibility or training."""
    kb = KeyboardLayout(name="abc", layout_meta={"variant": "alphabetical"})
    rows = ["abcdefghi", "jklmnopqr", "stuvwxyz"]
    for r in rows:
        kb.add_row(_row(r), align="left")
    kb.add_row([
        Key(id="Backspace", label="⌫", group="control", width=2.0, meta={"action": "backspace"}),
        Key(id="Space", label="Space", group="control", width=4.0, meta={"action": "space", "text": " "}),
        Key(id="Enter", label="Enter", group="control", width=2.0, meta={"action": "enter"}),
    ])
    return kb

def make_numeric() -> KeyboardLayout:
    """Return a numeric keypad layout with punctuation shortcuts."""
    kb = KeyboardLayout(name="numeric", layout_meta={"variant": "tenkey"})
    kb.add_row([Key(id="Digit7", label="7"), Key(id="Digit8", label="8"), Key(id="Digit9", label="9"), Key(id="Slash", label="/")], align="center")
    kb.add_row([Key(id="Digit4", label="4"), Key(id="Digit5", label="5"), Key(id="Digit6", label="6"), Key(id="Asterisk", label="*")], align="center")
    kb.add_row([Key(id="Digit1", label="1"), Key(id="Digit2", label="2"), Key(id="Digit3", label="3"), Key(id="Minus", label="-")], align="center")
    kb.add_row([Key(id="Digit0", label="0", width=2.0), Key(id="Dot", label="."), Key(id="Enter", label="Enter", group="control", meta={"action": "enter"})], align="center")
    return kb

# Register stock layouts and leave extension point for custom ones
LayoutRegistry.register("qwerty", make_qwerty)
LayoutRegistry.register("abc", make_abc)
LayoutRegistry.register("numeric", make_numeric)
