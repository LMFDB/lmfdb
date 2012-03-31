# -*- coding: utf-8 -*-
from base import app
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response

_bc = 'intro'

@app.route("/intro")
def introduction():
    return render_template("intro.html", title="Gentle Introduction", kid='intro', body_class=_bc)

@app.route("/intro/features")
def introduction_features():
    return render_template("intro.html", title="Gentle Introduction - Features", kid='intro.features', body_class=_bc)

@app.route("/intro/tutorial")
def introduction_tutorial():
    return render_template("intro.html", title="Gentle Introduction - Tutorial", kid='intro.tutorial', body_class=_bc)

@app.route("/bigpicture")
def bigpicture():
    return render_template("bigpicture.html", title="A Map of the LMFDB", body_class="bigpicture")

@app.route("/editorial-board")
def edit_board():
    return render_template("intro.html", title="Editorial and Management Boards", kid='content.edit-board', body_class=_bc)

