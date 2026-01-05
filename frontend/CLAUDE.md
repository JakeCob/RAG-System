# Claude Guidelines - Frontend

## Quick Reference

```typescript
// API calls
import { sendQuery, checkHealth, ingestFile, ApiRequestError } from "@/lib/api";

// Types
import type { QueryInput, QueryResponse, SourceCitation, ApiError } from "@/types";

// Utilities
import { cn, formatDuration, truncate } from "@/lib/utils";
```

## Type Safety

### Always handle undefined for array access
```typescript
// tsconfig has noUncheckedIndexedAccess: true
const items = ["a", "b", "c"];
const first = items[0]; // type: string | undefined

// Must check before use
if (first !== undefined) {
  console.log(first.toUpperCase());
}

// Or use optional chaining
console.log(items[0]?.toUpperCase());
```

### Explicit return types
```typescript
// Required by ESLint
function formatScore(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}

// For components
function Card({ title }: { title: string }): React.ReactElement {
  return <div>{title}</div>;
}
```

## Component Patterns

### Server Component (default)
```typescript
// app/page.tsx - no "use client"
import { checkHealth } from "@/lib/api";

export default async function Page(): Promise<React.ReactElement> {
  const health = await checkHealth();

  return (
    <main>
      <p>Status: {health.status}</p>
    </main>
  );
}
```

### Client Component (interactivity)
```typescript
"use client";

import { useState } from "react";
import { sendQuery } from "@/lib/api";
import type { QueryResponse } from "@/types";

export function QueryForm(): React.ReactElement {
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(query: string): Promise<void> {
    setLoading(true);
    try {
      const result = await sendQuery({ query });
      setResponse(result);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); void handleSubmit("test"); }}>
      {/* form content */}
    </form>
  );
}
```

## API Error Handling

```typescript
import { ApiRequestError, sendQuery } from "@/lib/api";

try {
  const result = await sendQuery({ query: "test" });
  // Handle success
} catch (error) {
  if (error instanceof ApiRequestError) {
    // Typed error from backend
    console.error(`Error ${error.code}: ${error.message}`);
    if (error.details !== undefined) {
      console.error("Details:", error.details);
    }
  } else {
    // Network or other error
    console.error("Unexpected error:", error);
  }
}
```

## Styling with Tailwind

```typescript
import { cn } from "@/lib/utils";

interface ButtonProps {
  variant: "primary" | "secondary";
  disabled?: boolean;
  children: React.ReactNode;
}

function Button({ variant, disabled, children }: ButtonProps): React.ReactElement {
  return (
    <button
      disabled={disabled}
      className={cn(
        "px-4 py-2 rounded-lg font-medium transition-colors",
        variant === "primary" && "bg-primary-600 text-white hover:bg-primary-700",
        variant === "secondary" && "bg-slate-100 text-slate-900 hover:bg-slate-200",
        disabled === true && "opacity-50 cursor-not-allowed"
      )}
    >
      {children}
    </button>
  );
}
```

## Testing Components

```typescript
// src/components/Button.test.tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Button } from "./Button";

describe("Button", () => {
  it("renders children", () => {
    render(<Button variant="primary">Click me</Button>);
    expect(screen.getByRole("button")).toHaveTextContent("Click me");
  });

  it("handles click events", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(<Button variant="primary" onClick={onClick}>Click</Button>);
    await user.click(screen.getByRole("button"));

    expect(onClick).toHaveBeenCalledOnce();
  });
});
```

## Commands

```bash
# Development
npm run dev

# Build
npm run build

# Type check (no emit)
npm run typecheck

# Lint
npm run lint
npm run lint:fix

# Format
npm run format
npm run format:check

# Test
npm run test
npm run test:coverage
```

## File Naming

- Components: `PascalCase.tsx` (e.g., `QueryForm.tsx`)
- Utilities: `camelCase.ts` (e.g., `formatDuration.ts`)
- Types: Export from `types/index.ts`
- Tests: `*.test.ts` or `*.test.tsx`

## Common Mistakes to Avoid

1. **Forgetting "use client"** for interactive components
2. **Not handling undefined** from array access
3. **Missing return types** on functions
4. **Using `any`** - use `unknown` and narrow instead
5. **Forgetting `void`** when calling async functions in event handlers
