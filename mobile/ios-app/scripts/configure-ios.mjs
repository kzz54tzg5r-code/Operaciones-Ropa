import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const plistPath = path.join(root, 'ios', 'App', 'App', 'Info.plist');

if (!fs.existsSync(plistPath)) {
  console.error('No existe ios/App/App/Info.plist. Ejecuta primero: npx cap add ios');
  process.exit(1);
}

let plist = fs.readFileSync(plistPath, 'utf8');

const values = [
  ['CFBundleDisplayName', '<string>Operaciones Ropa</string>'],
  ['NSCameraUsageDescription', '<string>Operaciones Ropa usa la cámara para adjuntar evidencias operativas.</string>'],
  ['NSPhotoLibraryUsageDescription', '<string>Operaciones Ropa usa tu fototeca para seleccionar evidencias operativas.</string>'],
  ['NSPhotoLibraryAddUsageDescription', '<string>Operaciones Ropa puede guardar evidencias generadas desde la aplicación.</string>'],
  ['ITSAppUsesNonExemptEncryption', '<false/>']
];

for (const [key, value] of values) {
  if (plist.includes('<key>' + key + '</key>')) continue;
  plist = plist.replace(
    '</dict>\n</plist>',
    '  <key>' + key + '</key>\n  ' + value + '\n</dict>\n</plist>'
  );
}

fs.writeFileSync(plistPath, plist, 'utf8');
console.log('Info.plist preparado para Operaciones Ropa iOS.');
