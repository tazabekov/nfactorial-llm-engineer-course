import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getCarById, getSimilarCars } from '../api/cars';
import { Car } from '../types/car';
import CarCard from '../components/CarCard';
import LoadingSpinner from '../components/LoadingSpinner';

function formatPrice(price: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(price);
}
function formatMileage(m: number) {
  return new Intl.NumberFormat('en-US').format(m) + ' miles';
}

type Tab = 'description' | 'specs' | 'features';

export default function CarDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [car, setCar] = useState<Car | null>(null);
  const [similarCars, setSimilarCars] = useState<Car[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [selectedImage, setSelectedImage] = useState(0);
  const [activeTab, setActiveTab] = useState<Tab>('description');
  const [saved, setSaved] = useState(false);
  const [contactOpen, setContactOpen] = useState(false);

  useEffect(() => {
    async function load() {
      if (!id) return;
      setLoading(true);
      const result = await getCarById(Number(id));
      if (!result) {
        setNotFound(true);
      } else {
        setCar(result);
        setSimilarCars(getSimilarCars(result));
      }
      setLoading(false);
    }
    load();
    window.scrollTo(0, 0);
  }, [id]);

  if (loading) return <LoadingSpinner fullPage />;

  if (notFound || !car) {
    return (
      <div className="min-h-screen bg-[#12232e] flex flex-col items-center justify-center gap-4 font-lato pt-16">
        <div className="w-20 h-20 rounded-2xl bg-[#1a3344] border border-[#1e3a50] flex items-center justify-center">
          <svg className="w-10 h-10 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h1 className="text-white font-bold text-2xl">Car Not Found</h1>
        <p className="text-gray-400">This listing may have been removed or doesn't exist.</p>
        <button
          onClick={() => navigate('/cars')}
          className="px-6 py-3 rounded-lg bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-semibold"
        >
          Browse Cars
        </button>
      </div>
    );
  }

  const images = car.images?.length ? car.images : [car.image, car.image, car.image, car.image, car.image];

  const specs = [
    { label: 'Year', value: car.year },
    { label: 'Make', value: car.make },
    { label: 'Model', value: car.model },
    { label: 'Body Type', value: car.bodyType },
    { label: 'Mileage', value: formatMileage(car.mileage) },
    { label: 'Fuel Type', value: car.fuel },
    { label: 'Transmission', value: car.transmission },
    { label: 'Color', value: car.color },
    { label: 'Engine', value: car.engine || '—' },
    { label: 'Exterior Color', value: car.exteriorColor || car.color },
    { label: 'Interior Color', value: car.interiorColor || '—' },
    { label: 'VIN', value: car.vin || '—' },
  ];

  return (
    <div className="min-h-screen bg-[#12232e] font-lato pt-16">
      {/* Breadcrumb */}
      <div className="bg-[#0B0C10] border-b border-[#1e3a50] py-3 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex items-center gap-2 text-sm text-gray-400">
          <Link to="/" className="hover:text-white transition-colors">Home</Link>
          <span>/</span>
          <Link to="/cars" className="hover:text-white transition-colors">Cars</Link>
          <span>/</span>
          <span className="text-white">{car.year} {car.make} {car.model}</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* ─── Left: Gallery + Details ─── */}
          <div className="lg:col-span-2 space-y-6">
            {/* Image Gallery */}
            <div className="space-y-3">
              {/* Main image */}
              <div className="relative h-72 sm:h-96 rounded-2xl overflow-hidden bg-[#1a3344]">
                <img
                  src={images[selectedImage]}
                  alt={`${car.year} ${car.make} ${car.model}`}
                  className="w-full h-full object-cover transition-all duration-500"
                  width={800}
                  height={450}
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1555215695-3004980ad54e?w=800';
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />
                {/* Nav arrows */}
                <button
                  onClick={() => setSelectedImage((i) => (i - 1 + images.length) % images.length)}
                  className="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 backdrop-blur-sm flex items-center justify-center text-white hover:bg-black/70 transition-colors"
                  aria-label="Previous image"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <button
                  onClick={() => setSelectedImage((i) => (i + 1) % images.length)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 backdrop-blur-sm flex items-center justify-center text-white hover:bg-black/70 transition-colors"
                  aria-label="Next image"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                {/* Image counter */}
                <div className="absolute bottom-4 right-4 px-3 py-1 rounded-full bg-black/60 backdrop-blur-sm text-white text-xs font-medium">
                  {selectedImage + 1} / {images.length}
                </div>
              </div>

              {/* Thumbnails */}
              <div className="grid grid-cols-5 gap-2">
                {images.slice(0, 5).map((img, i) => (
                  <button
                    key={i}
                    onClick={() => setSelectedImage(i)}
                    className={`relative h-16 rounded-xl overflow-hidden border-2 transition-all ${
                      selectedImage === i
                        ? 'border-[#3a7bd5] scale-[1.03]'
                        : 'border-[#1e3a50] opacity-60 hover:opacity-100 hover:border-[#3a7bd5]/50'
                    }`}
                    aria-label={`View image ${i + 1}`}
                  >
                    <img
                      src={img}
                      alt={`View ${i + 1}`}
                      className="w-full h-full object-cover"
                      width={160}
                      height={64}
                      loading="lazy"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1555215695-3004980ad54e?w=800';
                      }}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Tabs */}
            <div className="bg-[#1a3344] rounded-2xl border border-[#1e3a50] overflow-hidden">
              <div className="flex border-b border-[#1e3a50]">
                {(['description', 'specs', 'features'] as Tab[]).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`flex-1 py-4 text-sm font-semibold capitalize transition-colors ${
                      activeTab === tab
                        ? 'text-white border-b-2 border-[#3a7bd5] -mb-px bg-[#12232e]/40'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              <div className="p-6">
                {activeTab === 'description' && (
                  <p className="text-gray-300 leading-relaxed">{car.description}</p>
                )}

                {activeTab === 'specs' && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {specs.map((spec) => (
                      <div
                        key={spec.label}
                        className="flex items-center justify-between py-3 border-b border-[#1e3a50] last:border-0"
                      >
                        <span className="text-gray-400 text-sm">{spec.label}</span>
                        <span className="text-white text-sm font-medium">{spec.value}</span>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'features' && (
                  <div>
                    {car.features && car.features.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {car.features.map((feature) => (
                          <div key={feature} className="flex items-center gap-2.5 py-2">
                            <div className="w-5 h-5 rounded-full bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] flex items-center justify-center flex-shrink-0">
                              <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                              </svg>
                            </div>
                            <span className="text-gray-300 text-sm">{feature}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-gray-400">No features listed.</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ─── Right: Sidebar ─── */}
          <div className="space-y-4">
            {/* Price card */}
            <div className="bg-[#1a3344] rounded-2xl border border-[#1e3a50] p-6 sticky top-20">
              <div className="mb-1">
                <span className="text-gray-400 text-sm">{car.make}</span>
              </div>
              <h1 className="text-white font-black text-2xl font-lato mb-2">
                {car.year} {car.model}
              </h1>
              <p className="text-3xl font-black bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] bg-clip-text text-transparent mb-5">
                {formatPrice(car.price)}
              </p>

              {/* Quick specs */}
              <div className="grid grid-cols-2 gap-3 mb-5">
                {[
                  { label: 'Mileage', value: formatMileage(car.mileage) },
                  { label: 'Fuel', value: car.fuel },
                  { label: 'Transmission', value: car.transmission },
                  { label: 'Body', value: car.bodyType },
                ].map((spec) => (
                  <div key={spec.label} className="bg-[#12232e] rounded-xl p-3 border border-[#1e3a50]">
                    <p className="text-gray-400 text-xs mb-0.5">{spec.label}</p>
                    <p className="text-white text-sm font-semibold">{spec.value}</p>
                  </div>
                ))}
              </div>

              {/* CTA Buttons */}
              <div className="space-y-3">
                <button
                  onClick={() => setContactOpen(true)}
                  className="w-full py-3.5 rounded-xl bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-bold text-base hover:opacity-90 transition-opacity shadow-lg shadow-[#3a7bd5]/30"
                >
                  Contact Seller
                </button>
                <button
                  onClick={() => setSaved(!saved)}
                  className={`w-full py-3.5 rounded-xl border font-bold text-base transition-all ${
                    saved
                      ? 'bg-[#3a7bd5]/20 border-[#3a7bd5] text-[#00d2ff]'
                      : 'bg-[#12232e] border-[#1e3a50] text-gray-300 hover:border-[#3a7bd5] hover:text-white'
                  }`}
                >
                  {saved ? 'Saved to Favorites' : 'Save to Favorites'}
                </button>
              </div>

              {/* Seller info */}
              {car.seller && (
                <div className="mt-5 pt-5 border-t border-[#1e3a50]">
                  <p className="text-gray-400 text-xs font-semibold uppercase tracking-wide mb-3">Listed by</p>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#3a7bd5] to-[#00d2ff] flex items-center justify-center text-white font-bold text-sm">
                      {car.seller.name[0]}
                    </div>
                    <div>
                      <p className="text-white font-semibold text-sm">{car.seller.name}</p>
                      <p className="text-gray-400 text-xs">{car.seller.location}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ─── Similar Cars ─── */}
        {similarCars.length > 0 && (
          <div className="mt-16">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-white font-black text-2xl font-lato">Similar Cars</h2>
              <Link to="/cars" className="text-[#00d2ff] text-sm font-semibold hover:underline">
                View All
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {similarCars.map((sc) => (
                <CarCard key={sc.id} car={sc} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ─── Contact Modal ─── */}
      {contactOpen && car.seller && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
          onClick={(e) => { if (e.target === e.currentTarget) setContactOpen(false); }}
        >
          <div className="bg-[#1a3344] border border-[#1e3a50] rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-white font-bold text-xl">Contact Seller</h3>
              <button
                onClick={() => setContactOpen(false)}
                className="text-gray-400 hover:text-white p-1"
                aria-label="Close"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="bg-[#12232e] rounded-xl p-4 mb-5 border border-[#1e3a50]">
              <p className="text-gray-400 text-sm">Regarding</p>
              <p className="text-white font-semibold">{car.year} {car.make} {car.model} — {formatPrice(car.price)}</p>
            </div>

            <div className="space-y-3 mb-5">
              <ContactItem icon="phone" label="Phone" value={car.seller.phone} />
              <ContactItem icon="email" label="Email" value={car.seller.email} />
              <ContactItem icon="location" label="Location" value={car.seller.location} />
            </div>

            <div className="space-y-3">
              <textarea
                placeholder="Write a message to the seller..."
                rows={3}
                className="w-full bg-[#12232e] border border-[#1e3a50] rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-[#3a7bd5] resize-none"
              />
              <button
                onClick={() => setContactOpen(false)}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-bold hover:opacity-90 transition-opacity"
              >
                Send Message
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ContactItem({ icon, label, value }: { icon: string; label: string; value: string }) {
  const icons: Record<string, React.ReactNode> = {
    phone: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
      </svg>
    ),
    email: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
    location: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  };

  return (
    <div className="flex items-center gap-3 bg-[#12232e] rounded-xl p-3 border border-[#1e3a50]">
      <div className="w-8 h-8 rounded-lg bg-[#3a7bd5]/20 flex items-center justify-center text-[#3a7bd5]">
        {icons[icon]}
      </div>
      <div>
        <p className="text-gray-400 text-xs">{label}</p>
        <p className="text-white text-sm font-medium">{value}</p>
      </div>
    </div>
  );
}
