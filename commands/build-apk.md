# Build APK

Build an APK for local testing or manual sharing. No remote distribution.

> **PROJECT-SPECIFIC: replace the staging/production URLs and the pubspec path below with project values.**

## Instructions

### 1. Read Current Version

Read `{FLUTTER_APP_DIR}/pubspec.yaml` and extract the `version:` line (format: `X.Y.Z+N`).
- `VERSION` = `X.Y.Z`
- `BUILD_NUMBER` = `N`

### 2. Ask Target Environment

Use AskUserQuestion to choose:
- **Staging** — `{STAGING_API_URL}`, suffix `staging`
- **Production** — `{PRODUCTION_API_URL}`, suffix `beta`

### 3. Build APK

```bash
cd {FLUTTER_APP_DIR}

flutter build apk --release \
  --dart-define=API_BASE_URL=$API_URL \
  --build-name=$VERSION-$SUFFIX \
  --build-number=$BUILD_NUMBER
```

### 4. Report

Show:
- Environment and API URL used
- Version string (e.g. `1.3.7-staging+35`)
- APK path: `{FLUTTER_APP_DIR}/build/app/outputs/flutter-apk/app-release.apk`
