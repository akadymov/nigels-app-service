from app import app, db, socketio
from app.models import User, Room, Game, Hand, Turn, Player, TurnCard, DealtCards, HandScore
from gevent import monkey
from config import get_settings, get_environment
monkey.patch_all()

env = get_environment()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Room': Room, 'Game': Game, 'Hand': Hand, 'Turn': Turn, 'Player': Player, 'TurnCard': TurnCard, 'DealtCards': DealtCards, 'HandScore': HandScore}



if __name__ == '__main__':
    socketio.run(app, debug=True, port=get_settings('FLASK')['PORT'][env])