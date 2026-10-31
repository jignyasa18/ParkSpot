/**
 * ParkSpot TypeScript Definitions
 * Type-safe interfaces for smart mobility, bookings, and facility management
 */

export type VehicleType = 'CAR' | 'BIKE' | 'EV';

export type SlotStatus = 'AVAILABLE' | 'OCCUPIED' | 'MAINTENANCE';

export type BookingStatus = 'ACTIVE' | 'COMPLETED' | 'CANCELLED';

export interface Coordinates {
  x: number; // Percentage on vector map (0-100)
  y: number; // Percentage on vector map (0-100)
}

export interface ParkingLocation {
  id: number;
  name: string;
  location: string;
  distance: string;
  rate: number;
  rating: number;
  reviews: number;
  available: boolean;
  totalSpots: number;
  freeSpots: number;
  image: string;
  coordinates: Coordinates;
  description: string;
  slots: string[];
}

export interface Booking {
  id: string;
  locationName: string;
  slot: string;
  date: string;
  time: string;
  hours: number;
  total: number;
  status: BookingStatus;
  qr: string;
}

export interface ToastNotification {
  id: number;
  message: string;
  type: 'info' | 'success' | 'error';
}

export interface SearchState {
  location: string;
  date: string;
  time: string;
}

export interface UserProfile {
  id: number;
  name: string;
  email: string;
  role: 'USER' | 'MANAGER' | 'ADMIN';
  vehiclePlate: string;
}
