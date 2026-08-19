# MerzoStream Suite 0.1.0p

Cumulative Chat Core 3.0 and service integration repair.

- Unified Chat: real message composer and `chat_send` backend route.
- YouTube: direct OAuth live-chat adapter with active and upcoming broadcast discovery, receive and send.
- VK Видео Live: restored user-facing browser login without developer App ID / Client Secret fields; direct chat receive/send adapter.
- DonationAlerts: Secret Token realtime connector for widget-style token flow, while keeping OAuth support for Public API scenarios.
- Streamer.bot: outgoing message transport retained as fallback/integration, not the only chat foundation.
- Preserves 0.1.0o OBS/UI/installer changes and the dark Program Files installer with LocalAppData WebView2 profile.

## Acceptance focus

Verify Twitch, YouTube and VK chat receive/send independently, YouTube prepared/upcoming stream discovery, VK login persistence, and DonationAlerts Secret Token realtime events. Provider-side live acceptance still requires testing with the user's actual accounts/tokens; CI validates compilation and static contracts, not third-party account availability.
