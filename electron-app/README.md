# FIT Expo Demo - Desktop App

## Build Instructions

### 1. Install Dependencies
```bash
npm install
```

### 2. Test the App Locally
```bash
npm start
```

### 3. Build Windows Executable
```bash
npm run build
```

The Windows installer will be created in the `dist` folder as `FIT Expo Demo Setup 1.0.0.exe`

### 4. Distribute
Send the `.exe` file from the `dist` folder to your user. They just need to:
1. Double-click the installer
2. Follow the installation wizard
3. Launch "FIT Expo Demo" from their desktop or Start menu

## Notes
- The app includes the HTTP API configuration and will work without HTTPS issues
- No browser required - it's a standalone desktop application
- Works on Windows 10/11
