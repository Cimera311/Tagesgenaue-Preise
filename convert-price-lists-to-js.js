'use strict';

/*
 * Konvertiert die von fill_price_lists_paprika.py erzeugten CSV-Dateien
 * aus data/price_lists/ in einzelne JavaScript-Dateien unter src/scripts/.
 *
 * Verwendung:
 *   node csv_to_js.js
 *
 * Eingabedateien:
 *   data/price_lists/bitcoin_prices.csv
 *   data/price_lists/gomining_prices.csv
 *   data/price_lists/ethereum_prices.csv
 *   data/price_lists/bnb_prices.csv
 *   data/price_lists/solana_prices.csv
 *   data/price_lists/toncoin_prices.csv
 *   data/price_lists/usdt_prices.csv
 *   data/price_lists/usdc_prices.csv
 *
 * Ausgabedateien:
 *   src/scripts/price-data-btc.js
 *   src/scripts/price-data-gmt.js
 *   src/scripts/price-data-eth.js
 *   src/scripts/price-data-bnb.js
 *   src/scripts/price-data-sol.js
 *   src/scripts/price-data-ton.js
 *   src/scripts/price-data-usdt.js
 *   src/scripts/price-data-usdc.js
 */

const fs = require('fs');
const path = require('path');

const INPUT_DIR = path.join(__dirname, 'data', 'price_lists');
const OUTPUT_DIR = path.join(__dirname, 'src', 'scripts');

/*
 * false = Preise bleiben Strings mit deutschem Dezimalkomma,
 *         zum Beispiel "63915,48".
 *
 * true  = price_*-Felder werden zu echten JavaScript-Zahlen,
 *         zum Beispiel 63915.48.
 *
 * Für Berechnungen ist true normalerweise besser.
 * Für maximale Kompatibilität mit deinem alten Format bleibt es hier false.
 */
const PRICE_VALUES_AS_NUMBERS = true;

const FILES = [
  {
    input: 'bitcoin_prices.csv',
    output: 'price-data-btc.js',
    variable: 'btcPriceData',
    label: 'Bitcoin',
  },
  {
    input: 'gomining_prices.csv',
    output: 'price-data-gmt.js',
    variable: 'gmtPriceData',
    label: 'GoMining',
  },
  {
    input: 'ethereum_prices.csv',
    output: 'price-data-eth.js',
    variable: 'ethPriceData',
    label: 'Ethereum',
  },
  {
    input: 'bnb_prices.csv',
    output: 'price-data-bnb.js',
    variable: 'bnbPriceData',
    label: 'BNB',
  },
  {
    input: 'solana_prices.csv',
    output: 'price-data-sol.js',
    variable: 'solPriceData',
    label: 'Solana',
  },
  {
    input: 'toncoin_prices.csv',
    output: 'price-data-ton.js',
    variable: 'tonPriceData',
    label: 'Toncoin',
  },
  {
    input: 'usdt_prices.csv',
    output: 'price-data-usdt.js',
    variable: 'usdtPriceData',
    label: 'Tether',
  },
  {
    input: 'usdc_prices.csv',
    output: 'price-data-usdc.js',
    variable: 'usdcPriceData',
    label: 'USD Coin',
  },
];

function normalizeLineEndings(text) {
  return text
    .replace(/^\uFEFF/, '')
    .replace(/\r\n?/g, '\n');
}

function parsePriceValue(value) {
  if (!PRICE_VALUES_AS_NUMBERS) {
    return value;
  }

  if (value === '') {
    return null;
  }

  const number = Number(value.replace(',', '.'));

  if (!Number.isFinite(number)) {
    throw new Error(`Ungültiger Preiswert: "${value}"`);
  }

  return number;
}

function csvToDateObject(csvFilePath) {
  if (!fs.existsSync(csvFilePath)) {
    throw new Error(`CSV-Datei nicht gefunden: ${csvFilePath}`);
  }

  const csvContent = normalizeLineEndings(
    fs.readFileSync(csvFilePath, 'utf8')
  ).trim();

  if (!csvContent) {
    throw new Error(`CSV-Datei ist leer: ${csvFilePath}`);
  }

  const lines = csvContent
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean);

  if (lines.length < 2) {
    throw new Error(`CSV enthält keine Datenzeilen: ${csvFilePath}`);
  }

  const headers = lines[0]
    .split(';')
    .map(header => header.trim());

  const requiredHeaders = [
    'date_iso',
    'time_berlin',
    'symbol',
    'price_usd',
  ];

  for (const requiredHeader of requiredHeaders) {
    if (!headers.includes(requiredHeader)) {
      throw new Error(
        `Pflichtspalte "${requiredHeader}" fehlt in ${csvFilePath}`
      );
    }
  }

  const data = {};

  for (let lineIndex = 1; lineIndex < lines.length; lineIndex += 1) {
    const values = lines[lineIndex]
      .split(';')
      .map(value => value.trim());

    if (values.length !== headers.length) {
      throw new Error(
        `Spaltenanzahl stimmt nicht in ${path.basename(csvFilePath)}, ` +
        `Zeile ${lineIndex + 1}: ` +
        `erwartet ${headers.length}, erhalten ${values.length}`
      );
    }

    const row = {};

    headers.forEach((header, columnIndex) => {
      const value = values[columnIndex] ?? '';

      row[header] = header.startsWith('price_')
        ? parsePriceValue(value)
        : value;
    });

    const date = row.date_iso;

    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      throw new Error(
        `Ungültiges date_iso in ${path.basename(csvFilePath)}, ` +
        `Zeile ${lineIndex + 1}: "${date}"`
      );
    }

    /*
     * Falls ein Datum doppelt vorhanden ist,
     * gewinnt die zuletzt gelesene Zeile.
     */
    data[date] = row;
  }

  /*
   * Garantiert chronologische Reihenfolge
   * im erzeugten JavaScript-Objekt.
   */
  return Object.fromEntries(
    Object.entries(data).sort(
      ([dateA], [dateB]) => dateA.localeCompare(dateB)
    )
  );
}

function buildJsContent(variableName, data, sourceFilename) {
  const generatedAt = new Date().toISOString();

  return (
    `// Auto-generiert am ${generatedAt}\n` +
    `// Quelle: data/price_lists/${sourceFilename}\n` +
    `// Nicht manuell bearbeiten – stattdessen CSV neu konvertieren.\n\n` +

    `const ${variableName} = ${JSON.stringify(data, null, 2)};\n\n` +

    `if (typeof globalThis !== 'undefined') {\n` +
    `  globalThis.${variableName} = ${variableName};\n` +
    `}\n\n` +

    `if (typeof module !== 'undefined' && module.exports) {\n` +
    `  module.exports = ${variableName};\n` +
    `}\n`
  );
}

function convertCsvToJs() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  let converted = 0;
  let skipped = 0;
  let failed = 0;

  for (const file of FILES) {
    const inputPath = path.join(INPUT_DIR, file.input);
    const outputPath = path.join(OUTPUT_DIR, file.output);

    if (!fs.existsSync(inputPath)) {
      console.warn(
        `⚠️  ${file.label}: ${file.input} fehlt – übersprungen`
      );

      skipped += 1;
      continue;
    }

    try {
      const data = csvToDateObject(inputPath);

      const jsContent = buildJsContent(
        file.variable,
        data,
        file.input
      );

      fs.writeFileSync(
        outputPath,
        jsContent,
        'utf8'
      );

      console.log(
        `✅ ${file.label}: ` +
        `${Object.keys(data).length} Tage → ` +
        `${path.relative(__dirname, outputPath)}`
      );

      converted += 1;
    } catch (error) {
      console.error(
        `❌ ${file.label}: ${error.message}`
      );

      failed += 1;
    }
  }

  console.log(
    `\nFertig: ` +
    `${converted} konvertiert, ` +
    `${skipped} übersprungen, ` +
    `${failed} Fehler.`
  );

  if (failed > 0 || converted === 0) {
    process.exitCode = 1;
  }
}

convertCsvToJs();