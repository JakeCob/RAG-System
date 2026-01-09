# Deployment Guide

## Backend (Railway) ✅

**Status:** Deployed
**URL:** https://rag-system-production-5f7a.up.railway.app

### Configuration
- Using Railpack builder
- Python 3.11.9 (via `.tool-versions`)
- Dependencies from `requirements.txt`
- Start command in `railway.toml`

## Frontend (Vercel)

### Prerequisites
1. Install Vercel CLI (optional): `npm i -g vercel`
2. Have a Vercel account linked to your GitHub

### Deployment Steps

#### Option 1: Via Vercel Dashboard (Recommended)

1. **Go to [vercel.com](https://vercel.com)** and sign in

2. **Click "Add New Project"**

3. **Import your GitHub repository:**
   - Select `RAG-System` repository
   - Click "Import"

4. **Configure Project:**
   - **Framework Preset:** Next.js (will auto-detect)
   - **Root Directory:** Click "Edit" and set to `frontend` ⚠️ **IMPORTANT**
   - **Build Command:** Leave default (auto-detected)
   - **Output Directory:** Leave default (auto-detected)
   - **Install Command:** Leave default (auto-detected)

5. **Environment Variables:**
   The `NEXT_PUBLIC_API_URL` is already configured in `frontend/vercel.json` to point to:
   ```
   https://rag-system-production-5f7a.up.railway.app
   ```

   No additional env vars needed unless you want to override it.

6. **Deploy:**
   - Click "Deploy"
   - Wait for build to complete (~2-3 minutes)

#### Option 2: Via Vercel CLI

```bash
# Navigate to frontend directory
cd /root/Programming\ Projects/Personal/RAG-System/frontend

# Login to Vercel (if not already)
vercel login

# Deploy (production)
vercel --prod

# Or deploy preview
vercel
```

### Post-Deployment

1. **Test the deployed frontend:**
   - Visit your Vercel URL (e.g., `your-project.vercel.app`)
   - Try making a query to verify backend connectivity

2. **Set up CORS on Railway backend** (if needed):
   Add environment variable in Railway dashboard:
   ```
   ALLOWED_ORIGINS=https://your-project.vercel.app,https://your-project-*.vercel.app
   ```

3. **Update API URL if Railway domain changes:**
   Either update `vercel.json` and redeploy, or set env var in Vercel dashboard

### Monitoring

- **Vercel Dashboard:** https://vercel.com/dashboard
  - View deployment logs
  - Monitor function executions
  - Check analytics

- **Railway Dashboard:** https://railway.app/dashboard
  - View backend logs
  - Monitor resource usage
  - Check deployment status

### Troubleshooting

**Frontend can't connect to backend:**
1. Check CORS settings on Railway backend
2. Verify `NEXT_PUBLIC_API_URL` in Vercel env vars
3. Check Railway backend is running (visit API URL directly)

**Build fails on Vercel:**
1. Check build logs in Vercel dashboard
2. Verify `frontend/package.json` dependencies
3. Try running `cd frontend && npm run build` locally

**Environment variable not working:**
1. Ensure it starts with `NEXT_PUBLIC_` for client-side access
2. Redeploy after changing env vars
3. Clear Vercel cache and redeploy

### Files for Deployment

- ✅ `frontend/vercel.json` - Vercel environment variables
- ✅ `vercel.json` - Root Vercel config (git settings)
- ✅ `.vercelignore` - Excludes backend files from deployment
- ✅ `frontend/package.json` - Next.js dependencies
- ✅ `frontend/next.config.js` - Next.js configuration
- ✅ `railway.toml` - Railway configuration (backend)
- ✅ `requirements.txt` - Python dependencies (backend)
- ✅ `Procfile` - Railway start command (backup)

## Architecture

```
┌─────────────────┐
│   Vercel        │
│  (Frontend)     │
│   Next.js 14    │
└────────┬────────┘
         │
         │ HTTPS
         │
         ▼
┌─────────────────┐
│   Railway       │
│  (Backend)      │
│   FastAPI       │
│   + LanceDB     │
└─────────────────┘
```

## Cost Estimates

- **Vercel:** Free tier (Hobby) - 100GB bandwidth/month
- **Railway:** Depends on usage (~$5-10/month for small projects)

## Next Steps

1. Deploy frontend to Vercel using steps above
2. Test end-to-end functionality
3. Set up custom domain (optional)
4. Configure monitoring/alerts (optional)
