# Smart Lost & Found — web client

React + Vite + TypeScript, Tailwind, react-leaflet. Talks to the FastAPI server in `../api` through the Vite `/api` proxy (see `vite.config.ts`).

```bash
npm install
npm run dev -- --host   # http://localhost:5173, phone: http://<mac-lan-ip>:5173
npm run build           # tsc -b && vite build
```

Start the API first from the repo root: `uvicorn api.main:app --host 127.0.0.1 --port 8000`.

Routes: `/` home, `/account` login and own reports, `/report` lost/found form with map pins, `/matches` ranked matches, `/map` open reports, `/pickup/:lostId/:foundId` contact, meetup, notes, and recovered.

Session is a cookie set by the API; `src/api/client.ts` sends `credentials: "include"` with a 3-minute timeout so cold model loads do not fail the first request.
