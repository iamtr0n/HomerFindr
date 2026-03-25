import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Home, Search, Settings, PlusCircle } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import NewSearch from './pages/NewSearch'
import SearchResults from './pages/SearchResults'

function Nav() {
  const location = useLocation()
  const isActive = (path) => location.pathname === path ? 'bg-blue-700' : 'hover:bg-blue-700'

  return (
    <nav className="bg-blue-600 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center h-14 gap-6">
          <Link to="/" className="flex items-center gap-2 font-bold text-lg">
            <Home size={22} />
            HomeSearch
          </Link>
          <div className="flex gap-1 ml-6">
            <Link to="/" className={`px-3 py-1.5 rounded text-sm flex items-center gap-1.5 ${isActive('/')}`}>
              <Search size={16} /> Dashboard
            </Link>
            <Link to="/search/new" className={`px-3 py-1.5 rounded text-sm flex items-center gap-1.5 ${isActive('/search/new')}`}>
              <PlusCircle size={16} /> New Search
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/search/new" element={<NewSearch />} />
          <Route path="/search/:id/results" element={<SearchResults />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
