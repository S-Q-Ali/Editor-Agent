import { HashRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ProjectPage from './pages/ProjectPage'
import ReviewPage from './pages/ReviewPage'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-900 text-slate-100">
        <header className="border-b border-slate-700 bg-slate-800 px-6 py-4">
          <h1 className="text-xl font-bold">Local AI Video Editor</h1>
        </header>
        <main className="container mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/project" element={<ProjectPage />} />
            <Route path="/project/review" element={<ReviewPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
