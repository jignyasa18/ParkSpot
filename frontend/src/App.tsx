import React, { useState, useCallback, useMemo } from 'react';
import { 
  ParkingLocation, 
  Booking, 
  ToastNotification, 
  SearchState, 
  UserProfile 
} from './types';

/* ═══════════════════════════════════════════════════════════════
   PRE-SEEDED LOCATIONS DATA
   ═══════════════════════════════════════════════════════════════ */
const INITIAL_LOCATIONS: ParkingLocation[] = [
  {
    id: 1,
    name: "Bandra Station Parking",
    location: "Bandra (W), Mumbai",
    distance: "0.8 km",
    rate: 80,
    rating: 4.6,
    reviews: 1240,
    available: true,
    totalSpots: 48,
    freeSpots: 18,
    image: "https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80",
    coordinates: { x: 74, y: 35 },
    description: "Multi-level covered basement parking with automated boom barrier entry and CCTV surveillance.",
    slots: ["A01", "A02", "A03", "A04", "B01", "B02", "B03", "E01"]
  },
  {
    id: 2,
    name: "Linking Road Parking",
    location: "Bandra (W), Mumbai",
    distance: "1.2 km",
    rate: 100,
    rating: 4.4,
    reviews: 860,
    available: true,
    totalSpots: 32,
    freeSpots: 9,
    image: "https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80",
    coordinates: { x: 88, y: 22 },
    description: "Secure open tree-shaded parking bay ideal for shopping on Linking Road with dedicated valet staff.",
    slots: ["L01", "L02", "L03", "L04", "L05", "E02"]
  },
  {
    id: 3,
    name: "Pali Hill Parking",
    location: "Bandra (W), Mumbai",
    distance: "1.5 km",
    rate: 90,
    rating: 4.5,
    reviews: 980,
    available: true,
    totalSpots: 40,
    freeSpots: 14,
    image: "https://images.unsplash.com/photo-1573348722427-f1d6819fdf98?auto=format&fit=crop&w=800&q=80",
    coordinates: { x: 65, y: 68 },
    description: "Premium residential & dining parking with EV 50kW fast charger and 24/7 manned security.",
    slots: ["P01", "P02", "P03", "P04", "E03"]
  }
];

const INITIAL_BOOKINGS: Booking[] = [
  {
    id: "BK-9021",
    locationName: "Bandra Station Parking",
    slot: "A02",
    date: "Today, Oct 31",
    time: "10:00 AM - 12:00 PM",
    hours: 2,
    total: 160,
    status: "ACTIVE",
    qr: "PS-BANDRA-A02-9021"
  }
];

/* ═══════════════════════════════════════════════════════════════
   TOAST COMPONENT
   ═══════════════════════════════════════════════════════════════ */
interface ToastProps {
  toasts: ToastNotification[];
  onDismiss: (id: number) => void;
}

const ToastContainer: React.FC<ToastProps> = ({ toasts, onDismiss }) => {
  return (
    <div className="fixed top-5 right-5 z-[100] flex flex-col gap-2 max-w-sm pointer-events-none">
      {toasts.map(t => (
        <div key={t.id} className="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl bg-white border border-[#E8E1D5] shadow-xl text-xs text-[#1A1815] animate-fade-up">
          <i className={`fa-solid ${t.type === "success" ? "fa-circle-check text-green-700" : t.type === "error" ? "fa-circle-exclamation text-red-700" : "fa-circle-info text-[#1C3B37]"} text-sm`}></i>
          <span className="flex-1 font-semibold">{t.message}</span>
          <button onClick={() => onDismiss(t.id)} className="text-[#706A62] hover:text-[#1A1815]"><i className="fa-solid fa-xmark"></i></button>
        </div>
      ))}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   MAIN REACT + TYPESCRIPT APPLICATION
   ═══════════════════════════════════════════════════════════════ */
export const App: React.FC = () => {
  // State typed with TypeScript interfaces
  const [locations] = useState<ParkingLocation[]>(INITIAL_LOCATIONS);
  const [activePinId, setActivePinId] = useState<number>(1);
  const [wishlist, setWishlist] = useState<Record<number, boolean>>({ 1: false, 2: false, 3: false });
  const [toasts, setToasts] = useState<ToastNotification[]>([]);
  
  // Search parameters
  const [search, setSearch] = useState<SearchState>({
    location: "Bandra, Mumbai",
    date: "Oct 31, 2026",
    time: "10:00 AM"
  });

  // Booking & Modals State
  const [bookingModalLocation, setBookingModalLocation] = useState<ParkingLocation | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<string>("A01");
  const [durationHours, setDurationHours] = useState<number>(2);
  const [userBookings, setUserBookings] = useState<Booking[]>(INITIAL_BOOKINGS);
  const [passesModalOpen, setPassesModalOpen] = useState<boolean>(false);
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);

  const addToast = useCallback((message: string, type: 'info' | 'success' | 'error' = "info") => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, message, type }]);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const toggleWishlist = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setWishlist(prev => {
      const next = !prev[id];
      addToast(next ? "Saved to your saved parking spots!" : "Removed from saved parking spots.", "info");
      return { ...prev, [id]: next };
    });
  };

  const handleBookNow = (loc: ParkingLocation) => {
    setBookingModalLocation(loc);
    setSelectedSlot(loc.slots[0] || "A01");
  };

  const handleConfirmReservation = () => {
    if (!bookingModalLocation) return;
    const total = bookingModalLocation.rate * durationHours;
    const newBk: Booking = {
      id: `BK-${Math.floor(1000 + Math.random() * 9000)}`,
      locationName: bookingModalLocation.name,
      slot: selectedSlot,
      date: search.date,
      time: `${search.time} (${durationHours} Hours)`,
      hours: durationHours,
      total: total,
      status: "ACTIVE",
      qr: `PS-${bookingModalLocation.name.substring(0, 4).toUpperCase()}-${selectedSlot}-${Math.floor(1000 + Math.random() * 9000)}`
    };

    setUserBookings(prev => [newBk, ...prev]);
    setBookingModalLocation(null);
    addToast(`Reservation confirmed for ${selectedSlot} at ${bookingModalLocation.name}!`, "success");
    setPassesModalOpen(true);
  };

  const activePinLocation = useMemo(() => {
    return locations.find(l => l.id === activePinId) || locations[0];
  }, [locations, activePinId]);

  return (
    <div className="min-h-screen bg-[#F5F0E8] text-[#1A1815] flex flex-col">
      {/* 1. Header */}
      <header className="bg-[#0f1d22] text-white border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="cursor-pointer" onClick={() => { setActivePinId(1); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
            <span className="text-2xl sm:text-3xl font-serif font-normal tracking-tight text-white">ParkSpot</span>
          </div>

          <nav className="hidden md:flex items-center gap-9 text-xs sm:text-sm text-slate-300 font-normal">
            <button onClick={() => window.scrollTo({ top: 480, behavior: 'smooth' })} className="hover:text-white transition">Find Parking</button>
            <button onClick={() => window.scrollTo({ top: 360, behavior: 'smooth' })} className="hover:text-white transition">How it Works</button>
            <button onClick={() => addToast("Parking owners portal: List your space and earn ₹15,000/mo.", "info")} className="hover:text-white transition">For Owners</button>
            <button onClick={() => addToast("ParkSpot is India's premier contactless smart parking network.", "info")} className="hover:text-white transition">About</button>
          </nav>

          <div className="flex items-center gap-3">
            <button 
              onClick={() => setPassesModalOpen(true)}
              className="text-xs text-slate-300 hover:text-white flex items-center gap-1.5 px-3 py-1.5 rounded-full hover:bg-white/5 transition">
              <i className="fa-solid fa-ticket text-xs"></i>
              <span className="hidden sm:inline">My Passes</span>
              <span className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold flex items-center justify-center">
                {userBookings.length}
              </span>
            </button>

            <button 
              onClick={() => setAuthModalOpen(true)}
              className="btn-outline-white px-5 py-2 text-xs sm:text-sm font-medium">
              Sign in
            </button>
          </div>
        </div>
      </header>

      {/* 2. Hero Section */}
      <section className="bg-[#0f1d22] text-white relative overflow-hidden pt-10 pb-16 border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-12 gap-8 items-center min-h-[460px]">
          <div className="lg:col-span-6 z-10 space-y-4">
            <div className="flex items-center gap-3 text-xs tracking-[0.2em] font-medium text-slate-400 uppercase">
              <span>PARK</span>
              <span>•</span>
              <span>BOOK</span>
              <span>•</span>
              <span>DRIVE</span>
              <div className="h-0.5 w-12 bg-slate-700 ml-1"></div>
            </div>

            <h1 className="text-4xl sm:text-6xl font-serif font-normal text-white leading-[1.12] tracking-tight">
              Find your perfect<br />parking spot.
            </h1>

            <p className="text-sm sm:text-base text-slate-300 max-w-md font-light leading-relaxed">
              Discover, compare and book secure parking spaces near your destination.
            </p>
          </div>

          <div className="lg:col-span-6 relative h-[360px] sm:h-[420px] w-full rounded-2xl overflow-hidden bg-[#122329]">
            <svg className="w-full h-full absolute inset-0 opacity-80" preserveAspectRatio="none" viewBox="0 0 100 100">
              <path d="M 85,0 Q 82,30 92,60 L 100,70 L 100,0 Z" fill="#18363f" opacity="0.9" />
              <path d="M 0,0 L 0,35 Q 20,40 10,75 L 0,85 Z" fill="#18363f" opacity="0.5" />
              <line x1="0" y1="28" x2="100" y2="28" stroke="#22404b" strokeWidth="2" />
              <line x1="0" y1="58" x2="100" y2="58" stroke="#22404b" strokeWidth="2.5" />
              <line x1="45" y1="0" x2="45" y2="100" stroke="#22404b" strokeWidth="2.5" />
              <line x1="75" y1="0" x2="75" y2="100" stroke="#22404b" strokeWidth="2" />
            </svg>

            {locations.map(loc => {
              const isActive = activePinId === loc.id;
              return (
                <button 
                  key={loc.id}
                  onClick={() => setActivePinId(loc.id)}
                  style={{ left: `${loc.coordinates.x}%`, top: `${loc.coordinates.y}%` }}
                  className={`absolute -translate-x-1/2 -translate-y-1/2 rounded-full flex items-center justify-center transition-all z-20 ${
                    isActive
                      ? "w-8 h-8 bg-[#1f3f39] border-2 border-emerald-400 text-emerald-300 shadow-xl map-pulse-active"
                      : "w-7 h-7 bg-[#172b32] border border-white/40 text-slate-300 hover:border-white hover:scale-110"
                  }`}>
                  <span className="text-[11px] font-bold font-mono">P</span>
                </button>
              );
            })}

            {activePinLocation && (
              <div 
                style={{
                  top: `${Math.max(15, activePinLocation.coordinates.y - 12)}%`, 
                  left: `${Math.min(70, Math.max(30, activePinLocation.coordinates.x))}%`
                }}
                className="absolute -translate-x-1/2 -translate-y-1/2 z-30 bg-white text-[#1A1815] rounded-2xl p-3 shadow-2xl border border-white/40 w-64 sm:w-72 animate-fade-up">
                <div className="flex gap-3">
                  <img 
                    src={activePinLocation.image} 
                    alt={activePinLocation.name}
                    className="w-20 h-20 rounded-xl object-cover flex-shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <h4 className="text-xs font-bold text-[#1A1815] truncate">{activePinLocation.name}</h4>
                      <button onClick={(e) => { e.stopPropagation(); setActivePinId(activePinLocation.id === 1 ? 2 : 1); }} className="text-slate-400 hover:text-black text-xs">
                        <i className="fa-solid fa-xmark"></i>
                      </button>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-0.5 flex items-center gap-1">
                      <i className="fa-solid fa-location-dot text-[9px]"></i> {activePinLocation.location}
                    </p>
                    <p className="text-sm font-bold text-[#1A1815] mt-1.5">₹{activePinLocation.rate} <span className="text-[10px] text-slate-500 font-normal">/ hour</span></p>
                    <button 
                      onClick={() => handleBookNow(activePinLocation)}
                      className="btn-teal mt-1.5 w-full py-1.5 text-[11px]">
                      Book Now
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Floating Search Bar */}
        <div className="max-w-7xl mx-auto px-6 mt-6">
          <div className="bg-white text-[#1A1815] rounded-2xl p-3 sm:p-3.5 shadow-2xl border border-white/60 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 max-w-4xl">
            <div className="flex items-center gap-3 px-3 py-2 flex-1 border-b md:border-b-0 md:border-r border-slate-200">
              <i className="fa-solid fa-location-dot text-slate-400 text-sm"></i>
              <div className="flex-1">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Location</p>
                <input 
                  type="text" 
                  value={search.location} 
                  onChange={e => setSearch(prev => ({ ...prev, location: e.target.value }))}
                  placeholder="e.g. Bandra, Mumbai"
                  className="w-full text-xs font-semibold text-[#1A1815] focus:outline-none bg-transparent"
                />
              </div>
              <i className="fa-solid fa-chevron-down text-[10px] text-slate-400"></i>
            </div>

            <div className="flex items-center gap-3 px-3 py-2 flex-1 border-b md:border-b-0 md:border-r border-slate-200">
              <i className="fa-regular fa-calendar text-slate-400 text-sm"></i>
              <div className="flex-1">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Date</p>
                <input 
                  type="text" 
                  value={search.date} 
                  onChange={e => setSearch(prev => ({ ...prev, date: e.target.value }))}
                  className="w-full text-xs font-semibold text-[#1A1815] focus:outline-none bg-transparent"
                />
              </div>
              <i className="fa-solid fa-chevron-down text-[10px] text-slate-400"></i>
            </div>

            <div className="flex items-center gap-3 px-3 py-2 flex-1">
              <i className="fa-regular fa-clock text-slate-400 text-sm"></i>
              <div className="flex-1">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Time</p>
                <input 
                  type="text" 
                  value={search.time} 
                  onChange={e => setSearch(prev => ({ ...prev, time: e.target.value }))}
                  className="w-full text-xs font-semibold text-[#1A1815] focus:outline-none bg-transparent"
                />
              </div>
              <i className="fa-solid fa-chevron-down text-[10px] text-slate-400"></i>
            </div>

            <button 
              onClick={() => {
                addToast(`Filtered parking spots for ${search.location} at ${search.time}`, "info");
                window.scrollTo({ top: 480, behavior: 'smooth' });
              }}
              className="btn-teal px-6 py-3 text-xs sm:text-sm font-semibold flex items-center justify-center gap-2 whitespace-nowrap shadow-md">
              <i className="fa-solid fa-magnifying-glass text-xs"></i>
              <span>Find a Spot</span>
            </button>
          </div>
        </div>
      </section>

      {/* 3. Feature Pills */}
      <section className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid md:grid-cols-3 gap-6">
          <div className="feature-pill flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#E6EFE9] text-[#1C3B37] flex items-center justify-center text-lg flex-shrink-0">
              <i className="fa-solid fa-shield-halved"></i>
            </div>
            <div>
              <h3 className="text-base font-bold text-[#1A1815]">Verified spaces</h3>
              <p className="text-xs text-[#706A62] mt-0.5">Only trusted and verified parking locations.</p>
            </div>
          </div>

          <div className="feature-pill flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#E6EFE9] text-[#1C3B37] flex items-center justify-center text-lg flex-shrink-0">
              <i className="fa-solid fa-bolt"></i>
            </div>
            <div>
              <h3 className="text-base font-bold text-[#1A1815]">Instant booking</h3>
              <p className="text-xs text-[#706A62] mt-0.5">Reserve your spot in seconds.</p>
            </div>
          </div>

          <div className="feature-pill flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#E6EFE9] text-[#1C3B37] flex items-center justify-center text-lg flex-shrink-0">
              <i className="fa-solid fa-lock"></i>
            </div>
            <div>
              <h3 className="text-base font-bold text-[#1A1815]">Secure payments</h3>
              <p className="text-xs text-[#706A62] mt-0.5">Pay safely with UPI, cards or wallets.</p>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Popular Parking Grid */}
      <section className="max-w-7xl mx-auto px-6 pb-20">
        <div className="flex items-baseline justify-between mb-8">
          <h2 className="text-3xl sm:text-4xl font-serif font-normal text-[#1A1815]">
            Popular parking near you
          </h2>
          <button 
            onClick={() => addToast("Showing all available parking facilities.", "info")}
            className="text-xs sm:text-sm font-semibold text-[#1C3B37] hover:underline flex items-center gap-1.5">
            <span>View all</span>
            <i className="fa-solid fa-arrow-right text-xs"></i>
          </button>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {locations.map(loc => {
            const isFav = wishlist[loc.id];
            return (
              <div 
                key={loc.id} 
                className="nude-card rounded-3xl overflow-hidden flex flex-col justify-between group">
                
                <div className="relative h-56 w-full overflow-hidden bg-slate-100">
                  <img 
                    src={loc.image} 
                    alt={loc.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-all duration-500"
                  />
                  <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-md px-3 py-1 rounded-full text-xs font-semibold text-[#1A1815] shadow-sm flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span>Available</span>
                  </div>

                  <button 
                    onClick={(e) => toggleWishlist(loc.id, e)}
                    className="absolute top-4 right-4 w-9 h-9 rounded-full bg-black/30 hover:bg-black/50 backdrop-blur-md flex items-center justify-center text-white transition">
                    <i className={`${isFav ? "fa-solid fa-heart text-rose-500" : "fa-regular fa-heart"} text-sm`}></i>
                  </button>
                </div>

                <div className="p-5 flex-1 flex flex-col justify-between">
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="text-base font-bold text-[#1A1815] group-hover:text-[#1C3B37] transition">{loc.name}</h3>
                        <p className="text-xs text-[#706A62] mt-0.5">
                          <i className="fa-solid fa-location-dot text-[10px] mr-1"></i> {loc.location} • {loc.distance}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="text-lg font-bold text-[#1A1815]">₹{loc.rate}</span>
                        <span className="text-[10px] text-[#706A62]"> / hour</span>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center gap-1.5 text-xs text-[#706A62]">
                      <i className="fa-solid fa-star text-amber-500 text-xs"></i>
                      <span className="font-bold text-[#1A1815]">{loc.rating}</span>
                      <span>({loc.reviews.toLocaleString()} reviews)</span>
                    </div>
                  </div>

                  <div className="mt-5 pt-4 border-t border-[#F5F0E8] flex items-center justify-between">
                    <span className="text-xs text-emerald-700 font-semibold">
                      {loc.freeSpots} spots left
                    </span>
                    <button 
                      onClick={() => handleBookNow(loc)}
                      className="btn-teal px-6 py-2.5 text-xs">
                      Book Now
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Booking Modal */}
      {bookingModalLocation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4" onClick={() => setBookingModalLocation(null)}>
          <div className="bg-white rounded-3xl max-w-md w-full p-6 border border-[#E8E1D5] shadow-2xl animate-fade-up" onClick={e => e.stopPropagation()}>
            <div className="flex items-start justify-between pb-3 border-b border-[#F5F0E8] mb-4">
              <div>
                <span className="text-[10px] font-bold text-[#1C3B37] uppercase tracking-wider">Reserve Parking</span>
                <h3 className="text-lg font-bold text-[#1A1815]">{bookingModalLocation.name}</h3>
                <p className="text-xs text-[#706A62]">{bookingModalLocation.location} • ₹{bookingModalLocation.rate}/hr</p>
              </div>
              <button onClick={() => setBookingModalLocation(null)} className="text-slate-400 hover:text-black text-sm">
                <i className="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-xs font-bold text-[#1A1815] mb-2">Select Your Parking Bay:</label>
              <div className="grid grid-cols-4 gap-2">
                {bookingModalLocation.slots.map(s => (
                  <button 
                    key={s}
                    onClick={() => setSelectedSlot(s)}
                    className={`py-2 px-3 rounded-xl border text-xs font-mono font-bold transition ${
                      selectedSlot === s
                        ? "bg-[#1C3B37] text-white border-[#1C3B37] shadow-sm"
                        : "bg-[#FAF7F2] text-[#1A1815] border-[#E8E1D5] hover:border-slate-400"
                    }`}>
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-5 bg-[#FAF7F2] p-4 rounded-2xl border border-[#E8E1D5]">
              <div className="flex justify-between text-xs font-semibold text-[#1A1815] mb-2">
                <span>Parking Duration:</span>
                <span className="font-bold text-[#1C3B37]">{durationHours} Hours</span>
              </div>
              <input 
                type="range" 
                min="1" 
                max="10" 
                value={durationHours} 
                onChange={e => setDurationHours(Number(e.target.value))}
                className="w-full h-2 bg-slate-300 rounded-lg appearance-none cursor-pointer custom-range"
              />
              <div className="flex justify-between text-[10px] text-[#706A62] mt-1 font-mono">
                <span>1h</span><span>5h</span><span>10h</span>
              </div>

              <div className="mt-3 pt-3 border-t border-[#E8E1D5] flex justify-between items-center text-xs">
                <span className="text-[#706A62]">Total Amount:</span>
                <span className="text-lg font-bold text-[#1A1815]">₹{bookingModalLocation.rate * durationHours}</span>
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={() => setBookingModalLocation(null)} className="flex-1 py-2.5 rounded-xl border border-[#E8E1D5] text-xs font-semibold text-[#706A62] hover:bg-[#FAF7F2]">
                Cancel
              </button>
              <button onClick={handleConfirmReservation} className="btn-teal flex-1 py-2.5 text-xs shadow-md">
                Confirm & Pay
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Passes Drawer Modal */}
      {passesModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4" onClick={() => setPassesModalOpen(false)}>
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 border border-[#E8E1D5] shadow-2xl animate-fade-up" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between pb-3 border-b border-[#F5F0E8] mb-4">
              <div>
                <h3 className="text-base font-bold text-[#1A1815]">My Active Parking Passes</h3>
                <p className="text-xs text-[#706A62]">Show this digital pass at the boom barrier optical scanner</p>
              </div>
              <button onClick={() => setPassesModalOpen(false)} className="text-slate-400 hover:text-black text-sm">
                <i className="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div className="space-y-3 max-h-80 overflow-y-auto">
              {userBookings.map(b => (
                <div key={b.id} className="p-4 rounded-2xl bg-[#FAF7F2] border border-[#E8E1D5] flex items-center justify-between gap-4">
                  <div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                      {b.status}
                    </span>
                    <h4 className="text-sm font-bold text-[#1A1815] mt-1">{b.locationName} — Slot {b.slot}</h4>
                    <p className="text-xs text-[#706A62]">{b.time}</p>
                    <p className="text-[11px] font-mono font-bold text-[#1C3B37] mt-1">Code: {b.qr}</p>
                  </div>

                  <div className="w-16 h-16 rounded-xl bg-white border border-[#E8E1D5] flex items-center justify-center text-3xl text-[#1A1815] shadow-xs">
                    <i className="fa-solid fa-qrcode"></i>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Sign In Modal */}
      {authModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4" onClick={() => setAuthModalOpen(false)}>
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 border border-[#E8E1D5] shadow-2xl animate-fade-up text-center" onClick={e => e.stopPropagation()}>
            <span className="text-3xl font-serif font-bold text-[#0f1d22]">ParkSpot</span>
            <h3 className="text-base font-bold text-[#1A1815] mt-2">Sign in to your account</h3>
            <p className="text-xs text-[#706A62] mb-5">Access your passes, saved spaces, and vehicles</p>

            <div className="space-y-3 mb-4">
              <input type="email" defaultValue="patil45@gmail.com" placeholder="Email" className="w-full px-4 py-2.5 text-xs rounded-xl border border-[#E8E1D5] bg-[#FAF7F2]" />
              <input type="password" defaultValue="••••••••" placeholder="Password" className="w-full px-4 py-2.5 text-xs rounded-xl border border-[#E8E1D5] bg-[#FAF7F2]" />
            </div>

            <button 
              onClick={() => { addToast("Welcome back, Jignyasa Patil!", "success"); setAuthModalOpen(false); }}
              className="btn-teal w-full py-2.5 text-xs font-bold transition">
              Sign In
            </button>
          </div>
        </div>
      )}

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
};

export default App;
