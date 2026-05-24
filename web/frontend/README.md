# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

## API configuration & production builds

This project reads the backend base URL from a Vite environment variable at build time.

- Environment variable: `VITE_API_URL` — the full backend base URL (e.g. `https://api.example.com`).

Local development (Vite)

PowerShell (Windows):
```powershell
cd web/frontend
$env:VITE_API_URL = 'http://localhost:5000'
npm install
npm run dev
```

Bash / macOS / Linux:
```bash
cd web/frontend
export VITE_API_URL='http://localhost:5000'
npm install
npm run dev
```

Production build

PowerShell:
```powershell
cd web/frontend
$env:VITE_API_URL = 'https://api.example.com'
npm run build
```

Bash / macOS / Linux:
```bash
cd web/frontend
export VITE_API_URL='https://api.example.com'
npm run build
```

Vercel / CI

- Set `VITE_API_URL` in Vercel Environment Variables to your backend URL before running the build step.
- Vite inlines `import.meta.env.VITE_API_URL` during the build; the value must be present at build time.

Optional: cross-platform npm scripts using `cross-env`

If you prefer a single cross-platform script, add `cross-env` and then a script in `package.json`:

```json
"scripts": {
	"dev:api": "cross-env VITE_API_URL=http://localhost:5000 vite",
	"build:api": "cross-env VITE_API_URL=https://api.example.com vite build"
}
```

Install `cross-env`:
```bash
cd web/frontend
npm install --save-dev cross-env
```

Then run:
```bash
npm run build:api
```

This README section shows how to set `VITE_API_URL` for development and production builds. After setting the variable, run `npm run build` to produce a build that targets the configured backend.
