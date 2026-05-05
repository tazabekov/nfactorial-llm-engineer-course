import { Link } from 'react-router-dom';
import { Car } from '../types/car';

interface CarCardProps {
  car: Car;
}

function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(price);
}

function formatMileage(mileage: number): string {
  return new Intl.NumberFormat('en-US').format(mileage) + ' mi';
}

export default function CarCard({ car }: CarCardProps) {
  const fuelColor: Record<string, string> = {
    Electric: 'text-green-400',
    Gas: 'text-orange-400',
    Hybrid: 'text-teal-400',
    Diesel: 'text-yellow-400',
  };

  return (
    <Link
      to={`/cars/${car.id}`}
      className="group block bg-[#1a3344] rounded-xl border border-[#1e3a50] overflow-hidden hover:scale-[1.02] hover:border-[#3a7bd5]/50 hover:shadow-xl hover:shadow-[#3a7bd5]/10 transition-all duration-300"
      aria-label={`View ${car.year} ${car.make} ${car.model}`}
    >
      {/* Image */}
      <div className="relative h-48 overflow-hidden bg-[#12232e]">
        <img
          src={car.image}
          alt={`${car.year} ${car.make} ${car.model}`}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          width={400}
          height={192}
          loading="lazy"
          onError={(e) => {
            (e.target as HTMLImageElement).src =
              'https://images.unsplash.com/photo-1555215695-3004980ad54e?w=800';
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#1a3344]/80 via-transparent to-transparent" />
        {/* Fuel badge */}
        <div
          className={`absolute top-3 right-3 px-2 py-1 rounded-md bg-[#0B0C10]/80 backdrop-blur-sm text-xs font-semibold ${fuelColor[car.fuel] || 'text-gray-300'}`}
        >
          {car.fuel}
        </div>
        {/* Transmission badge */}
        <div className="absolute top-3 left-3 px-2 py-1 rounded-md bg-[#0B0C10]/80 backdrop-blur-sm text-xs font-medium text-gray-300">
          {car.transmission === 'Automatic' ? 'Auto' : 'Manual'}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="mb-2">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-0.5">
            {car.make}
          </p>
          <h3 className="text-white font-bold text-base leading-tight group-hover:text-[#00d2ff] transition-colors">
            {car.year} {car.model}
          </h3>
        </div>

        {/* Price */}
        <p className="text-2xl font-bold bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] bg-clip-text text-transparent mb-3">
          {formatPrice(car.price)}
        </p>

        {/* Specs */}
        <div className="grid grid-cols-3 gap-2 pt-3 border-t border-[#1e3a50]">
          <div className="flex flex-col items-center gap-0.5">
            <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span className="text-white text-xs font-medium">{formatMileage(car.mileage)}</span>
          </div>
          <div className="flex flex-col items-center gap-0.5">
            <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span className="text-white text-xs font-medium">{car.fuel}</span>
          </div>
          <div className="flex flex-col items-center gap-0.5">
            <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-white text-xs font-medium">{car.bodyType}</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
