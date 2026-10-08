import json
import os
from datetime import datetime, timedelta

SRS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'srs.json')

def _load():
    os.makedirs(os.path.dirname(SRS_FILE), exist_ok=True)
    if not os.path.exists(SRS_FILE):
        return {}
    with open(SRS_FILE) as f:
        return json.load(f)

def _save(data):
    with open(SRS_FILE, 'w') as f:
        json.dump(data, f)

def get_cards():
    return _load()

def save_cards(cards):
    _save(cards)

def review_card(card_id, front, back, quality):
    """SM-2 algorithm. quality: 0=wrong, 1=hard, 2=easy"""
    cards = _load()
    card = cards.get(card_id, {'interval': 1, 'ease': 2.5, 'reps': 0, 'front': front, 'back': back})
    card['front'] = front
    card['back'] = back

    if quality == 0:
        card['interval'] = 1
        card['reps'] = 0
    else:
        if card['reps'] == 0:
            card['interval'] = 1
        elif card['reps'] == 1:
            card['interval'] = 6
        else:
            card['interval'] = round(card['interval'] * card['ease'])
        card['reps'] += 1
        card['ease'] = max(1.3, card['ease'] + 0.1 - (2 - quality) * (0.08 + (2 - quality) * 0.02))

    due = datetime.now() + timedelta(days=card['interval'])
    card['due'] = due.strftime('%Y-%m-%d')
    cards[card_id] = card
    _save(cards)
    return card

def get_due_cards():
    today = datetime.now().strftime('%Y-%m-%d')
    return {k: v for k, v in _load().items() if v.get('due', '2000-01-01') <= today}
