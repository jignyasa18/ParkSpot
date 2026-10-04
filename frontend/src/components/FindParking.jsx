import { useState } from "react";
import "./FindParking.css";

import {
  Search,
  MapPin,
  Navigation,
  Car,
  Clock,
  SlidersHorizontal,
} from "lucide-react";

const parkingSpots = [
  {
    id: 1,
    name: "Bandra West Parking",
    location: "Bandra West, Mumbai",
    distance: "450 m",
    price: "₹40/hr",
    priceNumber: 40,
    available: 12,
    type: "Open parking",
    status: "Open now",
  },
  {
    id: 2,
    name: "Linking Road Parking",
    location: "Bandra West, Mumbai",
    distance: "700 m",
    price: "₹50/hr",
    priceNumber: 50,
    available: 8,
    type: "Covered parking",
    status: "Open now",
  },
  {
    id: 3,
    name: "Hill Road Parking",
    location: "Bandra West, Mumbai",
    distance: "1.1 km",
    price: "₹30/hr",
    priceNumber: 30,
    available: 18,
    type: "Open parking",
    status: "Open now",
  },
];

function FindParking({ onSelectParking }) {
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("default");

  const filteredParking = parkingSpots
    .filter((spot) => {
      const value = search.toLowerCase();

      return (
        spot.name.toLowerCase().includes(value) ||
        spot.location.toLowerCase().includes(value)
      );
    })
    .sort((a, b) => {
      if (sortBy === "price") {
        return a.priceNumber - b.priceNumber;
      }

      if (sortBy === "distance") {
        return parseFloat(a.distance) - parseFloat(b.distance);
      }

      return 0;
    });

  return (
    <div className="parking-page">

      {/* HEADER */}
      <header className="parking-header">

        <button className="parking-back">
          ←
        </button>

        <div className="parking-logo">
          ParkSpot
        </div>

        <div className="parking-location">
          <MapPin size={17} />
          <span>Bandra, Mumbai</span>
        </div>

      </header>


      {/* MAIN */}
      <main className="parking-main">

        {/* LEFT PANEL */}
        <section className="parking-left">

          <div className="parking-heading">

            <p className="parking-eyebrow">
              FIND PARKING
            </p>

            <h1>
              Parking near
              <br />
              your destination.
            </h1>

          </div>


          {/* SEARCH */}
          <div className="search-row">

            <div className="search-box">

              <Search size={20} />

              <input
                type="text"
                placeholder="Search an area or destination"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />

            </div>

            <button className="search-button">
              Search
            </button>

          </div>


          {/* FILTERS */}
          <div className="filter-row">

            <button className="filter-button active">
              <SlidersHorizontal size={17} />
              Filters
            </button>

            <button
              className={`filter-button ${
                sortBy === "price" ? "selected" : ""
              }`}
              onClick={() =>
                setSortBy(sortBy === "price" ? "default" : "price")
              }
            >
              Price
            </button>

            <button
              className={`filter-button ${
                sortBy === "distance" ? "selected" : ""
              }`}
              onClick={() =>
                setSortBy(sortBy === "distance" ? "default" : "distance")
              }
            >
              Distance
            </button>

          </div>


          {/* RESULT HEADER */}
          <div className="results-heading">

            <strong>
              Available parking
            </strong>

            <span>
              {filteredParking.reduce(
                (total, spot) => total + spot.available,
                0
              )}{" "}
              places nearby
            </span>

          </div>


          {/* PARKING LIST */}
          <div className="parking-list">

            {filteredParking.map((spot) => (

              <article
                className="parking-card"
                key={spot.id}
              >

                <div className="parking-card-info">

                  <div className="parking-card-title">

                    <h2>
                      {spot.name}
                    </h2>

                    <span className="available-badge">
                      Available
                    </span>

                  </div>


                  <div className="parking-card-location">

                    <MapPin size={15} />

                    <span>
                      {spot.location}
                    </span>

                  </div>


                  <div className="parking-card-meta">

                    <span>
                      <Navigation size={15} />
                      {spot.distance}
                    </span>

                    <span>
                      <Clock size={15} />
                      {spot.status}
                    </span>

                    <span>
                      <Car size={15} />
                      {spot.available} spaces
                    </span>

                  </div>

                </div>


                <div className="parking-card-right">

                  <strong className="parking-price">
                    {spot.price}
                  </strong>

                  <button
                    className="view-button"
                    onClick={() =>
                      onSelectParking(spot)
                    }
                  >
                    View
                  </button>

                </div>

              </article>

            ))}


            {filteredParking.length === 0 && (

              <div className="no-results">
                No parking locations found.
              </div>

            )}

          </div>

        </section>


        {/* MAP */}
        <section className="parking-map">

          <div className="map-road road-one"></div>
          <div className="map-road road-two"></div>
          <div className="map-road road-three"></div>

          <div className="map-label label-linking">
            Linking Road
          </div>

          <div className="map-label label-bandra">
            Bandra West
          </div>


          <button
            className="map-marker marker-one"
            onClick={() =>
              onSelectParking(parkingSpots[0])
            }
          >
            ₹40
          </button>

          <button
            className="map-marker marker-two"
            onClick={() =>
              onSelectParking(parkingSpots[1])
            }
          >
            ₹50
          </button>

          <button
            className="map-marker marker-three"
            onClick={() =>
              onSelectParking(parkingSpots[2])
            }
          >
            ₹30
          </button>

        </section>

      </main>

    </div>
  );
}

export default FindParking;