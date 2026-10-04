import { useState } from "react";

import "./ParkingDetails.css";

import {
  ArrowLeft,
  Car,
  Clock,
  MapPin,
  ShieldCheck,
  Camera,
  CheckCircle2,
} from "lucide-react";


function ParkingDetails({
  parking,
  onBack,
  onReserve,
}) {

  const [selectedSlot, setSelectedSlot] = useState(null);


  if (!parking) {
    return null;
  }


  // -----------------------------------------
  // PARKING FEATURES
  // -----------------------------------------

  const features = [

    {
      icon: Clock,
      title: "Open now",
      text: "Available throughout the day",
    },

    {
      icon: Camera,
      title: "CCTV monitoring",
      text: "Parking area is monitored",
    },

    {
      icon: ShieldCheck,
      title: "Secure parking",
      text: "Designed for safer parking",
    },

  ];


  // -----------------------------------------
  // PARKING SLOTS
  // -----------------------------------------

  const slots = [

    {
      id: "A01",
      status: "available",
    },

    {
      id: "A02",
      status: "available",
    },

    {
      id: "A03",
      status: "occupied",
    },

    {
      id: "A04",
      status: "available",
    },

    {
      id: "A05",
      status: "occupied",
    },

    {
      id: "A06",
      status: "available",
    },

  ];


  // -----------------------------------------
  // SLOT SELECT
  // -----------------------------------------

  const handleSlotSelect = (slot) => {

    if (slot.status === "occupied") {
      return;
    }

    setSelectedSlot(slot.id);
  };


  // -----------------------------------------
  // RESERVE
  // -----------------------------------------

  const handleReserve = () => {

    if (!selectedSlot) {

      alert("Please select a parking slot first.");

      return;
    }

    onReserve(parking, selectedSlot);
  };


  return (

    <div className="details-page">


      {/* =====================================
          HEADER
      ===================================== */}

      <header className="details-header">


        <button
          className="details-back"
          onClick={onBack}
        >

          <ArrowLeft size={18} />

          <span>
            Back to parking
          </span>

        </button>


        <div className="details-logo">
          ParkSpot
        </div>


        <div className="details-location">

          <MapPin size={16} />

          Mumbai

        </div>

      </header>



      {/* =====================================
          CONTENT
      ===================================== */}

      <main className="details-content">


        {/* ===================================
            LEFT
        =================================== */}

        <section className="details-main">


          <div className="details-heading">

            <p className="eyebrow">
              PARKING LOCATION
            </p>


            <h1>
              {parking.name}
            </h1>


            <div className="details-location-line">

              <MapPin size={16} />

              <span>
                {parking.location || "Bandra, Mumbai"}
              </span>

              <span className="separator">
                •
              </span>

              <span>
                {parking.distance}
              </span>

            </div>

          </div>



          {/* STATUS */}

          <div className="details-status">

            <div className="status-indicator"></div>

            <div>

              <strong>
                Open now
              </strong>

              <span>
                Parking is currently available
              </span>

            </div>

          </div>



          {/* =================================
              FEATURES
          ================================= */}

          <section className="details-section">

            <div className="section-title">

              <h2>
                Parking information
              </h2>

            </div>


            <div className="feature-grid">

              {features.map((feature) => {

                const Icon = feature.icon;

                return (

                  <div
                    className="feature-card"
                    key={feature.title}
                  >

                    <div className="feature-icon">

                      <Icon size={19} />

                    </div>


                    <div>

                      <strong>
                        {feature.title}
                      </strong>

                      <p>
                        {feature.text}
                      </p>

                    </div>

                  </div>

                );

              })}

            </div>

          </section>



          {/* =================================
              SLOTS
          ================================= */}

          <section className="details-section">


            <div className="section-title">


              <div>

                <h2>
                  Available slots
                </h2>

                <p>
                  Select a slot to continue
                </p>

              </div>


              <span className="availability-count">

                {parking.available} available

              </span>

            </div>



            <div className="slots-grid">


              {slots.map((slot) => {

                const isSelected =
                  selectedSlot === slot.id;

                const isOccupied =
                  slot.status === "occupied";


                return (

                  <button
                    key={slot.id}
                    className={`slot ${
                      slot.status
                    } ${
                      isSelected
                        ? "selected"
                        : ""
                    }`}
                    disabled={isOccupied}
                    onClick={() =>
                      handleSlotSelect(slot)
                    }
                  >

                    <Car size={17} />

                    <span>
                      {slot.id}
                    </span>


                    {!isOccupied && (

                      <CheckCircle2
                        size={14}
                      />

                    )}

                  </button>

                );

              })}

            </div>



            <div className="slot-legend">

              <span>

                <i className="legend-dot available-dot"></i>

                Available

              </span>


              <span>

                <i className="legend-dot occupied-dot"></i>

                Occupied

              </span>

            </div>

          </section>

        </section>



        {/* ===================================
            BOOKING CARD
        =================================== */}

        <aside className="booking-card">


          <div className="booking-card-top">


            <div className="booking-car-icon">

              <Car size={22} />

            </div>


            <div>

              <span>
                Parking rate
              </span>

              <strong>
                {parking.price}
              </strong>

            </div>

          </div>



          <div className="booking-divider"></div>



          <div className="booking-summary">


            <div>

              <span>
                Parking
              </span>

              <strong>
                {parking.name}
              </strong>

            </div>


            <div>

              <span>
                Distance
              </span>

              <strong>
                {parking.distance}
              </strong>

            </div>


            <div>

              <span>
                Selected slot
              </span>

              <strong>
                {selectedSlot || "Select a slot"}
              </strong>

            </div>


            <div>

              <span>
                Availability
              </span>

              <strong>
                {parking.available} spaces
              </strong>

            </div>

          </div>



          <button
            className="reserve-button"
            onClick={handleReserve}
          >

            Reserve Parking

          </button>


          <p className="booking-note">

            You will be able to review your
            booking before confirming.

          </p>

        </aside>

      </main>

    </div>

  );
}


export default ParkingDetails;