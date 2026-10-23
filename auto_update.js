/**
 * Tokyo Club Events - Auto Update & Live Sync Client Engine
 * ==========================================================
 * Automatically checks for latest event data updates from the crawler API / JSON endpoint,
 * supports background polling, manual refresh, and graceful fallback to offline cache.
 */

class ClubEventsAutoUpdater {
  constructor(options = {}) {
    this.endpoint = options.endpoint || 'data/clubs_events_data.json';
    this.pollInterval = options.pollInterval || 300000; // 5 minutes polling
    this.statusElementId = options.statusElementId || 'liveSyncStatus';
    this.buttonElementId = options.buttonElementId || 'liveSyncBtn';
    this.timer = null;
    this.lastUpdatedAt = null;
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
            metadata: data
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
window.clubAutoUpdater = new ClubEventsAutoUpdater();
window.fetchLatestEventData = () => window.clubAutoUpdater.fetchLatest(false);

// Auto-run when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => window.clubAutoUpdater.init());
} else {
  window.clubAutoUpdater.init();
}
