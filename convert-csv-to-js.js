const fs = require('fs');
const path = require('path');

function csvToJson(csvFilePath) {
    const csvContent = fs.readFileSync(csvFilePath, 'utf-8');
    const lines = csvContent.trim().split('\n');
    const headers = lines[0].split(';');
    
    const data = {};
    
    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(';');
        const date = values[0];
        
        data[date] = {
            date_iso: values[0],
            time_berlin: values[1],
            symbol: values[2],
            price_eur: values[3],
            price_usd: values[4]
        };
    }
    
    return data;
}

function convertCsvToJs() {
    // Erstelle src/scripts Verzeichnis falls nicht vorhanden
    const outputDir = path.join(__dirname, 'src', 'scripts');
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }
    
    // Bitcoin konvertieren
    const btcData = csvToJson(path.join(__dirname, 'data', 'bitcoin_eur.csv'));
    const btcJsContent = `// Auto-generiert am ${new Date().toISOString()}\nconst btcPriceData = ${JSON.stringify(btcData, null, 2)};\n\nif (typeof module !== 'undefined' && module.exports) {\n  module.exports = btcPriceData;\n}`;
    fs.writeFileSync(path.join(outputDir, 'price-data-btc.js'), btcJsContent);
    console.log('✅ Bitcoin Preisdaten konvertiert');
    
    // GoMining konvertieren
    const gmtData = csvToJson(path.join(__dirname, 'data', 'gominingtoken_eur.csv'));
    const gmtJsContent = `// Auto-generiert am ${new Date().toISOString()}\nconst gmtPriceData = ${JSON.stringify(gmtData, null, 2)};\n\nif (typeof module !== 'undefined' && module.exports) {\n  module.exports = gmtPriceData;\n}`;
    fs.writeFileSync(path.join(outputDir, 'price-data-gmt.js'), gmtJsContent);
    console.log('✅ GoMining Preisdaten konvertiert');
}

// Script ausführen
convertCsvToJs();