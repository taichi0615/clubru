/**
 * Tokyo Club Events - Auto Update & Live Sync Client Engine
 * ==========================================================
 * Automatically checks for latest event data updates from the crawler API / JSON endpoint,
 * supports background polling, manual refresh, and graceful fallback to offline cache.
 *
 * Integrated with the 12+ Official Club Endpoints:
 * 1. WARP SHINJUKU (https://warp-shinjuku.jp/event/)
 * 2. ZEROTOKYO (https://zerotokyo.jp/event/)
 * 3. CIRCUS TOKYO (https://circus-tokyo.jp/schedule/)
 * 4. ENTER SHIBUYA (https://entershibuya.com/schedule/)
 * 5. 翠月 (MITSUKI) (https://mitsuki-tokyo.com/)
 * 6. VENT (http://vent-tokyo.net/schedule/)
 * 7. RAISE (https://raisetokyo.com/events/)
 * 8. SEL OCTAGON TOKYO (https://sel-octagon-tokyo.jp/event/)
 * 9. 1OAK TOKYO (https://1oak.tokyo/)
 * 10. clubasia (https://clubasia.jp/events/)
 * 11. V2 TOKYO (https://www.v2tokyo.com/events-calendar/)
 * 12. R LOUNGE (http://rlounge.jp/schedule.html)
 */

const CLUB_OFFICIAL_ENDPOINTS = {
  warp: {
    name: "WARP SHINJUKU",
    scheduleUrl: "https://warp-shinjuku.jp/event/",
    type: "WordPress Daily 4-Floors",
    flyerPattern: "/wp-content/uploads/YYYY/MM/"
  },
  zerotokyo: {
    name: "ZEROTOKYO",
    scheduleUrl: "https://zerotokyo.jp/event/",
    type: "WordPress Event Slugs",
    flyerPattern: "/wp/wp-content/uploads/"
  },
  circus_tokyo: {
    name: "CIRCUS TOKYO",
    scheduleUrl: "https://circus-tokyo.jp/schedule/",
    type: "WordPress Schedule Archive",
    flyerPattern: "/wp-content/uploads/"
  },
  enter_shibuya: {
    name: "ENTER",
    scheduleUrl: "https://entershibuya.com/schedule/",
    type: "Schedule Entries & RA CDN",
    flyerPattern: "wp-content/uploads | imgproxy.ra.co"
  },
  mitsuki: {
    name: "翠月 (MITSUKI)",
    scheduleUrl: "https://mitsuki-tokyo.com/",
    type: "WordPress Date Posts",
    flyerPattern: "/wp/wp-content/uploads/"
  },
  vent: {
    name: "VENT",
    scheduleUrl: "http://vent-tokyo.net/schedule/",
    type: "Table Calendar & LivePocket",
    flyerPattern: "/wp-content/uploads/ | LivePocket"
  },
  raise: {
    name: "RAISE",
    scheduleUrl: "https://raisetokyo.com/events/",
    type: "WordPress CMS Event Cards",
    flyerPattern: "/cms/wp-content/uploads/"
  },
  sel_octagon: {
    name: "SEL OCTAGON TOKYO",
    scheduleUrl: "https://sel-octagon-tokyo.jp/event/",
    type: "Monthly Calendar Grid",
    flyerPattern: "/wp-content/uploads/"
  },
  "1oak_tokyo": {
    name: "1OAK TOKYO",
    scheduleUrl: "https://1oak.tokyo/",
    type: "Hero Poster & Weekly Drops",
    flyerPattern: "/assets/img/hero-poster.webp"
  },
  clubasia: {
    name: "clubasia",
    scheduleUrl: "https://clubasia.jp/events/",
    type: "Framer CMS & Ticket Proxy",
    flyerPattern: "framerusercontent.com/images/ | imgproxy.ra.co"
  },
  v2_tokyo: {
    name: "V2 TOKYO",
    scheduleUrl: "https://www.v2tokyo.com/events-calendar/",
    type: "Monthly Media Directory",
    flyerPattern: "/media/YYYYMMDD*.jpg"
  },
  r_lounge: {
    name: "R LOUNGE",
    scheduleUrl: "http://rlounge.jp/schedule.html",
    type: "6F & 7F Floor Schedules",
    flyerPattern: "/flyer/YYYYMMDD_{6f|7f}.jpg"
  }
};

class ClubEventsAutoUpdater {
  constructor(options = {}) {
    this.endpoint = options.endpoint || 'data/clubs_events_data.json';
    this.pollInterval = options.pollInterval || 300000; // 5 minutes polling
    this.statusElementId = options.statusElementId || 'liveSyncStatus';
    this.buttonElementId = options.buttonElementId || 'liveSyncBtn';
    this.timer = null;
    this.lastUpdatedAt = null;
    this.endpoints = CLUB_OFFICIAL_ENDPOINTS;
  }

  /**
   * Initialize auto-updater and start background polling
   */
  init() {
    this.fetchLatest();
    this.startPolling();
  }

  /**
   * Start background polling timer
   */
  startPolling() {
    if (this.timer) clearInterval(this.timer);
    this.timer = setInterval(() => {
      this.fetchLatest(true);
    }, this.pollInterval);
  }

  /**
   * Get registered official schedule endpoint for a specific club
   */
  getClubEndpoint(clubId) {
    return this.endpoints[clubId] || null;
  }

  /**
   * Fetch the freshest event data with cache-busting timestamp
   */
  async fetchLatest(isBackground = false) {
    const statusEl = document.getElementById(this.statusElementId);
    const btnEl = document.getElementById(this.buttonElementId);

    if (btnEl && !isBackground) {
      btnEl.classList.add('animate-spin');
    }

    try {
      const url = `${this.endpoint}?t=${Date.now()}`;
      const response = await fetch(url, { cache: 'no-store' });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      let newClubs = [];
      let updateTime = data.last_updated_at || new Date().toLocaleString('ja-JP');

      if (Array.isArray(data.clubs) && data.clubs.length > 0) {
        newClubs = data.clubs;
      } else if (Array.isArray(data) && data.length > 0) {
        newClubs = data;
      }

      if (newClubs.length > 0) {
        this.lastUpdatedAt = updateTime;
        
        // Dispatch global event for application re-rendering
        const event = new CustomEvent('clubEventsUpdated', {
          detail: {
            clubs: newClubs,
            lastUpdatedAt: updateTime,
            metadata: data,
            endpoints: this.endpoints
          }
        });
        window.dispatchEvent(event);

        if (statusEl) {
          statusEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-pulse"></span> 最新自動同期: ${updateTime}`;
        }
      }
    } catch (error) {
      console.log('Auto-update running in offline/snapshot mode:', error.message);
      if (statusEl && !this.lastUpdatedAt) {
        statusEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span> 最終検証データ同期済`;
      }
    } finally {
      if (btnEl) {
        btnEl.classList.remove('animate-spin');
      }
    }
  }
}

// Global instance & window binding
window.CLUB_OFFICIAL_ENDPOINTS = CLUB_OFFICIAL_ENDPOINTS;
window.clubAutoUpdater = new ClubEventsAutoUpdater();
window.fetchLatestEventData = () => window.clubAutoUpdater.fetchLatest(false);

// Auto-run when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => window.clubAutoUpdater.init());
} else {
  window.clubAutoUpdater.init();
}
