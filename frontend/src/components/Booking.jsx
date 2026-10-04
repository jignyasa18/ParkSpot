import "./Booking.css";

import {
  ArrowLeft,
  Car,
  MapPin,
  Clock,
  CalendarDays,
  CheckCircle2,
  CreditCard,
  ShieldCheck,
} from "lucide-react";


function Booking({
  parking,
  selectedSlot,
  onBack,
  onComplete,
}) {

  if (!parking) {
    return null;
  }


  const slot = selectedSlot || "A01";


  return (

    <div className="booking-page">


      {/* =====================================
          HEADER
      ===================================== */}

      <header className="booking-header">


        <button
          className="booking-back"
          onClick={onBack}
        >

          <ArrowLeft size={18} />

          <span>
            Back to parking
          </span>

        </button>


        <div className="booking-logo">
          ParkSpot
        </div>


        <div className="booking-location">

          <MapPin size={16} />

          <span>
            Mumbai
          </span>

        </div>

      </header>



      {/* =====================================
          MAIN
      ===================================== */}

      <main className="booking-content">


        {/* ===================================
            LEFT
        =================================== */}

        <section className="booking-main">


          <div className="booking-heading">

            <p className="booking-eyebrow">
              RESERVE PARKING
            </p>


            <h1>

              Review your parking
              <br />
              reservation.

            </h1>


            <p className="booking-description">

              Check your parking details before
              continuing.

            </p>

          </div>



          {/* =================================
              LOCATION
          ================================= */}

          <section className="booking-section">


            <div className="booking-section-heading">


              <div>

                <p className="section-eyebrow">
                  PARKING LOCATION
                </p>

                <h2>
                  {parking.name}
                </h2>

              </div>


              <div className="booking-status">

                <span></span>

                Available

              </div>

            </div>



            <div className="parking-summary-grid">


              <div className="summary-item">

                <div className="summary-icon">

                  <MapPin size={18} />

                </div>


                <div>

                  <span>
                    Location
                  </span>

                  <strong>
                    {parking.location ||
                      "Bandra, Mumbai"}
                  </strong>

                </div>

              </div>



              <div className="summary-item">

                <div className="summary-icon">

                  <NavigationIcon />

                </div>


                <div>

                  <span>
                    Distance
                  </span>

                  <strong>
                    {parking.distance}
                  </strong>

                </div>

              </div>



              <div className="summary-item">

                <div className="summary-icon">

                  <Car size={18} />

                </div>


                <div>

                  <span>
                    Parking type
                  </span>

                  <strong>
                    {parking.type ||
                      "Open parking"}
                  </strong>

                </div>

              </div>



              <div className="summary-item">

                <div className="summary-icon">

                  <Clock size={18} />

                </div>


                <div>

                  <span>
                    Status
                  </span>

                  <strong>
                    Open now
                  </strong>

                </div>

              </div>

            </div>

          </section>



          {/* =================================
              SLOT
          ================================= */}

          <section className="booking-section">


            <div className="booking-section-title">

              <div>

                <p className="section-eyebrow">
                  PARKING SLOT
                </p>

                <h2>
                  Selected slot
                </h2>

              </div>

            </div>



            <div className="selected-slot-card">


              <div className="selected-slot-icon">

                <Car size={22} />

              </div>


              <div className="selected-slot-info">

                <span>
                  Your parking space
                </span>

                <strong>
                  {slot}
                </strong>

              </div>


              <div className="selected-slot-check">

                <CheckCircle2 size={20} />

                <span>
                  Available
                </span>

              </div>

            </div>

          </section>



          {/* =================================
              RESERVATION
          ================================= */}

          <section className="booking-section">


            <div className="booking-section-title">

              <div>

                <p className="section-eyebrow">
                  RESERVATION DETAILS
                </p>

                <h2>
                  Booking information
                </h2>

              </div>

            </div>



            <div className="booking-details-grid">


              <div className="booking-input-card">

                <div className="booking-input-icon">

                  <CalendarDays size={18} />

                </div>


                <div>

                  <span>
                    Date
                  </span>

                  <strong>
                    Today
                  </strong>

                </div>

              </div>



              <div className="booking-input-card">

                <div className="booking-input-icon">

                  <Clock size={18} />

                </div>


                <div>

                  <span>
                    Entry
                  </span>

                  <strong>
                    Now
                  </strong>

                </div>

              </div>

            </div>

          </section>



          {/* =================================
              SECURITY
          ================================= */}

          <div className="booking-security">


            <div className="security-icon">

              <ShieldCheck size={19} />

            </div>


            <div>

              <strong>
                Secure reservation
              </strong>

              <p>

                Your reservation details will be
                reviewed before the booking is
                confirmed.

              </p>

            </div>

          </div>

        </section>



        {/* =====================================
            RIGHT SUMMARY
        ===================================== */}

        <aside className="booking-summary-card">


          <div className="summary-card-heading">

            <p>
              BOOKING SUMMARY
            </p>

            <h2>
              {parking.name}
            </h2>

          </div>



          <div className="summary-card-slot">


            <div className="summary-card-slot-icon">

              <Car size={20} />

            </div>


            <div>

              <span>
                Selected slot
              </span>

              <strong>
                {slot}
              </strong>

            </div>

          </div>



          <div className="summary-divider"></div>



          <div className="price-summary">


            <div>

              <span>
                Parking rate
              </span>

              <strong>
                {parking.price}
              </strong>

            </div>


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

          </div>



          <div className="summary-divider"></div>



          <div className="total-row">

            <span>
              Estimated total
            </span>

            <strong>
              {parking.price}
            </strong>

          </div>



          <button
            className="confirm-booking-button"
            onClick={onComplete}
          >

            <CreditCard size={18} />

            Continue to confirmation

          </button>



          <p className="summary-note">

            You will review your reservation before
            the final confirmation.

          </p>

        </aside>

      </main>

    </div>

  );
}



// =============================================
// SMALL NAVIGATION ICON
// =============================================

function NavigationIcon() {

  return (

    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >

      <polygon points="3 11 22 2 13 21 11 13 3 11" />

    </svg>

  );
}


export default Booking;