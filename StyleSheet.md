**General style conventions**

- All titles, bread crumbs, captions, column headings should be left-aligned and use <a href="https://en.wikipedia.org/wiki/Letter_case#Sentence_case">sentence case</a> (only first word and proper nouns capitalized).
- Bread should not be repetitive (so "Modular forms -> Hilbert", not "Modular forms -> Hilber modular forms").
- The "Learn more about" box should be present on all search/browse/statistics/object pages and include "Source of the data", "Completeness of the data", and "Reliability of the data" linked to knowls of the form rcs.source.blah, rcs.cande.blah, rcs.rigor.blah (in that order), as well as a link of the form "Labels of blah" whenever relevant that explains the format of the labels used.
- When a particular "Learn more about" page is displayed, the link to that page should not be removed from the "Learn more about" box.
- Section headings should be `<h2>`.
- All content under section headings should be slightly indented (use a table or `<p>` to achieve this)

**Browse and search**

- Colons should not follow captions on browse/search pages.
- Jump box captions should have the form "Find a specific blah, or blah by blah" should have knowls on the blahs, the input box should be on the line below (no caption in front) and the button should say "Find".
- Search heading on main browse page should simply be "Search".
- Abbreviated column headings should omit the period.
- Input boxes should have standard widths (very long boxes, e.g. geometric invariants, may span the entire width),
- Option boxes should use standard captions in lower case (e.g. include/exclude/exactly or yes/no).
- If an option imposes no restrictions on the search it should be blank, and except where there is a good reason to do otherwise, this should be the default.
- All search pages should have "List of blahs" and "Random blah" buttons (and possibly others).
- Default number of results with filled in (confirm) value of 50 should be on main search page and not appear on refine search page.
- Search results table should use row striping (ntdata table), headings should all have knowls (or pseudo-knowls).
- Refine search page headings should have the form "Blah search results", where blah is singular.
- Refine search pages should have captions above input boxes, no example to right, gray example inside input box.

**Object page conventions**

- Content should be organized intos sections (with`<h2>` headings).  The first section should contain the infromation that defines the objeect, the second section should contain standard invariants associated to the object, and from there they should be ordered from least to most technical/obscure.
- Content tables that are lists (each row is the same type of thing, e.g. local data at a prime) should use row striping (ntdata table).
- Every object page should have a properties box that starts with the label, then a portrait (if available), followed by standard invariants/properities that can be displayed in a compact form.
- Captions should be followed by colons in the body but not in the properties box.
- Any invariant listed in the properties box should also appear in the body (or header) of the page -- all information should be visible even with the property box closed.
- Factorizations of negative numbers should include only the sign, not -1 (use web_latex_factored_integer in utilities.py) 
- Every object page should have a related object box.  If the object has an L-function, all objects with the same L-function should appear, along with a link to the objects L-function.
- Links to the Downloads box should be labelled "Download X to Y" where X is the thing being downloaded (e.g. all data, coefficients, traces, ...) and Y is the format (e.g. text, Sage, Magma, ...).

