from app import app, db
from app.models import User, Room, Game, Hand, Turn, Player, TurnCard, DealtCards, HandScore


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Room': Room, 'Game': Game, 'Hand': Hand, 'Turn': Turn, 'Player': Player, 'TurnCard': TurnCard, 'DealtCards': DealtCards, 'HandScore': HandScore}
