import { Router, Request, Response, NextFunction } from 'express';
import { cars, Car } from '../data/cars';

const router = Router();

// In-memory store that starts from the seeded data
let carStore: Car[] = [...cars];
let nextId = carStore.length + 1;

// ─── Helpers ────────────────────────────────────────────────────────────────

function parseIntParam(value: unknown, fallback: number): number {
  const parsed = parseInt(String(value), 10);
  return isNaN(parsed) ? fallback : parsed;
}

function parseFloatParam(value: unknown): number | undefined {
  if (value === undefined || value === '') return undefined;
  const parsed = parseFloat(String(value));
  return isNaN(parsed) ? undefined : parsed;
}

// ─── GET /api/cars/makes  (must be declared before /:id) ────────────────────
router.get('/makes', (_req: Request, res: Response) => {
  const makes = [...new Set(carStore.map((c) => c.make))].sort();
  res.json({ makes });
});

// ─── GET /api/cars/stats  (must be declared before /:id) ────────────────────
router.get('/stats', (_req: Request, res: Response) => {
  const totalListings = carStore.length;
  const avgPrice =
    totalListings === 0
      ? 0
      : Math.round(carStore.reduce((sum, c) => sum + c.price, 0) / totalListings);
  res.json({
    totalListings,
    avgPrice,
    totalSold: 1847,   // simulated historical figure
    happyBuyers: 2134, // simulated historical figure
  });
});

// ─── GET /api/cars ────────────────────────────────────────────────────────────
router.get('/', (req: Request, res: Response) => {
  const {
    make,
    model,
    fuel,
    transmission,
    bodyType,
    sort,
  } = req.query as Record<string, string | undefined>;

  const yearMin = parseFloatParam(req.query.yearMin);
  const yearMax = parseFloatParam(req.query.yearMax);
  const priceMin = parseFloatParam(req.query.priceMin);
  const priceMax = parseFloatParam(req.query.priceMax);
  const page = parseIntParam(req.query.page, 1);
  const limit = parseIntParam(req.query.limit, 12);

  let result = [...carStore];

  // Filtering
  if (make) {
    result = result.filter((c) => c.make.toLowerCase() === make.toLowerCase());
  }
  if (model) {
    result = result.filter((c) => c.model.toLowerCase().includes(model.toLowerCase()));
  }
  if (fuel) {
    result = result.filter((c) => c.fuel.toLowerCase() === fuel.toLowerCase());
  }
  if (transmission) {
    result = result.filter(
      (c) => c.transmission.toLowerCase() === transmission.toLowerCase(),
    );
  }
  if (bodyType) {
    result = result.filter((c) => c.bodyType.toLowerCase() === bodyType.toLowerCase());
  }
  if (yearMin !== undefined) {
    result = result.filter((c) => c.year >= yearMin);
  }
  if (yearMax !== undefined) {
    result = result.filter((c) => c.year <= yearMax);
  }
  if (priceMin !== undefined) {
    result = result.filter((c) => c.price >= priceMin);
  }
  if (priceMax !== undefined) {
    result = result.filter((c) => c.price <= priceMax);
  }

  // Sorting
  switch (sort) {
    case 'price_asc':
      result.sort((a, b) => a.price - b.price);
      break;
    case 'price_desc':
      result.sort((a, b) => b.price - a.price);
      break;
    case 'year_desc':
      result.sort((a, b) => b.year - a.year);
      break;
    case 'mileage_asc':
      result.sort((a, b) => a.mileage - b.mileage);
      break;
    default:
      // Default: newest listings first
      result.sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
      );
  }

  // Pagination
  const total = result.length;
  const totalPages = Math.ceil(total / limit);
  const safePage = Math.min(Math.max(page, 1), totalPages || 1);
  const offset = (safePage - 1) * limit;
  const paginated = result.slice(offset, offset + limit);

  res.json({
    cars: paginated,
    total,
    page: safePage,
    totalPages,
  });
});

// ─── GET /api/cars/:id ────────────────────────────────────────────────────────
router.get('/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    res.status(400).json({ error: 'Invalid car ID' });
    return;
  }
  const car = carStore.find((c) => c.id === id);
  if (!car) {
    res.status(404).json({ error: `Car with id ${id} not found` });
    return;
  }
  res.json(car);
});

// ─── POST /api/cars ────────────────────────────────────────────────────────
router.post('/', (req: Request, res: Response, next: NextFunction) => {
  try {
    const body = req.body as Partial<Omit<Car, 'id' | 'createdAt'>>;

    // Required field validation
    const requiredFields: Array<keyof Omit<Car, 'id' | 'createdAt'>> = [
      'make',
      'model',
      'year',
      'price',
      'mileage',
      'fuel',
      'transmission',
      'bodyType',
      'color',
      'image',
      'description',
      'features',
      'location',
      'seller',
      'condition',
    ];

    const missingFields = requiredFields.filter(
      (field) => body[field] === undefined || body[field] === null || body[field] === '',
    );

    if (missingFields.length > 0) {
      res.status(422).json({
        error: 'Validation failed',
        missingFields,
      });
      return;
    }

    // Enum validation
    const validFuels: Car['fuel'][] = ['Gas', 'Electric', 'Hybrid', 'Diesel'];
    if (!validFuels.includes(body.fuel as Car['fuel'])) {
      res.status(422).json({
        error: 'Validation failed',
        message: `fuel must be one of: ${validFuels.join(', ')}`,
      });
      return;
    }

    const validTransmissions: Car['transmission'][] = ['Automatic', 'Manual'];
    if (!validTransmissions.includes(body.transmission as Car['transmission'])) {
      res.status(422).json({
        error: 'Validation failed',
        message: `transmission must be one of: ${validTransmissions.join(', ')}`,
      });
      return;
    }

    const validBodyTypes: Car['bodyType'][] = [
      'Sedan', 'SUV', 'Truck', 'Coupe', 'Convertible', 'Wagon', 'Hatchback',
    ];
    if (!validBodyTypes.includes(body.bodyType as Car['bodyType'])) {
      res.status(422).json({
        error: 'Validation failed',
        message: `bodyType must be one of: ${validBodyTypes.join(', ')}`,
      });
      return;
    }

    const validConditions: Car['condition'][] = ['New', 'Used', 'Certified Pre-Owned'];
    if (!validConditions.includes(body.condition as Car['condition'])) {
      res.status(422).json({
        error: 'Validation failed',
        message: `condition must be one of: ${validConditions.join(', ')}`,
      });
      return;
    }

    // Numeric validation
    const year = Number(body.year);
    const price = Number(body.price);
    const mileage = Number(body.mileage);

    if (isNaN(year) || year < 1886 || year > new Date().getFullYear() + 1) {
      res.status(422).json({ error: 'Validation failed', message: 'year is invalid' });
      return;
    }
    if (isNaN(price) || price < 0) {
      res.status(422).json({ error: 'Validation failed', message: 'price must be a non-negative number' });
      return;
    }
    if (isNaN(mileage) || mileage < 0) {
      res.status(422).json({ error: 'Validation failed', message: 'mileage must be a non-negative number' });
      return;
    }

    // Seller object validation
    const seller = body.seller as Car['seller'];
    if (
      typeof seller !== 'object' ||
      !seller.name ||
      !seller.phone ||
      !seller.email
    ) {
      res.status(422).json({
        error: 'Validation failed',
        message: 'seller must include name, phone, and email',
      });
      return;
    }

    // Features array validation
    if (!Array.isArray(body.features)) {
      res.status(422).json({
        error: 'Validation failed',
        message: 'features must be an array of strings',
      });
      return;
    }

    const newCar: Car = {
      id: nextId++,
      make: String(body.make),
      model: String(body.model),
      year,
      price,
      mileage,
      fuel: body.fuel as Car['fuel'],
      transmission: body.transmission as Car['transmission'],
      bodyType: body.bodyType as Car['bodyType'],
      color: String(body.color),
      image: String(body.image),
      description: String(body.description),
      features: body.features as string[],
      location: String(body.location),
      seller,
      createdAt: new Date().toISOString(),
      condition: body.condition as Car['condition'],
    };

    carStore.push(newCar);
    res.status(201).json(newCar);
  } catch (err) {
    next(err);
  }
});

export default router;
