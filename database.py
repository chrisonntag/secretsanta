from peewee import *
import datetime


DATABASE = SqliteDatabase('data.db')


class BaseModel(Model):
    class Meta:
        database = DATABASE


class Game(BaseModel):
    name = CharField(unique=True)
    uuid = UUIDField(unique=True)
    imageurl = CharField()
    text = TextField()
    triggered = BooleanField(default=False)


class Participant(BaseModel):
    game = ForeignKeyField(Game, backref='participants')
    uuid = UUIDField(unique=True)
    name = CharField()
    mail = CharField()
    wishes = TextField()


class Partner(BaseModel):
    game = ForeignKeyField(Game)
    donor = ForeignKeyField(Participant)
    gifted = ForeignKeyField(Participant)


def create_tables():
    with DATABASE:
        DATABASE.create_tables([Game, Participant, Partner])


def create_game(name, uuid, imageurl, text):
    try:
        with DATABASE.atomic():
            # Attempt to create the user. If the username is taken, due to the
            # unique constraint, the database will raise an IntegrityError.
            game = Game.create(
                name=name,
                uuid=uuid,
                imageurl=imageurl,
                text=text)
    except IntegrityError:
        raise IntegrityError


def create_participant(name, mail, gamename, uuid):
    try:
        with DATABASE.atomic():
            # Attempt to create the user. If the username is taken, due to the
            # unique constraint, the database will raise an IntegrityError.
            game = Game.get(Game.name == gamename)
            participant = Participant.create(
                game=game,
                name=name,
                mail=mail,
                uuid=uuid)
    except IntegrityError:
        raise IntegrityError


