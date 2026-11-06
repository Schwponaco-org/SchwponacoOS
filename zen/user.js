// Zen settings, applied on every start (they override anything changed in Settings meanwhile).
// Linked into the profile by zen/install.sh. Every session starts clean: private browsing, no history,
// everything cleared on exit.

// --- Sessions: nothing carries over ---------------------------------------------------------------
user_pref("browser.privatebrowsing.autostart", true);       // always private browsing
user_pref("places.history.enabled", false);
user_pref("privacy.sanitize.sanitizeOnShutdown", true);
user_pref("privacy.clearOnShutdown_v2.formdata", true);
user_pref("signon.rememberSignons", false);                  // no saved passwords
user_pref("signon.autofillForms", false);
user_pref("signon.generation.enabled", false);
user_pref("signon.firefoxRelay.feature", "disabled");
user_pref("signon.management.page.breach-alerts.enabled", false);
user_pref("extensions.formautofill.creditCards.enabled", false);

// --- Tracking and fingerprinting ------------------------------------------------------------------
user_pref("privacy.trackingprotection.enabled", true);
user_pref("privacy.trackingprotection.socialtracking.enabled", true);
user_pref("privacy.trackingprotection.emailtracking.enabled", true);
user_pref("privacy.trackingprotection.allow_list.convenience.enabled", false);
user_pref("privacy.trackingprotection.consentmanager.skip.pbmode.enabled", false);
user_pref("privacy.annotate_channels.strict_list.enabled", true);
user_pref("privacy.fingerprintingProtection", true);
user_pref("privacy.bounceTrackingProtection.mode", 1);
user_pref("privacy.query_stripping.enabled", true);         // strip tracking parameters from links
user_pref("privacy.query_stripping.enabled.pbmode", true);
user_pref("network.http.referer.disallowCrossSiteRelaxingDefault.top_navigation", true);

// --- Network --------------------------------------------------------------------------------------
user_pref("dom.security.https_only_mode", true);
user_pref("network.trr.mode", 3);                             // encrypted DNS only, no fallback
user_pref("network.trr.uri", "https://mozilla.cloudflare-dns.com/dns-query");
user_pref("network.dns.disablePrefetch", true);              // no connections to pages you haven't opened
user_pref("network.prefetch-next", false);
user_pref("network.http.speculative-parallel-limit", 0);

// --- Address bar: suggest searches, never your own browsing --------------------------------------
user_pref("browser.search.suggest.enabled", true);
user_pref("browser.search.suggest.enabled.private", true);
user_pref("browser.urlbar.suggest.history", false);
user_pref("browser.urlbar.suggest.bookmark", false);
user_pref("browser.urlbar.suggest.openpage", false);
user_pref("browser.urlbar.suggest.engines", false);
user_pref("browser.urlbar.suggest.clipboard", false);
user_pref("browser.urlbar.suggest.recentsearches", false);

// --- Look and behaviour ---------------------------------------------------------------------------
user_pref("zen.view.compact.enable-at-startup", true);
user_pref("zen.view.window.scheme", 0);
user_pref("layout.css.prefers-color-scheme.content-override", 0);   // dark pages
user_pref("sidebar.visibility", "hide-launcher");
user_pref("browser.toolbars.bookmarks.visibility", "never");       // nothing slides in at the top edge
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.bookmarks.restore_default_bookmarks", false);
user_pref("browser.translations.automaticallyPopup", false);
user_pref("browser.translations.neverTranslateLanguages", "da");
user_pref("layout.spellcheckDefault", 0);

// No trackpad swipe gestures: back/forward, the arrow that slides in, and Zen's swipe between spaces
user_pref("browser.gesture.swipe.left", "");
user_pref("browser.gesture.swipe.right", "");
user_pref("widget.disable-swipe-tracker", true);
user_pref("zen.workspaces.swipe-actions", false);
