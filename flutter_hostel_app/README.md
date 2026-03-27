# Flutter Hostel APK

## 1) Generate Flutter boilerplate
From `flutter_hostel_app` run:

```bash
flutter create .
```

Then replace files with these already provided:
- `lib/main.dart`
- `android/app/src/main/AndroidManifest.xml`
- `pubspec.yaml`

## 2) Install packages
```bash
flutter pub get
```

## 3) Build debug APK
```bash
flutter build apk --debug
```

APK path:
`build/app/outputs/flutter-apk/app-debug.apk`

## 4) Build release APK
```bash
flutter build apk --release
```

APK path:
`build/app/outputs/flutter-apk/app-release.apk`

## Notes
- The app uses native login (`/login`) and then opens your web dashboard in WebView.
- All pages/features are loaded from `https://hmsuz.com`, so behavior stays aligned with the web app.
- To change server URL, edit `baseUrl` in `lib/main.dart`.
