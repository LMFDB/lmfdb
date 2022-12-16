import subprocess

pro = subprocess.run("pycodestyle lmfdb", shell=True, capture_output=True)
failedcodes = {
    line.split(":", 4)[3].lstrip().split(" ", 1)[0]
    for line in pro.stdout.decode().splitlines()
}

autopep8 = r"""
E241 - Fix extraneous whitespace around keywords.
E242 - Remove extraneous whitespace around operator.
E251 - Remove whitespace around parameter '=' sign.
E252 - Missing whitespace around parameter equals.
E26  - Fix spacing after comment hash for inline comments.
E265 - Fix spacing after comment hash for block comments.
E266 - Fix too many leading '#' for block comments.
E27  - Fix extraneous whitespace around keywords.
E301 - Add missing blank line.
E302 - Add missing 2 blank lines.
E303 - Remove extra blank lines.
E304 - Remove blank line following function decorator.
E305 - Expected 2 blank lines after end of function or class.
E306 - Expected 1 blank line before a nested definition.
E401 - Put imports on separate lines.
E402 - Fix module level import not at top of file
E501 - Try to make lines fit within --max-line-length characters.
E502 - Remove extraneous escape of newline.
E701 - Put colon-separated compound statement on separate lines.
E70  - Put semicolon-separated compound statement on separate lines.
E711 - Fix comparison with None.
E712 - Fix comparison with boolean.
E713 - Use 'not in' for test for membership.
E714 - Use 'is not' test for object identity.
E721 - Use "isinstance()" instead of comparing types directly.
E722 - Fix bare except.
E731 - Use a def when use do not assign a lambda expression.
W291 - Remove trailing whitespace.
W292 - Add a single newline at the end of the file.
W293 - Remove trailing whitespace on blank line.
W391 - Remove trailing blank lines.
W503 - Fix line break before binary operator.
W504 - Fix line break after binary operator.
W601 - Use "in" rather than "has_key()".
W602 - Fix deprecated form of raising exception.
W603 - Use "!=" instead of "<>"
W604 - Use "repr()" instead of backticks.
W605 - Fix invalid escape sequence 'x'.
W690 - Fix various deprecated code (via lib2to3).
"""
pairs = [
    tuple(elt.strip().replace(" - ", " ").split(" ", 1))
    for elt in autopep8.strip("\n").split("\n")
]
allcodes = dict(elt for elt in pairs if len(elt) == 2)
allcodes.pop("E26")
allcodes.pop("E301")
allcodes.pop("W503")
failedcodes.discard("E266")  # autopep8 doesn't really fully fix this one


passingcodes = sorted(set(allcodes).difference(failedcodes), key=lambda x: x[1:])
for elt in passingcodes:
    print(f"          # {elt} - {allcodes[elt]}")
print(
    f"          args: --recursive --in-place --aggressive --select={','.join(passingcodes)} lmfdb/"
)
