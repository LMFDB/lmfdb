# Style guide

Below, we describe several styling conventions for the LMFDB. See also the
[Developer's Guide](https://github.com/LMFDB/lmfdb/blob/main/Development.md)
contains other conventions and information for the development process.

## General style conventions

- All titles, bread crumbs, captions, column headings should be left-aligned and use <a href="https://en.wikipedia.org/wiki/Letter_case#Sentence_case">sentence case</a> (only first word and proper nouns capitalized).
- Bread crumbs should avoid repetition (so "Modular forms -> Hilbert", not "Modular forms -> Hilbert modular forms").
- Section headings should be `<h2>`.
- All content under section headings should be slightly indented (use a table or `<p>` to achieve this).
- Whenever possible pages should be laid out to avoid horizontal scrolling on displays that are 1280 pixels or wider.

## Learn more about box

- This box should be present on all search/browse/object pages and include "Source of the data", "Completeness of the data", and "Reliability of the data" links to knowls of the form rcs.source.blah, rcs.cande.blah, rcs.rigor.blah (in that order).
- Completeness page headings should have the form "Completeness of blah data" where blah is singular (e.g. "modular form" or "elliptic curve"), and similarly for Source and Reliability pages.
- For sections where labels are relevant, there should also be "Labels of blah" links to knowls that explains the format of the labels for blah.
- When a particular "Learn more about" page is displayed, the link to that page should not be removed from the "Learn more about" box.
- In general, all mathematical quantities that are offset in some way (e.g. listed in a table or following a caption) should be displayed in math mode, including integers.  This does not apply to integers that appear in a sentence or as part of a phrase (e.g. "Genus 2 curves" not "Genus $2$ curves")

## Browse and search

- Each browse page should have a short summary at the top followed by sections labelled "Browse", "Search", "Find", in that order.
- Colons should not follow captions on browse/search pages.
- Captions should have knowls attached to them.
- Abbreviated column headings should omit the period.
- Input boxes should have standard widths (very long boxes, e.g. geometric invariants, may span the entire width),
- Option boxes should use standard captions in lower case (e.g. include/exclude/exactly or yes/no).
- If an option imposes no restrictions on the search it should be blank, and except where there is a good reason to do otherwise, this should be the default.
- All search pages should have "List of blahs" and "Random blah" buttons (and possibly others).
- Default number of results with filled in (confirm) value of 50 should be on main search page and not appear on refine search page.
- Search results table should use row striping (ntdata table), headings should all have knowls (or pseudo-knowls).
- Refine search page headings should have the form "Blah search results", where blah is singular.
- Refine search pages should have captions above input boxes, no example to right, gray example inside input box.
- Mathematical values listed in search results, including integers, should be in math mode, with the exception of tables whose entries are integers or percentages.
- Search result values that are words (e.g. even/odd, not computed, trivial, etc...) should be lower case in the default html font (not \mathrm).
- Boolean values in search results that indicate the presence of a property (e.g. IsSolvable) should generally use a checkmark &#x2713; for yes, blank for no, with the checkmark centered.
- Labels and lists (e.g. Weierstrass coefficients) in search results should be left-aligned.
- Alignment of numbers in search results may vary: fixed precision decimal numbers should be right aligned, as should integers whose values vary over a wide range (e.g. orders of Galois groups).  Small integers (e.g < 100) should generally be centered, factored signed integers (e.g discriminants) should be left aligned.
- Factored polynomials and factored positive integers in search results should be centered.

## Object pages

- Object page templates should extend homepage.html and include a content block.
- Every object page should have a properties box, and when relevant/available, a related objects box, and a downloads box.
- Content should be organized into sections (with`<h2>` headings).  The first section should contain the information that defines the object, the second section should contain standard invariants associated to the object, and from there they should be ordered from least to most technical/obscure.
- Content tables that are lists (each row is the same type of thing, e.g. local data at a prime) should use row striping (ntdata table).
- Content captions should be knowls (or contain a knowl) and be followed by colons.
- Any invariant listed in the properties box should also appear in the body (or header) of the page -- all information should be visible even with the property box closed.
- Values that are words (e.g yes/no, even/odd, Trivial) should be in lower case using the default (sans serif) font
- Mathematical values including integers should be displayed in math mode, with the exception of tables whose entries are integers or percentages.
- Factorizations of negative numbers should include only the sign, not -1 (use web_latex_factored_integer in utilities.py).
- Mathematical values, including integers, should be in math mode.
- Values that are words (e.g. yes/no, even/odd, not computed, trivial, etc...) should be lower case in the default html font (not \mathrm).
- Use the "\card" macro for cardinalities (which now displays #).

## Properties box

- Captions in the property box should be sentence case (like all captions) with no colon.
- The first line of the properties box should be the label (if one exists) followed by a portrait (if available), followed by up to 8 standard invariants or properties of the object that can be displayed in a compact form (the properties box should never scroll).
- Property values that are words (e.g yes/no, even/odd, Trivial) should be in lower case using the default (sans serif) font
- Mathematical values including integers should be in math mode.
- Integers in properties box should not be shown in factored form (the relevant the factorization should be in the body of the page) and should be shown in scientific notation if they are too large to fit (use prop_int_pretty).
- Properties that are words (e.g. yes/no, even/odd, not computed, trivial, etc...) should be lower case in the default html font (not \mathrm).

## Related objects box

- If an object has an L-function, all objects with the same L-function should appear (this will eventually be automated), as well as the L-function of the object itself, which should be the last entry in the related objects box.

## Downloads box

- Links in the Downloads box should have the form "Download X to Y" where X is the thing being downloaded (e.g. "all data", "coefficients", "traces", ...) and Y is the format (e.g. "text", "Sage", "Magma", ...).
