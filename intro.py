# -*- coding: utf-8 -*-
from base import app
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response

@app.route("/intro")
def introduction():
    return render_template("intro.html", title="Gentle Introduction")
