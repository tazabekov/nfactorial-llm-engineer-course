import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const isHome = location.pathname === '/';

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navBg =
    isHome && !scrolled
      ? 'bg-transparent'
      : 'bg-[#0B0C10]/95 backdrop-blur-md shadow-lg shadow-black/20';

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${navBg}`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#3a7bd5] to-[#00d2ff] flex items-center justify-center shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <span className="text-xl font-bold font-lato">
              <span className="bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] bg-clip-text text-transparent">
                Auto
              </span>
              <span className="text-white">Hunt</span>
            </span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-8">
            <Link
              to="/cars"
              className="text-gray-300 hover:text-white transition-colors duration-200 font-medium text-sm tracking-wide"
            >
              Browse Cars
            </Link>
            <Link
              to="/sell"
              className="text-gray-300 hover:text-white transition-colors duration-200 font-medium text-sm tracking-wide"
            >
              Sell a Car
            </Link>
            <a
              href="#how-it-works"
              onClick={(e) => {
                if (location.pathname !== '/') return;
                e.preventDefault();
                document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="text-gray-300 hover:text-white transition-colors duration-200 font-medium text-sm tracking-wide"
            >
              How It Works
            </a>
            <Link
              to="/sell"
              className="px-5 py-2 rounded-lg bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white text-sm font-semibold hover:opacity-90 transition-opacity shadow-lg shadow-[#3a7bd5]/30"
            >
              List a Car
            </Link>
          </nav>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden text-gray-300 hover:text-white p-2"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
          >
            {menuOpen ? (
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>

        {/* Mobile Menu */}
        {menuOpen && (
          <div className="md:hidden bg-[#0B0C10]/98 border-t border-[#1e3a50] pb-4">
            <div className="flex flex-col gap-1 pt-2">
              <Link
                to="/cars"
                className="px-4 py-3 text-gray-300 hover:text-white hover:bg-[#12232e] rounded-lg transition-colors"
                onClick={() => setMenuOpen(false)}
              >
                Browse Cars
              </Link>
              <Link
                to="/sell"
                className="px-4 py-3 text-gray-300 hover:text-white hover:bg-[#12232e] rounded-lg transition-colors"
                onClick={() => setMenuOpen(false)}
              >
                Sell a Car
              </Link>
              <Link
                to="/sell"
                className="mx-4 mt-2 px-5 py-3 rounded-lg bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white text-sm font-semibold text-center"
                onClick={() => setMenuOpen(false)}
              >
                List a Car Free
              </Link>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
