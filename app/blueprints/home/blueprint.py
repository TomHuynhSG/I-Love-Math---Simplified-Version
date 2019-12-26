# app/blueprints/home/blueprint.py
"""
This module is the Flask blueprint for the product catalog page (/).
"""


from flask import Blueprint, render_template


home_page = Blueprint('home_page', __name__)


@home_page.route('/')
def display():
    return render_template('home.html')

