# Android APK Build Guide

## ✅ Your APK is Ready!

**Location:** `/Users/andyayas/Desktop/DietSimulator.apk`

### 📱 Install on Android Tablet

1. Transfer `DietSimulator.apk` to your Android tablet (via USB, email, or cloud storage)
2. On your tablet, enable "Install from Unknown Sources" in Settings
3. Tap the APK file and install
4. Open "Diet Simulator" app

### 🔄 Rebuild APK After Changes

If you modify `index.html`, rebuild the APK:

```bash
# 1. Copy updated files to www folder
cp index.html www/
cp -r assets www/
cp -r pdfs www/

# 2. Sync and build
npx cap sync android
cd android && ./gradlew assembleDebug

# 3. Your new APK will be at:
# android/app/build/outputs/apk/debug/app-debug.apk
```

### 📦 Build Release APK (for distribution)

```bash
cd android && ./gradlew assembleRelease
# Find at: android/app/build/outputs/apk/release/app-release-unsigned.apk
```

### ⚙️ Project Structure

```
ExpoDietDemo/
├── www/                    # Web assets (copied from root)
│   ├── index.html
│   ├── assets/
│   └── pdfs/
├── android/                # Native Android project
└── capacitor.config.json   # Capacitor configuration
```

## Important Notes

- The app works completely offline once installed
- All PDFs are bundled with the app
- No changes to your original functionality
- App name: "Diet Simulator"
- Package ID: com.fit.dietsimulator
