import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import HomePage from './pages/HomePage';
import BrowsePage from './pages/BrowsePage';
import CarDetailPage from './pages/CarDetailPage';
import SellPage from './pages/SellPage';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen bg-[#12232e]">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/cars" element={<BrowsePage />} />
            <Route path="/cars/:id" element={<CarDetailPage />} />
            <Route path="/sell" element={<SellPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}

function NotFound() {
  return (
    <div className="min-h-screen bg-[#12232e] flex flex-col items-center justify-center gap-4 font-lato pt-16 px-4">
      <div className="w-20 h-20 rounded-2xl bg-[#1a3344] border border-[#1e3a50] flex items-center justify-center">
        <span className="text-3xl font-black text-gray-500">404</span>
      </div>
      <h1 className="text-white font-bold text-3xl">Page Not Found</h1>
      <p className="text-gray-400 text-center max-w-sm">
        The page you're looking for doesn't exist. Let's get you back on track.
      </p>
      <a
        href="/"
        className="px-8 py-3 rounded-xl bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-bold hover:opacity-90 transition-opacity shadow-lg shadow-[#3a7bd5]/30"
      >
        Go Home
      </a>
    </div>
  );
}
