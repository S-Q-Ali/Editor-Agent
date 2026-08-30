function Dashboard() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h3 className="text-lg font-semibold mb-2">Projects</h3>
          <p className="text-slate-400">No projects yet. Create one to get started.</p>
        </div>
        <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h3 className="text-lg font-semibold mb-2">System Status</h3>
          <p className="text-slate-400">Checking...</p>
        </div>
        <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h3 className="text-lg font-semibold mb-2">Quick Start</h3>
          <p className="text-slate-400">Upload music, lyrics, and AI clips to begin.</p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
