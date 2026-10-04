import { useState } from "react";

import FindParking from "./components/FindParking";
import ParkingDetails from "./components/ParkingDetails";
import Booking from "./components/Booking";

function App() {
  const [page, setPage] = useState("parking");
  const [selectedParking, setSelectedParking] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState(null);

  const handleSelectParking = (parking) => {
    setSelectedParking(parking);
    setSelectedSlot(null);
    setPage("details");
  };

  const handleBackToParking = () => {
    setSelectedParking(null);
    setSelectedSlot(null);
    setPage("parking");
  };

  const handleReserve = (parking, slot) => {
    setSelectedParking(parking);
    setSelectedSlot(slot);
    setPage("booking");
  };

  const handleBackToDetails = () => {
    setPage("details");
  };

  const handleCompleteBooking = () => {
    alert(
      `Parking reserved successfully!\n\nLocation: ${
        selectedParking?.name
      }\nSlot: ${selectedSlot || "A01"}`
    );

    setPage("parking");
    setSelectedParking(null);
    setSelectedSlot(null);
  };

  if (page === "booking") {
    return (
      <Booking
        parking={selectedParking}
        selectedSlot={selectedSlot}
        onBack={handleBackToDetails}
        onComplete={handleCompleteBooking}
      />
    );
  }

  if (page === "details") {
    return (
      <ParkingDetails
        parking={selectedParking}
        onBack={handleBackToParking}
        onReserve={handleReserve}
      />
    );
  }

  return (
    <FindParking
      onSelectParking={handleSelectParking}
      onBack={() => {}}
    />
  );
}

export default App;