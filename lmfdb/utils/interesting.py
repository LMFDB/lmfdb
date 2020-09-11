from flask import render_template, url_for
from lmfdb.knowledge.knowl import knowldb

def interesting_knowls(category, table, title, url_for_label, label_col="label"):
    # category might be something like ec.q
    main_cat = category.split(".")[0]
    knowls = knowldb.search(category=main_cat, types=["top", "bottom", "type"], projection=["id", "title"])
    # Filter to only those with category correct
    knowls = [k for k in knowls if k["id"].startswith(category)]
    # Get the labels and links
    n = len(category)
    unsorted = {}
    for k in knowls:
        label = k["id"][n:]
        label = label[:label.rfind(".")]
        k["label"] = label
        k["link"] = url_for_label(label)
        unsorted[label] = k
    # Use the table for sorting
    sorted_labels = table.search({label_col: {"$in": [k["label"] for k in knowls]}}, "label")
    knowls = [unsorted[label] for label in sorted_labels]
    # Now sort so that top knowls appear first
    knowls.sort(key=lambda x: -x["type"])
    return render_template("interesting.html", knowls=knowls, title=title)
