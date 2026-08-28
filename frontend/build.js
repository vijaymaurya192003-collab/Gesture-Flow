/**
 * Build script: Copies static web assets into Capacitor www and Android native assets
 */
const fs = require('fs');
const path = require('path');

const srcDir = __dirname;
const wwwDir = path.join(__dirname, 'www');
const androidPublicDir = path.join(__dirname, 'android', 'app', 'src', 'main', 'assets', 'public');

[wwwDir, androidPublicDir].forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

const filesToCopy = ['index.html', 'style.css', 'api.js', 'app.js', 'vercel.json', 'logo.png', 'favicon.png'];

filesToCopy.forEach(file => {
  const src = path.join(srcDir, file);
  if (fs.existsSync(src)) {
    // Copy to www/
    fs.copyFileSync(src, path.join(wwwDir, file));
    console.log(`Copied ${file} -> www/${file}`);

    // Copy to Android native assets if android folder exists
    if (fs.existsSync(androidPublicDir)) {
      fs.copyFileSync(src, path.join(androidPublicDir, file));
      console.log(`Copied ${file} -> android/.../public/${file}`);
    }
  }
});

// Copy assets folder
const assetsSrc = path.join(srcDir, 'assets');
if (fs.existsSync(assetsSrc)) {
  const wwwAssets = path.join(wwwDir, 'assets');
  const androidAssets = path.join(androidPublicDir, 'assets');
  [wwwAssets, androidAssets].forEach(dir => {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  });

  fs.readdirSync(assetsSrc).forEach(item => {
    const s = path.join(assetsSrc, item);
    fs.copyFileSync(s, path.join(wwwAssets, item));
    if (fs.existsSync(androidPublicDir)) {
      fs.copyFileSync(s, path.join(androidAssets, item));
    }
    console.log(`Copied assets/${item} -> www & android`);
  });
}

console.log('Build complete! Static assets and logo files synchronized to www and Android native assets.');

