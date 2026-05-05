import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import CarCard from '../components/CarCard';
import LoadingSpinner from '../components/LoadingSpinner';
import { getCars } from '../api/cars';
import { Car, CarFilters } from '../types/car';
import { carMakes, bodyTypes, fuelTypes, transmissionTypes } from '../data/mockCars';

const SORT_OPTIONS = [
  { value: 'price_asc', label: 'Price: Low to High' },
  { value: 'price_desc', label: 'Price: High to Low' },
  { value: 'year_desc', label: 'Newest First' },
  { value: 'year_asc', label: 'Oldest First' },
  { value: 'mileage_asc', label: 'Lowest Mileage' },
];

interface FilterState {
  makes: string[];
  bodyTypes: string[];
  fuels: string[];
  transmissions: string[];
  yearMin: number;
  yearMax: number;
  priceMin: number;
  priceMax: number;
  mileageMax: number;
}

const DEFAULT_FILTERS: FilterState = {
  makes: [],
  bodyTypes: [],
  fuels: [],
  transmissions: [],
  yearMin: 2015,
  yearMax: 2023,
  priceMin: 0,
  priceMax: 300000,
  mileageMax: 100000,
};

export default function BrowsePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [cars, setCars] = useState<Car[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalCars, setTotalCars] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [sort, setSort] = useState<CarFilters['sort']>('year_desc');
  const [filters, setFilters] = useState<FilterState>(() => {
    // Initialize from URL params
    const init = { ...DEFAULT_FILTERS };
    const make = searchParams.get('make');
    if (make) init.makes = [make];
    const bodyType = searchParams.get('bodyType');
    if (bodyType) init.bodyTypes = [bodyType];
    const fuel = searchParams.get('fuel');
    if (fuel) init.fuels = [fuel];
    const transmission = searchParams.get('transmission');
    if (transmission) init.transmissions = [transmission];
    const priceMax = searchParams.get('priceMax');
    if (priceMax) init.priceMax = Number(priceMax);
    const yearMin = searchParams.get('yearMin');
    if (yearMin) init.yearMin = Number(yearMin);
    const yearMax = searchParams.get('yearMax');
    if (yearMax) init.yearMax = Number(yearMax);
    return init;
  });
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const fetchCars = useCallback(async () => {
    setLoading(true);
    try {
      const apiFilters: CarFilters = {
        sort,
        page: currentPage,
        limit: 12,
      };
      if (filters.makes.length === 1) apiFilters.make = filters.makes[0];
      if (filters.bodyTypes.length === 1) apiFilters.bodyType = filters.bodyTypes[0];
      if (filters.fuels.length === 1) apiFilters.fuel = filters.fuels[0];
      if (filters.transmissions.length === 1) apiFilters.transmission = filters.transmissions[0];
      if (filters.priceMin > 0) apiFilters.priceMin = filters.priceMin;
      if (filters.priceMax < 300000) apiFilters.priceMax = filters.priceMax;
      if (filters.yearMin > 2015) apiFilters.yearMin = filters.yearMin;
      if (filters.yearMax < 2023) apiFilters.yearMax = filters.yearMax;
      if (filters.mileageMax < 100000) apiFilters.mileageMax = filters.mileageMax;

      const result = await getCars(apiFilters);
      // Client-side multi-select filtering for make/bodyType/fuel/transmission
      let filtered = result.cars;
      if (filters.makes.length > 1) {
        filtered = filtered.filter((c) => filters.makes.includes(c.make));
      }
      if (filters.bodyTypes.length > 1) {
        filtered = filtered.filter((c) => filters.bodyTypes.includes(c.bodyType));
      }
      if (filters.fuels.length > 1) {
        filtered = filtered.filter((c) => filters.fuels.includes(c.fuel));
      }
      if (filters.transmissions.length > 1) {
        filtered = filtered.filter((c) => filters.transmissions.includes(c.transmission));
      }
      setCars(filtered);
      setTotalCars(result.total);
      setTotalPages(result.totalPages);
    } finally {
      setLoading(false);
    }
  }, [filters, sort, currentPage]);

  useEffect(() => {
    fetchCars();
  }, [fetchCars]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [currentPage]);

  function toggleArrayFilter(key: keyof FilterState, value: string) {
    setFilters((prev) => {
      const arr = prev[key] as string[];
      const next = arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
      return { ...prev, [key]: next };
    });
    setCurrentPage(1);
  }

  function clearFilters() {
    setFilters(DEFAULT_FILTERS);
    setCurrentPage(1);
    setSearchParams({});
  }

  const hasActiveFilters =
    filters.makes.length > 0 ||
    filters.bodyTypes.length > 0 ||
    filters.fuels.length > 0 ||
    filters.transmissions.length > 0 ||
    filters.priceMax < 300000 ||
    filters.mileageMax < 100000;

  return (
    <div className="min-h-screen bg-[#12232e] font-lato pt-16">
      {/* Page header */}
      <div className="bg-[#0B0C10] border-b border-[#1e3a50] py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-white font-black text-3xl font-lato mb-1">Browse Cars</h1>
          <p className="text-gray-400 text-sm">
            {loading ? 'Searching...' : `${totalCars} vehicles available`}
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-8">
          {/* ─── Sidebar ─── */}
          <aside
            className={`
              fixed inset-y-0 left-0 z-50 w-72 bg-[#0B0C10] overflow-y-auto transform transition-transform duration-300 lg:static lg:transform-none lg:w-64 lg:flex-shrink-0 lg:bg-transparent
              ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
            `}
          >
            {/* Mobile sidebar header */}
            <div className="flex items-center justify-between p-4 border-b border-[#1e3a50] lg:hidden">
              <h2 className="text-white font-bold">Filters</h2>
              <button
                onClick={() => setSidebarOpen(false)}
                className="text-gray-400 hover:text-white p-1"
                aria-label="Close filters"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-4 lg:p-0 space-y-6">
              {/* Filter header */}
              <div className="flex items-center justify-between">
                <h2 className="text-white font-bold text-base">Filters</h2>
                {hasActiveFilters && (
                  <button
                    onClick={clearFilters}
                    className="text-[#00d2ff] text-xs font-semibold hover:underline"
                  >
                    Clear All
                  </button>
                )}
              </div>

              {/* Make */}
              <FilterSection title="Make">
                {carMakes.map((make) => (
                  <CheckboxFilter
                    key={make}
                    label={make}
                    checked={filters.makes.includes(make)}
                    onChange={() => toggleArrayFilter('makes', make)}
                  />
                ))}
              </FilterSection>

              {/* Body Type */}
              <FilterSection title="Body Type">
                {bodyTypes.map((type) => (
                  <CheckboxFilter
                    key={type}
                    label={type}
                    checked={filters.bodyTypes.includes(type)}
                    onChange={() => toggleArrayFilter('bodyTypes', type)}
                  />
                ))}
              </FilterSection>

              {/* Fuel Type */}
              <FilterSection title="Fuel Type">
                {fuelTypes.map((fuel) => (
                  <CheckboxFilter
                    key={fuel}
                    label={fuel}
                    checked={filters.fuels.includes(fuel)}
                    onChange={() => toggleArrayFilter('fuels', fuel)}
                  />
                ))}
              </FilterSection>

              {/* Transmission */}
              <FilterSection title="Transmission">
                {transmissionTypes.map((tx) => (
                  <CheckboxFilter
                    key={tx}
                    label={tx}
                    checked={filters.transmissions.includes(tx)}
                    onChange={() => toggleArrayFilter('transmissions', tx)}
                  />
                ))}
              </FilterSection>

              {/* Price Range */}
              <FilterSection title="Max Price">
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>$0</span>
                    <span className="text-white font-semibold">
                      ${(filters.priceMax / 1000).toFixed(0)}K
                    </span>
                    <span>$300K</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={300000}
                    step={5000}
                    value={filters.priceMax}
                    onChange={(e) => {
                      setFilters((f) => ({ ...f, priceMax: Number(e.target.value) }));
                      setCurrentPage(1);
                    }}
                    className="w-full h-1.5 bg-[#1e3a50] rounded-full appearance-none cursor-pointer accent-[#3a7bd5]"
                  />
                </div>
              </FilterSection>

              {/* Year Range */}
              <FilterSection title="Year Range">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">From</label>
                    <select
                      value={filters.yearMin}
                      onChange={(e) => {
                        setFilters((f) => ({ ...f, yearMin: Number(e.target.value) }));
                        setCurrentPage(1);
                      }}
                      className="w-full bg-[#12232e] border border-[#1e3a50] rounded-lg px-2 py-2 text-white text-sm focus:outline-none focus:border-[#3a7bd5]"
                    >
                      {[2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023].map((y) => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">To</label>
                    <select
                      value={filters.yearMax}
                      onChange={(e) => {
                        setFilters((f) => ({ ...f, yearMax: Number(e.target.value) }));
                        setCurrentPage(1);
                      }}
                      className="w-full bg-[#12232e] border border-[#1e3a50] rounded-lg px-2 py-2 text-white text-sm focus:outline-none focus:border-[#3a7bd5]"
                    >
                      {[2019, 2020, 2021, 2022, 2023].map((y) => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </FilterSection>

              {/* Max Mileage */}
              <FilterSection title="Max Mileage">
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>0</span>
                    <span className="text-white font-semibold">
                      {filters.mileageMax === 100000 ? 'Any' : `${(filters.mileageMax / 1000).toFixed(0)}K mi`}
                    </span>
                    <span>100K+</span>
                  </div>
                  <input
                    type="range"
                    min={5000}
                    max={100000}
                    step={5000}
                    value={filters.mileageMax}
                    onChange={(e) => {
                      setFilters((f) => ({ ...f, mileageMax: Number(e.target.value) }));
                      setCurrentPage(1);
                    }}
                    className="w-full h-1.5 bg-[#1e3a50] rounded-full appearance-none cursor-pointer accent-[#3a7bd5]"
                  />
                </div>
              </FilterSection>
            </div>
          </aside>

          {/* Sidebar overlay for mobile */}
          {sidebarOpen && (
            <div
              className="fixed inset-0 z-40 bg-black/60 lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
          )}

          {/* ─── Main Content ─── */}
          <div className="flex-1 min-w-0">
            {/* Toolbar */}
            <div className="flex items-center justify-between mb-6 gap-4">
              <button
                className="flex items-center gap-2 lg:hidden px-4 py-2 rounded-lg bg-[#1a3344] border border-[#1e3a50] text-white text-sm font-medium"
                onClick={() => setSidebarOpen(true)}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 010 2H4a1 1 0 01-1-1zm3 6a1 1 0 011-1h10a1 1 0 010 2H7a1 1 0 01-1-1zm3 6a1 1 0 011-1h4a1 1 0 010 2h-4a1 1 0 01-1-1z" />
                </svg>
                Filters
                {hasActiveFilters && (
                  <span className="w-5 h-5 rounded-full bg-[#3a7bd5] text-white text-xs flex items-center justify-center">
                    !
                  </span>
                )}
              </button>

              <div className="flex items-center gap-3 ml-auto">
                <span className="text-gray-400 text-sm hidden sm:block">Sort by:</span>
                <select
                  value={sort}
                  onChange={(e) => {
                    setSort(e.target.value as CarFilters['sort']);
                    setCurrentPage(1);
                  }}
                  className="bg-[#1a3344] border border-[#1e3a50] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-[#3a7bd5] cursor-pointer"
                >
                  {SORT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Active filter tags */}
            {hasActiveFilters && (
              <div className="flex flex-wrap gap-2 mb-5">
                {[...filters.makes, ...filters.bodyTypes, ...filters.fuels, ...filters.transmissions].map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#3a7bd5]/20 border border-[#3a7bd5]/40 text-[#00d2ff] text-xs font-medium"
                  >
                    {tag}
                    <button
                      onClick={() => {
                        if (filters.makes.includes(tag)) toggleArrayFilter('makes', tag);
                        else if (filters.bodyTypes.includes(tag)) toggleArrayFilter('bodyTypes', tag);
                        else if (filters.fuels.includes(tag)) toggleArrayFilter('fuels', tag);
                        else if (filters.transmissions.includes(tag)) toggleArrayFilter('transmissions', tag);
                      }}
                      className="hover:text-white ml-0.5"
                      aria-label={`Remove ${tag} filter`}
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Car grid */}
            {loading ? (
              <LoadingSpinner />
            ) : cars.length === 0 ? (
              <EmptyState onClear={clearFilters} />
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                  {cars.map((car) => (
                    <CarCard key={car.id} car={car} />
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="mt-10 flex items-center justify-center gap-2">
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="px-4 py-2 rounded-lg bg-[#1a3344] border border-[#1e3a50] text-white text-sm disabled:opacity-40 hover:border-[#3a7bd5] transition-colors"
                    >
                      Previous
                    </button>

                    {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((page) => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`w-10 h-10 rounded-lg text-sm font-semibold transition-colors ${
                          currentPage === page
                            ? 'bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white'
                            : 'bg-[#1a3344] border border-[#1e3a50] text-gray-300 hover:border-[#3a7bd5]'
                        }`}
                      >
                        {page}
                      </button>
                    ))}

                    <button
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                      className="px-4 py-2 rounded-lg bg-[#1a3344] border border-[#1e3a50] text-white text-sm disabled:opacity-40 hover:border-[#3a7bd5] transition-colors"
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function FilterSection({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="border-b border-[#1e3a50] pb-5">
      <button
        className="flex items-center justify-between w-full text-white font-semibold text-sm mb-3 hover:text-[#00d2ff] transition-colors"
        onClick={() => setOpen(!open)}
      >
        {title}
        <svg
          className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && <div className="space-y-2">{children}</div>}
    </div>
  );
}

function CheckboxFilter({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="flex items-center gap-2.5 cursor-pointer group">
      <div
        className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
          checked ? 'bg-[#3a7bd5] border-[#3a7bd5]' : 'border-[#1e3a50] group-hover:border-[#3a7bd5]'
        }`}
      >
        {checked && (
          <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="sr-only"
        aria-label={label}
      />
      <span className="text-sm text-gray-400 group-hover:text-white transition-colors">{label}</span>
    </label>
  );
}

function EmptyState({ onClear }: { onClear: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-20 h-20 rounded-2xl bg-[#1a3344] border border-[#1e3a50] flex items-center justify-center mb-5">
        <svg className="w-10 h-10 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-white font-bold text-xl mb-2">No cars found</h3>
      <p className="text-gray-400 text-sm max-w-sm mb-6">
        No vehicles match your current filters. Try adjusting your search criteria.
      </p>
      <button
        onClick={onClear}
        className="px-6 py-3 rounded-lg bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-semibold text-sm"
      >
        Clear All Filters
      </button>
    </div>
  );
}
