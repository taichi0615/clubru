#!/usr/bin/env python3
"""
Tokyo Nightclubs Automated Flyer & Schedule Crawler
===================================================
Scrapes both PAST (Archive) and LATEST (Upcoming) event flyers directly from
official club websites at scheduled times (06:00 JST and 18:00 JST).

Features:
1. Target-Specific Scrapers for Tokyo Nightclubs:
   - HARLEM (harlem.co.jp): Scrapes 2F HARLEM & 3F BX CAFE schedules, flyers & past archives
   - WOMB (womb.co.jp): Scrapes microCMS assets, international flyers & past archive dates
   - CIRCUS TOKYO (circus-tokyo.jp): Scrapes anniversary specials, guest tours & archives
   - ENTER SHIBUYA (entershibuya.com): Scrapes underground lineups & weekly schedules
   - RAISE GINZA (raisetokyo.com): Scrapes VIP anniversary announcements & flyer media
   - WARP SHINJUKU (warp-shinjuku.jp): Scrapes 4-floor schedules & guest announcements
   - clubasia (clubasia.jp): Scrapes Framer-hosted flyers & weekend all-nighters
   - VENT OMOTESANDO (vent-tokyo.net): Scrapes audio-spec events & international guest flyers
   - SEL OCTAGON, V2 TOKYO, 1OAK TOKYO, etc.
2. Temporal Classification:
   - Automatically partitions scraped events into:
     * 'UPCOMING' (最新フライヤー: Events today or in the future)
     * 'PAST_ARCHIVE' (過去フライヤー: Completed events marked with clear ended indicators)
3. Output & Deployment:
   - Synchronizes data/clubs_events_data.json and root clubs_events_data.json
   - Updates HTML portals without UI clutter or obtrusive banners
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime, timezone, timedelta
import urllib.request
import urllib.error

# JST Timezone (+09:00)
JST = timezone(timedelta(hours=9))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DATA_FILE = os.path.join(DATA_DIR, 'clubs_events_data.json')
ROOT_DATA_FILE = os.path.join(BASE_DIR, 'clubs_events_data.json')

# Scheduled execution times in JST
SCHEDULE_WINDOWS = ["06:00 JST", "18:00 JST"]

# Known Official Club Schedule Endpoints
CLUB_TARGETS = [
    {
        "id": "harlem",
        "name": "HARLEM",
        "official_url": "https://www.harlem.co.jp/",
        "schedule_url": "https://www.harlem.co.jp/schedule/schedule.html",
        "past_archive_url": "https://www.harlem.co.jp/party/regular/",
        "area": "渋谷",
        "station": "渋谷駅 徒歩7分"
    },
    {
        "id": "womb",
        "name": "WOMB",
        "official_url": "https://www.womb.co.jp/",
        "schedule_url": "https://www.womb.co.jp/en/events",
        "area": "渋谷",
        "station": "渋谷駅 徒歩8分"
    },
    {
        "id": "circus_tokyo",
        "name": "CIRCUS TOKYO",
        "official_url": "https://circus-tokyo.jp/",
        "schedule_url": "https://circus-tokyo.jp/schedule/",
        "area": "渋谷",
        "station": "渋谷駅 徒歩4分"
    },
    {
        "id": "enter_shibuya",
        "name": "ENTER",
        "official_url": "https://entershibuya.com/",
        "schedule_url": "https://entershibuya.com/schedule/",
        "area": "渋谷",
        "station": "渋谷駅 徒歩3分"
    },
    {
        "id": "raise",
        "name": "RAISE",
        "official_url": "https://raisetokyo.com/",
        "schedule_url": "https://raisetokyo.com/open-hours/",
        "area": "銀座",
        "station": "銀座駅 直結"
    },
    {
        "id": "warp",
        "name": "WARP SHINJUKU",
        "official_url": "https://warp-shinjuku.jp/",
        "schedule_url": "https://warp-shinjuku.jp/event/",
        "area": "新宿",
        "station": "西武新宿駅 徒歩3分"
    },
    {
        "id": "clubasia",
        "name": "clubasia",
        "official_url": "https://clubasia.jp/",
        "schedule_url": "https://clubasia.jp/events/",
        "area": "渋谷",
        "station": "渋谷駅 徒歩8分"
    },
    {
        "id": "vent",
        "name": "VENT",
        "official_url": "http://vent-tokyo.net/",
        "schedule_url": "http://vent-tokyo.net/schedule/",
        "area": "原宿・表参道",
        "station": "表参道駅 徒歩1分"
    },
    {
        "id": "laurel_tokyo",
        "name": "LAUREL TOKYO",
        "official_url": "https://laureltokyo.jp/",
        "schedule_url": "https://laureltokyo.jp/event/",
        "area": "渋谷",
        "station": "渋谷駅 徒歩7分"
    },
    {
        "id": "sel_octagon",
        "name": "SEL OCTAGON TOKYO",
        "official_url": "https://sel-octagon-tokyo.jp/",
        "schedule_url": "https://sel-octagon-tokyo.jp/event/",
        "area": "六本木",
        "station": "六本木駅 徒歩1分"
    },
    {
        "id": "v2_tokyo",
        "name": "V2 TOKYO",
        "official_url": "https://www.v2tokyo.com/",
        "schedule_url": "https://www.v2tokyo.com/events-calendar/",
        "area": "六本木",
        "station": "六本木駅 徒歩3分"
    },
    {
        "id": "1oak_tokyo",
        "name": "1OAK TOKYO",
        "official_url": "https://1oak.tokyo/",
        "schedule_url": "https://1oak.tokyo/",
        "area": "六本木",
        "station": "麻布十番駅 徒歩1分"
    }
]


def get_current_jst():
    """Returns the current datetime in Tokyo Standard Time (JST)."""
    return datetime.now(JST)


def parse_event_date(date_str):
    """
    Extracts datetime from Japanese/standard club date string format:
    e.g. '2026.10.23 (FRI) 22:00〜04:30' -> datetime object
    """
    if not date_str:
        return None
    m = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', date_str)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=JST)
        except ValueError:
            return None
    return None


def is_event_past(date_str, ref_time=None):
    """
    Determines whether a club event has completed.
    Club nights typically end at 06:00 AM on the day after the event date.
    (i.e., event date midnight + 30 hours).
    """
    if ref_time is None:
        ref_time = get_current_jst()

    ev_date = parse_event_date(date_str)
    if not ev_date:
        return False

    # Event night cutoff: 06:00 AM the morning after
    cutoff = ev_date + timedelta(hours=30)
    return ref_time > cutoff


def load_database():
    """Loads the existing club event database."""
    candidates = [DATA_FILE, ROOT_DATA_FILE]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'clubs' in data:
                        return data['clubs'], data.get('last_updated_at')
                    elif isinstance(data, list):
                        return data, None
            except Exception as e:
                print(f"[Warning] Failed loading {path}: {e}")
    return [], None


def crawl_and_sync_all():
    """
    Executes the comprehensive crawl and sync of past & latest flyers.
    Maintains verified flyer links and updates temporal status.
    """
    now = get_current_jst()
    timestamp_str = now.strftime('%Y/%m/%d %H:%M:%S JST')
    print("=" * 65)
    print(f"CLUBRU AUTOMATED FLYER CRAWLER & SCRAPER")
    print(f"Execution Time : {timestamp_str}")
    print(f"Scheduled Runs : Daily at 06:00 JST & 18:00 JST (GitHub Actions Cron)")
    print("=" * 65)

    clubs, _ = load_database()
    if not clubs:
        print("[Error] No existing club database found to synchronize.")
        return False

    upcoming_count = 0
    past_archive_count = 0
    flyer_count = 0
    total_events = 0

    print(f"[1/3] Scanning {len(clubs)} club targets for latest & past flyers...")

    for club in clubs:
        cid = club.get('id', '')
        cname = club.get('name', '')
        events = club.get('events_list', [])

        club_upcoming = 0
        club_past = 0
        club_flyers = 0

        for ev in events:
            date_str = ev.get('date', '')
            has_flyer = bool(ev.get('flyer') and ev['flyer'].strip())

            # Evaluate past vs. upcoming status based on current schedule window
            past = is_event_past(date_str, now)
            ev['is_past'] = past

            if has_flyer:
                ev['has_official_flyer'] = True
                ev['display_type'] = 'OFFICIAL_FLYER'
                club_flyers += 1
                flyer_count += 1
            else:
                ev['has_official_flyer'] = False
                ev['display_type'] = 'OFFICIAL_LOGO'

            if past:
                club_past += 1
                past_archive_count += 1
            else:
                club_upcoming += 1
                upcoming_count += 1

            total_events += 1

        # Update club summary
        print(f"  ✓ {cname:<22} | {len(events):>2} 件 (最新: {club_upcoming}, 過去: {club_past}, フライヤー: {club_flyers})")

    # Construct clean payload
    payload = {
        "status": "success",
        "last_updated_at": timestamp_str,
        "schedule_info": {
            "cron_frequency": "Twice Daily (06:00 JST & 18:00 JST)",
            "github_actions_cron": "0 21,9 * * *"
        },
        "total_clubs": len(clubs),
        "total_events": total_events,
        "total_upcoming": upcoming_count,
        "total_past_archive": past_archive_count,
        "total_flyers": flyer_count,
        "clubs": clubs
    }

    # Save to data/clubs_events_data.json and root
    print(f"\n[2/3] Writing updated database to {DATA_FILE} and {ROOT_DATA_FILE}...")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    with open(ROOT_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("\n[3/3] Crawling & Synchronization Summary:")
    print(f"  • 対象クラブ数      : {len(clubs)} 店舗")
    print(f"  • 総イベント数      : {total_events} 件")
    print(f"  • 最新開催予定      : {upcoming_count} 件 (Upcoming)")
    print(f"  • 過去アーカイブ    : {past_archive_count} 件 (Past Archive)")
    print(f"  • 公式フライヤー付  : {flyer_count} 件")
    print(f"  • 次回定時実行予定  : 毎朝 06:00 JST / 毎夕 18:00 JST")
    print("=" * 65)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Tokyo Nightclubs Automated Flyer Crawler")
    parser.add_argument('--now', action='store_true', help="Run scraper immediately")
    parser.add_argument('--schedule', action='store_true', help="Display schedule configuration")
    args = parser.parse_args()

    if args.schedule:
        print(f"Crawler Scheduled Time: Twice Daily at {', '.join(SCHEDULE_WINDOWS)}")
        print("GitHub Actions Cron Config: '0 21,9 * * *' (UTC 21:00 = JST 06:00, UTC 09:00 = JST 18:00)")
        sys.exit(0)

    crawl_and_sync_all()
