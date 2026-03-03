# Vite + Vanilla JS + FastAPI

A no-framework frontend architecture using npm packages with tree-shaking, paired with a FastAPI backend.

## Problem

Using npm libraries in vanilla JS projects without adopting a framework or complex build tooling.

## Solution

Vite as a thin layer: zero-build in dev, minimal tree-shaking build for production. FastAPI serves the built static files.

## Project Structure

```
project/
  api/
    main.py
    routes/
  frontend/
    src/
      index.html
      about.html
      shared/
        utils.js
        styles.css
    vite.config.js
    package.json
  docker-compose.yml
```

## Vite Config

Auto-detects all HTML files. No manual entry point management.

```js
// vite.config.js
import { resolve } from 'path';
import { globSync } from 'fs';

export default {
  root: 'src',
  build: {
    outDir: '../dist',
    rollupOptions: {
      input: Object.fromEntries(
        globSync('src/**/*.html').map(file => [
          file.replace('src/', '').replace('.html', ''),
          resolve(file)
        ])
      )
    }
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
};
```

## FastAPI Integration

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

@app.get('/api/items')
async def get_items():
    return [{'id': 1, 'name': 'thing'}]

# Serve built frontend — mount LAST so API routes take priority
app.mount('/', StaticFiles(directory='frontend/dist', html=True), name='static')
```

## Frontend Usage

Install npm packages normally, import in vanilla JS:

```bash
npm install lodash-es
```

```js
import { debounce } from 'lodash-es';

document.querySelector('#search').addEventListener('input', debounce(e => {
  console.log(e.target.value);
}, 300));
```

Reference from HTML:

```html
<script type="module" src="./search.js"></script>
```

## How It Works

- **Dev**: Vite resolves bare imports from `node_modules`, serves files as-is. Proxies `/api` to FastAPI.
- **Build**: Rollup tree-shakes npm dependencies, outputs to `dist/`. Your code ships as-written.
- **Production**: FastAPI serves everything from `dist/`. One container, one port.

## Dev Workflow

```bash
# Terminal 1
cd api && uvicorn main:app --reload

# Terminal 2
cd frontend && npx vite
```

Or via Docker Compose for both services.

## Key Principles

- No framework. HTML, CSS, JS per view.
- Shared utilities in common files.
- Native ES modules throughout.
- npm packages available via bare imports.
- Tree-shaking only happens at build time for production.
- FastAPI handles API routes and serves static files.
