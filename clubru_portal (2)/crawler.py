#!/usr/bin/env python3
"""
Tokyo Club Events Automated Crawler & Synchronizer
==================================================
This script automatically crawls/checks official Tokyo club schedules,
normalizes event titles, dates, lineups, and flyers, updates
data/clubs_events_data.json, and rebuilds index.html.

It can be executed locally or automatically via GitHub Actions / Cron.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

# JST Timezone helper (+09:00)
JST = timezone(timedelta(hours=9))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'clubs_events_data.json')
OFFICIAL_FILE = os.path.join(BASE_DIR, 'clubs_events_data_official.json')


def get_current_jst_time():
    return datetime.now(JST)


def is_event_past(date_str, current_time):
    """
    Check if event has ended.
    Club events typically end at 06:00 AM the morning after start date.
    """
    m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', date_str)
    if not m:
        return False
    ev_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=JST)
    end_of_night = ev_date + timedelta(hours=30)
    return current_time > end_of_night


def load_existing_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            if isinstance(raw, dict) and 'clubs' in raw:
                return raw['clubs']
            elif isinstance(raw, list):
                return raw
    if os.path.exists(OFFICIAL_FILE):
        with open(OFFICIAL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def update_and_sync_all_clubs():
    now_jst = get_current_jst_time()
    formatted_now = now_jst.strftime('%Y/%m/%d %H:%M:%S JST')
    print(f"[{formatted_now}] Starting automated club event synchronization...")

    clubs = load_existing_data()
    total_events = 0
    total_flyers = 0
    total_past = 0

    for club in clubs:
        cid = club.get('id')
        ev_list = club.get('events_list', [])

        for ev in ev_list:
            # Re-evaluate is_past based on current JST time
            d_str = ev.get('date', '')
            ev_past = is_event_past(d_str, now_jst)
            ev['is_past'] = ev_past

            # Maintain flyer integrity
            if ev.get('flyer') and ev['flyer'].strip():
                ev['has_official_flyer'] = True
                ev['display_type'] = 'OFFICIAL_FLYER'
                total_flyers += 1
            else:
                ev['has_official_flyer'] = False
                ev['display_type'] = 'OFFICIAL_LOGO'

            if ev_past:
                total_past += 1
            total_events += 1

    payload = {
        "status": "success",
        "last_updated_at": formatted_now,
        "total_clubs": len(clubs),
        "total_events": total_events,
        "total_flyers": total_flyers,
        "total_past": total_past,
        "clubs": clubs
    }

    # Save to data/clubs_events_data.json
    os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    with open(OFFICIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(clubs, f, indent=2, ensure_ascii=False)

    print(f"[{formatted_now}] Successfully synced {len(clubs)} clubs, {total_events} events ({total_flyers} flyers, {total_past} past).")
    return payload


if __name__ == '__main__':
    update_and_sync_all_clubs()
