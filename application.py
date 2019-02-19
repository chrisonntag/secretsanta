import os.path
import uuid
from functools import wraps
import simplejson as json
import traceback
import datetime
import bleach
from collections import defaultdict

from flask import Flask, Response, render_template, make_response, url_for, redirect
from flask import jsonify
from flask import request

import database as db
import heatmap
from database import User, DayAction
import studip


STATIC_DIR = '/static'

app = Flask(__name__, static_url_path=STATIC_DIR, template_folder='static')
app.debug = True


def print_exceptions(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            print('')
            print('------')
            print('API: exception')
            print(e)
            print(traceback.format_exc())
            print(request.url)
            print(request.data)
            print('------')
            raise
    return wrapped


def root_dir():
    return os.path.abspath(os.path.dirname(__file__)) + STATIC_DIR


def get_file(filename):
    try:
        src = os.path.join(root_dir(), filename)
        return open(src).read()
    except IOError as exc:
        return str(exc)


def get_error(msg):
    return jsonify({'result': 'ERROR', 'message': msg})


# Open database connection before requests and close them afterwards
@app.before_request
def before_request():
    db.DATABASE.connect()


@app.after_request
def after_request(response):
    db.DATABASE.close()
    return response


@app.route('/', methods=['GET'])
def root():
    content = get_file('index.html')
    return Response(content, mimetype="text/html")


# Serving static files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def get_resource(path):
    mimetypes = {
        ".css": "text/css",
        ".html": "text/html",
        ".js": "application/javascript",
    }
    complete_path = os.path.join(root_dir(), path)
    ext = os.path.splitext(path)[1]
    mimetype = mimetypes.get(ext, "text/html")
    content = get_file(complete_path)
    return Response(content, mimetype=mimetype)


if __name__ == '__main__':
    app.run()

