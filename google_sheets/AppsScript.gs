/**
 * Append BTC & GoMining EUR prices to a "prices" sheet at 00:00 Europe/Berlin.
 * - Set file timezone to Europe/Berlin (File → Spreadsheet settings).
 * - Create an installable time-based trigger at 00:00.
 * - Idempotent by date: skips if today's date exists.
 */
const COINS = [
  { id: "bitcoin", paprikaId: "btc-bitcoin", symbol: "BTC" },
  { id: "gomining-token", paprikaId: "gmt-gomining-token", symbol: "GOMINING" },
];
const VS = "eur";
const SHEET_NAME = "prices";

function appendDailyPrices() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const tz = ss.getSpreadsheetTimeZone() || "Europe/Berlin";
  const today = Utilities.formatDate(new Date(), tz, "yyyy-MM-dd");
  const sh = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);

  // header
  if (sh.getLastRow() === 0) {
    sh.appendRow(["date_iso", "symbol", "price_eur"]);
  }

  // read existing dates to avoid duplicates
  const lastRow = sh.getLastRow();
  if (lastRow > 1) {
    const dates = sh.getRange(2, 1, lastRow - 1, 1).getValues().flat();
    if (dates.includes(today)) {
      Logger.log("Skip: date already exists " + today);
      return;
    }
  }

  const cg = fetchCoinGeckoSimple(COINS.map(c => c.id));
  COINS.forEach(c => {
    let price = null;
    if (cg && cg[c.id] && cg[c.id][VS] != null) {
      price = Number(cg[c.id][VS]);
    } else {
      price = fetchPaprikaEUR(c.paprikaId);
    }
    if (price == null) return;
    sh.appendRow([today, c.symbol, Number(price)]);
  });
}

/** Fetch simple price from CoinGecko (no API key) */
function fetchCoinGeckoSimple(ids) {
  try {
    const url = "https://api.coingecko.com/api/v3/simple/price?ids=" +
      encodeURIComponent(ids.join(",")) + "&vs_currencies=" + VS;
    const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true, headers: { "accept": "application/json" } });
    if (res.getResponseCode() >= 200 && res.getResponseCode() < 300) {
      return JSON.parse(res.getContentText());
    }
  } catch (e) {}
  return null;
}

/** Fallback to Coinpaprika */
function fetchPaprikaEUR(id) {
  try {
    const url = "https://api.coinpaprika.com/v1/tickers/" + id;
    const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true, headers: { "accept": "application/json" } });
    if (res.getResponseCode() >= 200 && res.getResponseCode() < 300) {
      const data = JSON.parse(res.getContentText());
      return data && data.quotes && data.quotes.EUR ? data.quotes.EUR.price : null;
    }
  } catch (e) {}
  return null;
}

/** One-time helper to create a daily 00:00 trigger in the sheet's timezone */
function createMidnightTrigger() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const tz = ss.getSpreadsheetTimeZone() || "Europe/Berlin";
  // Clean old triggers for this function
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === "appendDailyPrices")
    .forEach(t => ScriptApp.deleteTrigger(t));

  ScriptApp.newTrigger("appendDailyPrices")
    .timeBased()
    .everyDays(1)
    .atHour(0)        // midnight
    .inTimezone(tz)   // ensure 00:00 local
    .create();
  SpreadsheetApp.getUi().alert("Trigger created for 00:00 " + tz);
}
