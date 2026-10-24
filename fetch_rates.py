"""Reads the Duhok market board on saidoco.com/m/ and writes rates.json for the Our Home app.

Runs once an hour on GitHub. Only the public exchange rates are stored here: no household data.
On the board, "فروتن" is the selling price (what you pay for 1 dollar) and "كرين" the buying price
(what you get for 1 dollar).
"""
import html, json, re, sys, urllib.request
from datetime import datetime, timezone

URL = 'https://saidoco.com/m/'
CURRENCIES = {'دولار': 'usd', 'يورو': 'eur', 'جنيه': 'gbp'}
SANE = {'usd': (900, 4000), 'eur': (900, 5000), 'gbp': (900, 6000)}

def read_board(page):
    page = re.sub(r'<(svg|style|script).*?</\1>', '', page, flags=re.S)
    lines = [l.strip() for l in html.unescape(re.sub(r'<[^>]+>', '\n', page)).split('\n') if l.strip()]
    day = next((m.group(0) for l in lines if (m := re.search(r'\d{4}-\d{2}-\d{2}', l))), None)
    clock = next((m.group(0) for l in lines if (m := re.search(r'\d{1,2}:\d{2}\s*[ap]m', l, re.I))), None)
    rates = {}
    for i, line in enumerate(lines):
        m = re.fullmatch(r'1\s+(\S+)', line)
        code = m and CURRENCIES.get(m.group(1))
        if not code or code in rates:
            continue
        numbers = [int(x) for x in lines[i + 1:i + 8] if re.fullmatch(r'\d{3,5}', x)]
        if len(numbers) >= 2 and all(SANE[code][0] <= n <= SANE[code][1] for n in numbers[:2]):
            rates[code] = {'sell': numbers[0], 'buy': numbers[1]}
    if not day or 'usd' not in rates:
        raise ValueError('Could not find the date and dollar rate on the board')
    return {'date': day, 'time': clock, **rates}

def main(path='rates.json'):
    req = urllib.request.Request(URL, headers={'User-Agent': 'OurHomeRates/1.0 (family budget app; hourly)'})
    board = read_board(urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace'))
    try:
        old = json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError):
        old = {}
    history = {d['date']: d for d in old.get('history', [])}
    history[board['date']] = {'date': board['date'], 'buy': board['usd']['buy'], 'sell': board['usd']['sell']}
    data = {
        'source': 'Saido exchange, Duhok market (saidoco.com/m)',
        'board': board,
        'checked': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'history': sorted(history.values(), key=lambda d: d['date'])[-730:],
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(board)

if __name__ == '__main__':
    main(*sys.argv[1:])
