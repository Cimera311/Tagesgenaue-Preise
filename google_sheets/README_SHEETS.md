# Google Sheets price logger (00:00 MEZ)

1) Neues Google Sheet anlegen → **Datei → Einstellungen**: Zeitzone **Europe/Berlin** setzen.
2) **Erweiterungen → Apps Script** öffnen, Inhalt von `AppsScript.gs` einfügen.
3) Speichern → `createMidnightTrigger()` einmal ausführen (Berechtigungen bestätigen).
   - Erstellt einen täglichen Trigger **00:00** in Berlin‑Zeitzone.
4) Beim ersten Lauf wird das Sheet `prices` mit Header angelegt.
5) Idempotent: Wenn der heutige Tag schon existiert, wird nichts doppelt angehängt.

Spalten: `date_iso, symbol, price_eur`
Coins: BTC, GoMining (anpassbar in `COINS`).
