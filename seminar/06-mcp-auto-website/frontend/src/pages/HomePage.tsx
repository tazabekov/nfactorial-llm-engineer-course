import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import CarCard from '../components/CarCard';
import { Car } from '../types/car';
import { mockCars, carMakes, bodyTypes, fuelTypes } from '../data/mockCars';

const stats = [
  { value: '2,400+', label: 'Cars Listed' },
  { value: '1,800+', label: 'Happy Buyers' },
  { value: '500+', label: 'Trusted Dealers' },
  { value: '4.9★', label: 'Rating' },
];

const howItWorks = [
  {
    step: '01',
    title: 'Browse Listings',
    description:
      'Search through thousands of verified car listings with detailed specs, high-quality photos, and transparent pricing.',
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    ),
  },
  {
    step: '02',
    title: 'Contact Seller',
    description:
      'Reach out directly to verified sellers or dealerships. Schedule test drives, ask questions, and negotiate the best deal.',
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
  },
  {
    step: '03',
    title: 'Drive Away Happy',
    description:
      'Complete the purchase with confidence. All listings are verified and we support you through the entire buying process.',
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

export default function HomePage() {
  const navigate = useNavigate();
  const [featuredCars] = useState<Car[]>(mockCars.slice(0, 6));
  const [searchFilters, setSearchFilters] = useState({
    make: '',
    bodyType: '',
    year: '',
    priceMax: '',
  });

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const params = new URLSearchParams();
    if (searchFilters.make) params.set('make', searchFilters.make);
    if (searchFilters.bodyType) params.set('bodyType', searchFilters.bodyType);
    if (searchFilters.year) {
      params.set('yearMin', searchFilters.year);
      params.set('yearMax', searchFilters.year);
    }
    if (searchFilters.priceMax) params.set('priceMax', searchFilters.priceMax);
    navigate(`/cars?${params.toString()}`);
  }

  return (
    <div className="bg-[#12232e] min-h-screen font-lato">
      {/* ─── Hero ─── */}
      <section className="relative min-h-screen flex items-center overflow-hidden">
        {/* Background image */}
        <div className="absolute inset-0">
          <img
            src="https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1600"
            alt="Luxury car"
            className="w-full h-full object-cover"
            width={1600}
            height={900}
          />
          <div className="absolute inset-0 bg-gradient-to-r from-[#0B0C10]/95 via-[#12232e]/70 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0B0C10]/60 via-transparent to-transparent" />
        </div>

        {/* Hero content */}
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-32">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#3a7bd5]/20 border border-[#3a7bd5]/40 mb-6">
              <div className="w-2 h-2 rounded-full bg-[#00d2ff] animate-pulse" />
              <span className="text-[#00d2ff] text-sm font-medium">2,400+ Cars Available Now</span>
            </div>

            <h1 className="font-lato font-black text-white leading-[1.1] mb-6" style={{ fontSize: 'clamp(48px, 7vw, 72px)' }}>
              Find Your{' '}
              <span className="bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] bg-clip-text text-transparent">
                Perfect Car
              </span>
            </h1>

            <p className="text-gray-300 text-lg leading-relaxed mb-10 max-w-xl">
              Discover thousands of premium vehicles from trusted dealers and private sellers.
              Your dream car is just a search away.
            </p>

            <div className="flex flex-wrap gap-4">
              <button
                onClick={() => navigate('/cars')}
                className="px-8 py-4 rounded-lg bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-bold text-base hover:opacity-90 transition-all shadow-xl shadow-[#3a7bd5]/30 hover:shadow-[#3a7bd5]/50 hover:-translate-y-0.5"
              >
                Browse Cars
              </button>
              <button
                onClick={() => navigate('/sell')}
                className="px-8 py-4 rounded-lg bg-white/10 border border-white/20 text-white font-bold text-base hover:bg-white/20 transition-all backdrop-blur-sm"
              >
                Sell Your Car
              </button>
            </div>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 animate-bounce">
          <span className="text-gray-400 text-xs">Scroll to explore</span>
          <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </section>

      {/* ─── Search Bar ─── */}
      <section className="relative z-20 -mt-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto">
          <form
            onSubmit={handleSearch}
            className="bg-[#0B0C10]/95 backdrop-blur-xl border border-[#1e3a50] rounded-2xl p-4 shadow-2xl shadow-black/40"
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              <div className="lg:col-span-1">
                <label className="block text-xs text-gray-400 font-medium mb-1.5 px-1">Make</label>
                <select
                  value={searchFilters.make}
                  onChange={(e) => setSearchFilters((f) => ({ ...f, make: e.target.value }))}
                  className="w-full bg-[#12232e] border border-[#1e3a50] rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-[#3a7bd5] transition-colors appearance-none cursor-pointer"
                >
                  <option value="">Any Make</option>
                  {carMakes.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              <div className="lg:col-span-1">
                <label className="block text-xs text-gray-400 font-medium mb-1.5 px-1">Body Type</label>
                <select
                  value={searchFilters.bodyType}
                  onChange={(e) => setSearchFilters((f) => ({ ...f, bodyType: e.target.value }))}
                  className="w-full bg-[#12232e] border border-[#1e3a50] rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-[#3a7bd5] transition-colors appearance-none cursor-pointer"
                >
                  <option value="">Any Type</option>
                  {bodyTypes.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div className="lg:col-span-1">
                <label className="block text-xs text-gray-400 font-medium mb-1.5 px-1">Year</label>
                <select
                  value={searchFilters.year}
                  onChange={(e) => setSearchFilters((f) => ({ ...f, year: e.target.value }))}
                  className="w-full bg-[#12232e] border border-[#1e3a50] rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-[#3a7bd5] transition-colors appearance-none cursor-pointer"
                >
                  <option value="">Any Year</option>
                  {[2023, 2022, 2021, 2020, 2019, 2018].map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>

              <div className="lg:col-span-1">
                <label className="block text-xs text-gray-400 font-medium mb-1.5 px-1">Max Price</label>
                <select
                  value={searchFilters.priceMax}
                  onChange={(e) => setSearchFilters((f) => ({ ...f, priceMax: e.target.value }))}
                  className="w-full bg-[#12232e] border border-[#1e3a50] rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-[#3a7bd5] transition-colors appearance-none cursor-pointer"
                >
                  <option value="">Any Price</option>
                  <option value="50000">Under $50,000</option>
                  <option value="100000">Under $100,000</option>
                  <option value="150000">Under $150,000</option>
                  <option value="250000">Under $250,000</option>
                </select>
              </div>

              <div className="lg:col-span-1">
                <label className="block text-xs text-gray-400 font-medium mb-1.5 px-1">&nbsp;</label>
                <button
                  type="submit"
                  className="w-full px-6 py-2.5 rounded-lg bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-bold text-sm hover:opacity-90 transition-opacity shadow-lg shadow-[#3a7bd5]/30"
                >
                  Search Cars
                </button>
              </div>
            </div>

            {/* Quick filters */}
            <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-[#1e3a50]">
              <span className="text-xs text-gray-500">Popular:</span>
              {fuelTypes.concat(['Under $80K', 'Manual']).map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => {
                    if (tag === 'Under $80K') {
                      navigate('/cars?priceMax=80000');
                    } else if (tag === 'Manual') {
                      navigate('/cars?transmission=Manual');
                    } else {
                      navigate(`/cars?fuel=${tag}`);
                    }
                  }}
                  className="px-3 py-1 rounded-full bg-[#12232e] border border-[#1e3a50] text-gray-400 text-xs hover:border-[#3a7bd5] hover:text-white transition-colors"
                >
                  {tag}
                </button>
              ))}
            </div>
          </form>
        </div>
      </section>

      {/* ─── Stats Bar ─── */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-[#1e3a50] rounded-2xl overflow-hidden border border-[#1e3a50]">
            {stats.map((stat, i) => (
              <div
                key={i}
                className="bg-[#12232e] px-6 py-8 flex flex-col items-center gap-1 text-center hover:bg-[#1a3344] transition-colors"
              >
                <span className="text-3xl font-black bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] bg-clip-text text-transparent">
                  {stat.value}
                </span>
                <span className="text-gray-400 text-sm font-medium">{stat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Featured Listings ─── */}
      <section className="pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-end justify-between mb-8">
            <div>
              <p className="text-[#3a7bd5] text-sm font-semibold uppercase tracking-widest mb-2">
                Hand-Picked
              </p>
              <h2 className="text-white font-black text-3xl sm:text-4xl font-lato">
                Featured Listings
              </h2>
            </div>
            <button
              onClick={() => navigate('/cars')}
              className="hidden sm:flex items-center gap-2 text-[#00d2ff] text-sm font-semibold hover:gap-3 transition-all"
            >
              View All Cars
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {featuredCars.map((car) => (
              <CarCard key={car.id} car={car} />
            ))}
          </div>

          <div className="mt-8 text-center sm:hidden">
            <button
              onClick={() => navigate('/cars')}
              className="px-8 py-3 rounded-lg bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-bold"
            >
              View All Cars
            </button>
          </div>
        </div>
      </section>

      {/* ─── How It Works ─── */}
      <section id="how-it-works" className="py-20 px-4 sm:px-6 lg:px-8 bg-[#0B0C10]">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-14">
            <p className="text-[#3a7bd5] text-sm font-semibold uppercase tracking-widest mb-3">
              Simple Process
            </p>
            <h2 className="text-white font-black text-3xl sm:text-4xl font-lato mb-4">
              How AutoHunt Works
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto leading-relaxed">
              From searching to driving away, we've made car buying as seamless as possible.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            {/* Connecting line */}
            <div className="hidden md:block absolute top-12 left-1/3 right-1/3 h-0.5 bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] opacity-30" />

            {howItWorks.map((step, i) => (
              <div key={i} className="relative flex flex-col items-center text-center">
                <div className="relative mb-6">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#3a7bd5]/20 to-[#00d2ff]/10 border border-[#3a7bd5]/30 flex items-center justify-center text-[#3a7bd5] mb-4">
                    {step.icon}
                  </div>
                  <div className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-gradient-to-br from-[#3a7bd5] to-[#00d2ff] flex items-center justify-center text-white text-xs font-black">
                    {i + 1}
                  </div>
                </div>
                <h3 className="text-white font-bold text-xl mb-3">{step.title}</h3>
                <p className="text-gray-400 leading-relaxed text-sm">{step.description}</p>
              </div>
            ))}
          </div>

          <div className="mt-14 text-center">
            <button
              onClick={() => navigate('/cars')}
              className="px-10 py-4 rounded-xl bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-bold text-base hover:opacity-90 transition-all shadow-xl shadow-[#3a7bd5]/30 hover:-translate-y-0.5"
            >
              Start Browsing Now
            </button>
          </div>
        </div>
      </section>

      {/* ─── CTA Banner ─── */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-[#12232e]">
        <div className="max-w-4xl mx-auto">
          <div className="relative rounded-3xl overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] opacity-90" />
            <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=800')] bg-cover bg-center opacity-10 mix-blend-overlay" />
            <div className="relative z-10 px-8 py-12 text-center">
              <h2 className="text-white font-black text-3xl sm:text-4xl font-lato mb-4">
                Ready to Sell Your Car?
              </h2>
              <p className="text-white/90 mb-8 text-lg max-w-xl mx-auto">
                List your vehicle in minutes and reach thousands of qualified buyers.
                No hidden fees, no hassle.
              </p>
              <div className="flex flex-wrap gap-4 justify-center">
                <button
                  onClick={() => navigate('/sell')}
                  className="px-8 py-4 rounded-xl bg-white text-[#3a7bd5] font-black text-base hover:bg-gray-100 transition-colors shadow-xl"
                >
                  List Your Car Free
                </button>
                <button
                  onClick={() => navigate('/cars')}
                  className="px-8 py-4 rounded-xl bg-white/10 border-2 border-white/40 text-white font-bold text-base hover:bg-white/20 transition-colors backdrop-blur-sm"
                >
                  Learn More
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
