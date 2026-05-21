# Deploy Mobile App

Build and distribute the mobile app via Firebase App Distribution.

> **PROJECT-SPECIFIC: replace the API URLs, Firebase app ID, tester group, and pubspec path below with project values.**

## Instructions

### 1. Read Current Version

Read `{MOBILE_APP_DIR}/pubspec.yaml` and extract the `version:` line (format: `X.Y.Z+N`).

### 2. Ask Target Environment

Use AskUserQuestion:
- **Staging** — builds with staging API, `-staging` suffix, notifies `{TESTER_GROUP}` group
- **Production** — builds with production API, `-beta` suffix, notifies `{TESTER_GROUP}` group

### 3. Get Release Notes

Read `{MOBILE_CHANGELOG_PATH}` and use the latest entry's `changes` array as release notes.
Format as a bulleted list prefixed with the environment label:

```
STAGING v1.2.13:
- Change 1
- Change 2
```

Or for production: `PROD-BETA v1.2.13: ...`

### 4. Build APK

```bash
cd {MOBILE_APP_DIR}

flutter build apk --release \
  --dart-define=API_BASE_URL=$API_URL \
  --build-name=$VERSION-$SUFFIX \
  --build-number=$BUILD_NUMBER
```

| Environment | API_BASE_URL | Suffix |
|-------------|-------------|--------|
| Staging | `{STAGING_API_URL}` | `staging` |
| Production | `{PRODUCTION_API_URL}` | `beta` |

### 5. Distribute via Firebase

```bash
firebase appdistribution:distribute \
  {MOBILE_APP_DIR}/build/app/outputs/flutter-apk/app-release.apk \
  --app {FIREBASE_APP_ID} \
  --groups "{TESTER_GROUP}" \
  --release-notes "$RELEASE_NOTES"
```

### 6. Report

Show:
- Environment deployed
- Version string (e.g. `1.2.13-staging+23`)
- Release notes sent
- Tester group notified
