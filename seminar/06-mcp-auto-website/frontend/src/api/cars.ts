import axios from 'axios';
import { Car, CarFilters, CarsResponse } from '../types/car';
import { mockCars } from '../data/mockCars';

const API_BASE = 'http://localhost:3001';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 5000,
});

// Helper: filter mock cars client-side
function filterMockCars(filters: CarFilters): CarsResponse {
  let results = [...mockCars];

  if (filters.make) {
    results = results.filter((c) => c.make.toLowerCase() === filters.make!.toLowerCase());
  }
  if (filters.model) {
    results = results.filter((c) => c.model.toLowerCase().includes(filters.model!.toLowerCase()));
  }
  if (filters.yearMin) {
    results = results.filter((c) => c.year >= filters.yearMin!);
  }
  if (filters.yearMax) {
    results = results.filter((c) => c.year <= filters.yearMax!);
  }
  if (filters.priceMin) {
    results = results.filter((c) => c.price >= filters.priceMin!);
  }
  if (filters.priceMax) {
    results = results.filter((c) => c.price <= filters.priceMax!);
  }
  if (filters.mileageMax) {
    results = results.filter((c) => c.mileage <= filters.mileageMax!);
  }
  if (filters.fuel) {
    results = results.filter((c) => c.fuel.toLowerCase() === filters.fuel!.toLowerCase());
  }
  if (filters.transmission) {
    results = results.filter((c) => c.transmission.toLowerCase() === filters.transmission!.toLowerCase());
  }
  if (filters.bodyType) {
    results = results.filter((c) => c.bodyType.toLowerCase() === filters.bodyType!.toLowerCase());
  }

  // Sorting
  if (filters.sort) {
    switch (filters.sort) {
      case 'price_asc':
        results.sort((a, b) => a.price - b.price);
        break;
      case 'price_desc':
        results.sort((a, b) => b.price - a.price);
        break;
      case 'year_desc':
        results.sort((a, b) => b.year - a.year);
        break;
      case 'year_asc':
        results.sort((a, b) => a.year - b.year);
        break;
      case 'mileage_asc':
        results.sort((a, b) => a.mileage - b.mileage);
        break;
    }
  }

  const page = filters.page || 1;
  const limit = filters.limit || 12;
  const total = results.length;
  const totalPages = Math.ceil(total / limit);
  const start = (page - 1) * limit;
  const paginatedCars = results.slice(start, start + limit);

  return { cars: paginatedCars, total, page, totalPages };
}

export async function getCars(filters: CarFilters = {}): Promise<CarsResponse> {
  try {
    const params: Record<string, string | number> = {};
    if (filters.make) params.make = filters.make;
    if (filters.model) params.model = filters.model;
    if (filters.yearMin) params.yearMin = filters.yearMin;
    if (filters.yearMax) params.yearMax = filters.yearMax;
    if (filters.priceMin) params.priceMin = filters.priceMin;
    if (filters.priceMax) params.priceMax = filters.priceMax;
    if (filters.mileageMax) params.mileageMax = filters.mileageMax;
    if (filters.fuel) params.fuel = filters.fuel;
    if (filters.transmission) params.transmission = filters.transmission;
    if (filters.bodyType) params.bodyType = filters.bodyType;
    if (filters.sort) params.sort = filters.sort;
    if (filters.page) params.page = filters.page;
    if (filters.limit) params.limit = filters.limit;

    const response = await api.get<CarsResponse>('/api/cars', { params });
    return response.data;
  } catch {
    // Fall back to mock data
    return filterMockCars(filters);
  }
}

export async function getCarById(id: number): Promise<Car | null> {
  try {
    const response = await api.get<Car>(`/api/cars/${id}`);
    return response.data;
  } catch {
    // Fall back to mock data
    const car = mockCars.find((c) => c.id === id);
    return car || null;
  }
}

export async function createCarListing(data: Partial<Car>): Promise<Car> {
  try {
    const response = await api.post<Car>('/api/cars', data);
    return response.data;
  } catch {
    // Simulate success with mock response
    const newCar: Car = {
      id: Math.floor(Math.random() * 10000) + 100,
      make: data.make || '',
      model: data.model || '',
      year: data.year || new Date().getFullYear(),
      price: data.price || 0,
      mileage: data.mileage || 0,
      fuel: data.fuel || 'Gas',
      transmission: data.transmission || 'Automatic',
      bodyType: data.bodyType || 'Sedan',
      color: data.color || '',
      image: 'https://images.unsplash.com/photo-1555215695-3004980ad54e?w=800',
      description: data.description || '',
    };
    return newCar;
  }
}

export function getSimilarCars(car: Car, limit = 3): Car[] {
  return mockCars
    .filter(
      (c) =>
        c.id !== car.id &&
        (c.make === car.make ||
          c.bodyType === car.bodyType ||
          Math.abs(c.price - car.price) < 30000)
    )
    .slice(0, limit);
}
