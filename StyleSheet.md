**General style conventions**

- All titles, bread crumbs, captions, column headings should be left-aligned and use <a href="https://en.wikipedia.org/wiki/Letter_case#Sentence_case">sentence case</a> (only first word and proper nouns capitalized).
- Bread should not be repetitive (so "Modular forms -> Hilbert", not "Modular forms -> Hilber modular forms").
- The "Learn more about" box should be present on all search/browse/statistics/object pages.
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

**Object page conveentions**

- Section headings should use `<h2>`, subsection headings should generally be avoided, but use `>h3>` when present.
- Content tables that are lists (each row is the same type of thing, e.g. local data at a prime) should use row striping (ntdata table)
- Captions in should be capitalized in sentence case, use colons in body but not in properties box
- Factorizations of negative numbers should include only the sign, not -1 (use web_latex_factored_integer in utilities.py) 

