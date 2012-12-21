# -*- coding: utf-8 -*-
from base import app
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response


@app.route("/about")
def about():
    return render_template("about.html", title="About")


@app.route("/acknowledgment")
def acknowledgment():
    return render_template("acknowledgment.html", title="Acknowledgments")

# geeky pages have humans.txt


@app.route("/humans.txt")
def humans_txt():
    return render_template("acknowledgment.html", title="Acknowledgments")

# google's CSE for www.lmfdb.org/* (and *only* those pages!)


@app.route("/search")
def search():
    return render_template("search.html", title="Search LMFDB", bread=[('Search', url_for("search"))])

##
## INTRO PAGES
##

# common base class
_bc = 'intro'

bread = lambda: [('Intro', url_for("introduction"))]

# template displaying just one single knowl as an KNOWL_INC
_single_knowl = 'single.html'


@app.route("/intro")
def introduction():
    b = bread()
    return render_template(_single_knowl, title="Introduction", kid='intro', body_class=_bc, bread=b)


@app.route("/intro/features")
def introduction_features():
    b = bread()
    b.append(('Features', url_for("introduction_features")))
    return render_template(_single_knowl, title="Features", kid='intro.features', body_class=_bc, bread=b)


@app.route("/intro/tutorial")
def introduction_tutorial():
    b = bread()
    b.append(('Tutorial', url_for("introduction_tutorial")))
    return render_template(_single_knowl, title="Tutorial", kid='intro.tutorial', body_class=_bc, bread=b)


@app.route("/bigpicture")
def bigpicture():
    b = [('Big Picture', url_for('bigpicture'))]
    return render_template("bigpicture.html", title="A Map of the LMFDB", body_class=_bc, bread=b)


@app.route("/roadmap")
def roadmap():
    t = "Future Plans"
    b = [(t, url_for('roadmap'))]
    return render_template('roadmap.html', title=t, body_class=_bc, bread=b)

## INTRO PAGES END


@app.route("/editorial-board")
def edit_board():
    t = "Editorial and Management Boards"
    b = [(t, url_for("edit_board"))]
    return render_template(_single_knowl, title=t, kid='content.edit-board', body_class='', bread=b)


@app.route("/contact")
def contact():
    t = "Contact"
    b = [(t, url_for("contact"))]
    return render_template('contact.html', title=t, body_class='', bread=b)
