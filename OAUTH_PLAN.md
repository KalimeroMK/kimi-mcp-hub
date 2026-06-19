# Plan: Avtomatsko Otvoranje na Browser za OAuth

## Shto se pravi
Koga korisnikot ke napravi `kimi-mcp-hub auth github` (ili `add github`),
sistemot avtomatski go otvara browserot i cheka avtorizacija -- kako Claude Code CLI.

## Podrzhani Serveri

| Server | OAuth Tip | Avtomatski Browser |
|--------|-----------|-------------------|
| **GitHub** | Device Flow + Web Flow | Da |
| **Jira** | OAuth 2.0 (PKCE) | Da |
| **Confluence** | OAuth 2.0 (PKCE) | Da |
| **Slack** | OAuth 2.0 | Da |
| **Figma** | OAuth 2.0 | Da |
| **Gmail** | OAuth 2.0 (Google) | Da |
| **Datadog** | API Key (nema OAuth) | Ne |
| **Linear** | API Key (nema OAuth) | Ne |

## Kako Raboti (GitHub primer)

```
$ kimi-mcp-hub auth github

Otvaranje browser za GitHub avtorizacija...
Ako ne se otvori avtomatski, otvori ja ovaa strana:
https://github.com/login/oauth/authorize?...

[spiner] Chekanje na avtorizacija...

Svrzano! GitHub e avtoriziran.
```

### Device Flow (preporachlivo za CLI)
1. CLI prakja POST do GitHub za device code
2. GitHub vrakja: `device_code`, `user_code`, `verification_uri`
3. CLI avtomatski go otvara `verification_uri` vo browser
4. CLI pokazuva `user_code` koj korisnikot treba da go vnesi
5. CLI poll-va GitHub dali e avtorizirano
6. Koga ke e avtorizirano, GitHub vrakja `access_token`

### Web Flow (so localhost callback)
1. Startuva localhost server na random port (callback)
2. Gradite OAuth URL so PKCE
3. Otvora browser avtomatski
4. Korisnikot klika "Authorize"
5. Browser redirect-va na localhost so `?code=...`
6. CLI go zemva kodot i go razmenava za token

## Fajlovi shto ke se menuvaat

1. `src/kimi_mcp_hub/auth/oauth.py` -- dodadi PKCE, GitHub support
2. `src/kimi_mcp_hub/auth/providers.py` -- NOV: site OAuth provideri
3. `src/kimi_mcp_hub/auth/__init__.py` -- export novite klasi
4. `src/kimi_mcp_hub/cli.py` -- `auth` komanda da koristi noviot sistem
5. `src/kimi_mcp_hub/servers/github.py` -- dodadi OAuth config
