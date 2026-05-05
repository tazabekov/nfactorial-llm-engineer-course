export interface Car {
  id: number;
  make: string;
  model: string;
  year: number;
  price: number;
  mileage: number;
  fuel: 'Gas' | 'Electric' | 'Hybrid' | 'Diesel';
  transmission: 'Automatic' | 'Manual';
  bodyType: 'Sedan' | 'SUV' | 'Truck' | 'Coupe' | 'Convertible' | 'Wagon' | 'Hatchback';
  color: string;
  image: string;
  description: string;
  vin?: string;
  engine?: string;
  exteriorColor?: string;
  interiorColor?: string;
  features?: string[];
  images?: string[];
  seller?: {
    name: string;
    phone: string;
    email: string;
    location: string;
  };
}

export interface CarFilters {
  make?: string;
  model?: string;
  yearMin?: number;
  yearMax?: number;
  priceMin?: number;
  priceMax?: number;
  mileageMax?: number;
  fuel?: string;
  transmission?: string;
  bodyType?: string;
  sort?: 'price_asc' | 'price_desc' | 'year_desc' | 'year_asc' | 'mileage_asc';
  page?: number;
  limit?: number;
}

export interface CarsResponse {
  cars: Car[];
  total: number;
  page: number;
  totalPages: number;
}

export interface SellFormData {
  // Step 1
  make: string;
  model: string;
  year: string;
  mileage: string;
  vin: string;
  bodyType: string;
  fuel: string;
  transmission: string;
  // Step 2
  condition: string;
  color: string;
  interiorColor: string;
  features: string[];
  // Step 3
  price: string;
  description: string;
  photos: File[];
  // Step 4
  sellerName: string;
  sellerEmail: string;
  sellerPhone: string;
  sellerLocation: string;
}
