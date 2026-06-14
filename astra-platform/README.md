# 🌟 ASTRA Web Platform

The **ASTRA Web Platform** is an interactive, high-performance Next.js application designed to visualize, analyze, and query variable stars. It integrates a 3D celestial sphere explorer, interactive light-curve visualization, self-attention map explanations, real-time audio synthesis of stellar variability, and serverless ONNX model inference.

---

## 🏗️ Architecture & Technology Stack

The platform is designed to run efficiently in both local environments and resource-constrained serverless cloud environments (e.g., Vercel, Render).

### Frontend Stack
- **Framework:** Next.js 16 (App Router)
- **UI & Layout:** React 19, Tailwind CSS v4, `@base-ui/react`, `lucide-react`
- **3D Graphics:** Three.js via React Three Fiber (`@react-three/fiber`) and Drei (`@react-three/drei`) for the interactive star field and constellation boundaries
- **Plots & Charts:** Recharts for high-fidelity interactive light curves and attention-map grids
- **State Management:** Zustand (lightweight, decoupled client stores)
- **Interactions:** Framer Motion (micro-animations, smooth transition overlays)
- **Sonification:** HTML5 Web Audio API (real-time FM synthesis mapping stellar brightness to audio frequency)

### Backend Stack
- **Database:** Node.js native `node:sqlite` (`DatabaseSync`) querying a local, optimized database containing 944 verified targets
- **ML Inference:** ONNX Runtime Node (`onnxruntime-node`) loaded directly in serverless API routes
- **Scientific Pipelines:** Custom JS translators matching Python's normalization, detrending, and phase-folding routines

---

## ⚡ Serverless Optimization & SQLite URI Locks

Deploying databases and ML runtimes in serverless environments (like Vercel Serverless Functions) presents strict filesystem constraints. ASTRA addresses these via two configuration designs:

### 1. Vercel Serverless File Tracing
To ensure the Next.js production build includes the SQLite database and ONNX models, the platform configures tracing in `next.config.ts`:

```typescript
// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingIncludes: {
    '/api/**/*': ['./data/**/*'], // Package database and ONNX assets in API functions
  },
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
```

### 2. Immutable SQLite Connection Locks (`?immutable=1`)
Because serverless filesystems are read-only, attempting to write journal files (`-journal` or `-wal`) or acquiring standard lock-files will cause the runtime to crash. All ASTRA API routes safely acquire read-only immutable file locks by appending `?immutable=1` to the file URL:

```typescript
import { DatabaseSync } from 'node:sqlite';
import { pathToFileURL } from 'node:url';

// Open the database in read-only and immutable mode
const dbPath = path.join(process.cwd(), 'data', 'astra.sqlite');
const db = new DatabaseSync(pathToFileURL(dbPath).toString() + '?immutable=1', { readOnly: true });
```

---

## 🔄 Request Processing Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Researcher (Browser)
    participant Front as Next.js Frontend (Zustand + Three.js)
    participant API as Next.js API Routes (Serverless)
    database DB as SQLite (astra.sqlite)
    participant ONNX as ONNX Runtime Node (model.onnx)

    User->>Front: Access Star Detail / Request Prediction
    Front->>API: GET /api/predict/[id]
    Note over API: Resolves path to astra.sqlite
    API->>DB: Open with pathToFileURL + ?immutable=1
    DB-->>API: Returns star's resampled light curve array
    Note over API: Load ONNX session & run inference
    API->>ONNX: Feed dual-channel tensor (1, 2, 1000)
    ONNX-->>API: Returns logits & raw attention weights
    Note over API: Apply temperature scaling & MC dropout uncertainty
    API-->>Front: JSON Payload (calibrated probabilities, attention weights)
    Front->>User: Render interactive 3D field, attention maps, and Web Audio playbacks
```

---

## 📡 Backend API Endpoints

| Endpoint | Method | Description |
|:---|:---:|:---|
| `/api/stars` | `GET` | Retrieve paginated stellar catalog with filter options (class, magnitude, period). |
| `/api/stars/[id]` | `GET` | Fetch metadata, celestial coordinates, and full light curve array for a target. |
| `/api/predict/[id]` | `GET` | Run live ONNX model inference to obtain calibrated class probabilities. |
| `/api/explain/[id]` | `GET` | Fetch attention weight matrices from the HybridTransformer's self-attention layers. |
| `/api/search` | `GET` | Perform RA/Dec coordinate range-based cone search and star name query. |
| `/api/osint/[id]` | `GET` | Get links to external databases (AAVSO VSX, MAST Portal, TIC Catalog). |
| `/api/upload` | `POST` | Process user-uploaded CSV, run preprocessing, and run ONNX classifier. |

---

## 🛠️ Local Installation & Development

### Prerequisites
- Node.js (version `>= 22.5.0` required for native `node:sqlite` `DatabaseSync`)
- npm or pnpm

### Setup Steps
1. Navigate to the platform directory:
   ```bash
   cd astra-platform
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your browser.

### Building for Production
To build the application:
```bash
npm run build
```
To run the production build locally:
```bash
npm run start
```

---

## 🐳 Docker Deployment

For containerized environments, a production-optimized multi-stage `Dockerfile` is provided:

```dockerfile
# Build stage
FROM node:22.5-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Runner stage
FROM node:22.5-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/data ./data
RUN npm ci --only=production
EXPOSE 3000
CMD ["npm", "run", "start"]
```

Build and run with:
```bash
docker build -t astra-platform .
docker run -p 3000:3000 astra-platform
```
