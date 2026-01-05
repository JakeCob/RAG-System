export default function Home(): React.ReactElement {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-primary-600">RAG System</h1>
        <p className="mt-4 text-lg text-slate-600">
          Multi-Source Agentic RAG Web Application
        </p>
        <div className="mt-8 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-slate-500">Environment scaffold ready.</p>
          <p className="mt-2 text-xs text-slate-400">
            Next.js + FastAPI + ChromaDB
          </p>
        </div>
      </div>
    </main>
  );
}
