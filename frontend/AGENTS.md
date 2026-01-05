# AI Agent Guidelines - Frontend

## Technology Stack

- **Next.js 14** with App Router
- **TypeScript** (strict mode)
- **Tailwind CSS** for styling
- **Vitest** + React Testing Library for tests
- **Deployed on Vercel**

## Directory Structure

```
frontend/
├── src/
│   ├── app/           # Next.js App Router pages
│   │   ├── layout.tsx     # Root layout
│   │   ├── page.tsx       # Home page
│   │   └── globals.css    # Global styles
│   ├── components/    # React components
│   ├── lib/           # Utilities and API client
│   │   ├── api.ts         # Backend API client
│   │   └── utils.ts       # Helper functions
│   ├── types/         # TypeScript interfaces
│   │   └── index.ts       # API types (mirrors backend schemas)
│   └── test/          # Test setup
│       └── setup.ts       # Vitest configuration
├── package.json
├── tsconfig.json      # Strict TypeScript config
├── tailwind.config.ts
├── vitest.config.ts
└── .eslintrc.json     # Strict ESLint rules
```

## Type Definitions

Types in `src/types/index.ts` must mirror backend Pydantic schemas:

| Backend Schema | Frontend Type |
|---------------|---------------|
| `TailorOutput` | `QueryResponse` |
| `SourceCitation` | `SourceCitation` |
| `MemoryQuery` | `QueryInput` |
| `AgentFailure` | `ApiError` |

## API Client

Use `src/lib/api.ts` for all backend communication:

```typescript
import { checkHealth, sendQuery, ingestFile } from "@/lib/api";

// Health check
const health = await checkHealth();

// Query
const response = await sendQuery({
  query: "What is the budget?",
  persona: "executive"
});

// File upload
const result = await ingestFile(file, { source: "manual" });
```

## Component Guidelines

1. **Server Components by default** (no "use client" unless needed)
2. **Client Components** only for interactivity
3. **Explicit return types** on all functions
4. **Use `cn()` utility** for conditional classes

```typescript
import { cn } from "@/lib/utils";

function Button({ variant }: { variant: "primary" | "secondary" }) {
  return (
    <button className={cn(
      "px-4 py-2 rounded",
      variant === "primary" && "bg-blue-500 text-white",
      variant === "secondary" && "bg-gray-200"
    )}>
      Click me
    </button>
  );
}
```

## Testing

```bash
# Run tests
npm run test

# With coverage
npm run test:coverage

# Type check
npm run typecheck

# Lint
npm run lint
```

## Strict TypeScript Settings

The `tsconfig.json` enforces:
- `noUncheckedIndexedAccess` - Array access may be undefined
- `exactOptionalPropertyTypes` - Optional props need explicit undefined
- `noImplicitReturns` - All code paths must return
- `noUnusedLocals` / `noUnusedParameters`

## Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Access in code:
```typescript
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
```
