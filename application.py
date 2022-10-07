import os.path
import uuid
from functools import wraps
import simplejson as json
import traceback
import datetime
import random
import bleach
import configparser
from collections import defaultdict

from flask import Flask, Response, render_template, make_response, url_for, redirect, abort
from flask import jsonify
from flask import request
from flask_mail import Mail, Message

import database as db
from database import Game, Participant, Partner


PROJ_DIR = os.path.dirname(os.path.abspath(__file__))

config = configparser.RawConfigParser()
config.read(os.path.join(PROJ_DIR, 'config.cfg'))


STATIC_DIR = '/static'

app = Flask(__name__, static_url_path='', static_folder='static', template_folder='static')
app.debug = True

app.config['MAIL_SERVER']= config.get('mail', 'host')
app.config['MAIL_PORT'] = config.get('mail', 'port')
app.config['MAIL_USERNAME'] = config.get('mail', 'user')
app.config['MAIL_PASSWORD'] = config.get('mail', 'password')
app.config['MAIL_USE_TLS'] = config.getboolean('mail', 'tls')
app.config['MAIL_USE_SSL'] = config.getboolean('mail', 'ssl')
mail = Mail(app)

@app.errorhandler(404)
def not_found(e):
# defining function
    return render_template("/404.html")

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
def root_view():
    db_games = Game.select();
    games = []
    for game in db_games:
        games.append({'name': game.name, 'imageurl': game.imageurl, 'text': game.text, 'uuid': game.uuid, 'triggered': game.triggered})

    if len(games) == 0:
        return redirect(url_for('create_view'))


    return render_template('/index.html', games=games)


@app.route('/create', methods=['GET', 'POST'])
@print_exceptions
def create_view():
    if request.method == 'POST':
        data = request.form
        name = data.get('name')
        imageurl = data.get('imageurl')
        text = data.get('text')
        key = uuid.uuid4().hex

        try:
            db.create_game(name, key, imageurl, text)
        except db.IntegrityError as e:
            return get_error('Could not create game.')

        return redirect(url_for('root_view'))

    content = get_file('create.html')
    return Response(content, mimetype="text/html")


@app.route('/register', methods=['GET', 'POST'])
@print_exceptions
def register_view():
    if request.method == 'POST':
        name = request.form.get('name', None)
        email = request.form.get('email', None)
        game_uuid = request.form.get('game', None)
        game = Game.get(Game.uuid == game_uuid)
        key = uuid.uuid4().hex

        p = Participant.select().where(Participant.mail == email, Participant.game == game)
        if len(p) == 0:
            Participant.create(game=game, uuid=key, name=name, mail=email)
            return redirect(url_for('game_view', game=game_uuid))
        else:
            return render_template('/register.html', game=game_uuid)
    else:
        game_uuid = request.args.get('g', None)
        if game_uuid is not None:
            return render_template('/register.html', game=game_uuid)


@app.route('/trigger', methods=['GET'])
@print_exceptions
def trigger_view():
    game_uuid = request.args.get('g', None)
    if game_uuid is not None:
        game = Game.get(Game.uuid == game_uuid)
        participants = Participant.select().where(Participant.game == game)

        if not game.triggered and len(participants) > 2:

            # members list containing objects of participants
            members = [{"name": p.name, "mail": p.mail, "uuid": p.uuid} for p in participants]

            # partner list contains tuples of list indizes from members list.
            partners = []

            # select random partner from members where partner is not the
            # same person nor on the right side of a partner relation
            for i in range(0, len(members)):
                potential_partners = list(range(0, len(members)))

                potential_partners.remove(i) # delete itself
                bi = list(filter(lambda x: x[1] == i, partners))
                if len(bi) > 0:
                    potential_partners.remove(bi[0][0]) # delete direct partner

                if len(partners) > 0:
                    assigned = [pair[1] for pair in partners]
                    for el in assigned:
                        try:
                            potential_partners.remove(el) # delete already assigned
                        except ValueError as e:
                            continue

                partner = random.choice(potential_partners)
                partners.append((i, partner))

            allocations = []
            for el in partners:
                allocations.append((members[el[0]], members[el[1]]))

            # Save partners
            for el in allocations:
                donor = Participant.get(Participant.uuid == el[0]['uuid'])
                gifted = Participant.get(Participant.uuid == el[1]['uuid'])
                Partner.create(donor=donor, gifted=gifted, game=game)

            game.triggered = True
            game.save()
            # return render_template('/trigger.html', allocations=allocations)
            return redirect(url_for('game_view', game=game.uuid))
        elif len(participants) <= 2:
            # not enough partners
            return redirect(url_for('game_view', game=game.uuid))
        else:
            # Game has already been triggered
            for participant in participants:
                partner = Partner.get(Partner.donor == participant, Partner.game == game)
                url = request.url_root + 'user/' + str(participant.uuid)
                msg = Message('Secret Santa: Auslosung', sender = config.get('mail', 'from'), recipients=[participant.mail])
                msg.body = "Hallo %s,\n\n dein ausgeloster Partner ist %s. Damit niemand seinen Partner vergisst und jeder up-to-date ist, was sich jemand wuenscht, kannst du in Zukunft unter %s nachschauen, wer es ist." % (participant.name, partner.gifted.name, url)
                mail.send(msg)

            return redirect(url_for('game_view', game=game.uuid))


@app.route('/games/<game>', methods=['GET'])
@print_exceptions
def game_view(game=None):
    try:
        game = Game.get(Game.uuid == game)
    except Exception as e:
        game = None 

    if game:
        participants = Participant.select().where(Participant.game == game)
        return render_template('/game.html', game=game, participants=participants)
    else:
        abort(404)


@app.route('/games/<game>', methods=['DELETE'])
@print_exceptions
def game_delete(game):
    Participant.delete().where(Participant.game == game).execute()
    Game.delete().where(Game.uuid == game).execute()
    return "Game was successfully deleted"
 

@app.route('/user/<user>', methods=['GET', 'POST'])
@print_exceptions
def user_view(user=None):
    try:
        user = Participant.get(Participant.uuid == user)
    except Exception as e:
        user = None

    if not user:
        abort(404)
        
    partner = Partner.get(Partner.donor == user, Partner.game == user.game)

    if request.method == 'POST':
        wishes = request.form.get('wishes', None)
        if wishes is not None:
            user.wishes = wishes
            user.save()

    return render_template('/user.html', user=user, partner=partner)



if __name__ == '__main__':
    app.run()

