import os
import googlemaps

# Ensure your organization's API key is securely loaded from environment variables
GOOGLE_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "YOUR_SECURE_API_KEY_HERE")

def initialize_hydro_shield(api_key):
    if api_key == "YOUR_SECURE_API_KEY_HERE" or not api_key:
        raise ValueError("CRITICAL ERROR: Google Maps API Key must be populated.")
    return googlemaps.Client(key=api_key)

def scan_property_for_water_hazards(gmaps_client, street_address, radius_meters=500):
    print(f"Initializing Hydro-Shield Scan for Address: {street_address}")
    
    # 1. Geocode the human-readable physical address into precise coordinate bounds
    geocode_result = gmaps_client.geocode(street_address)
    if not geocode_result:
        return {"status": "ERROR", "message": "Address resolution failed."}
        
    location = geocode_result[0]['geometry']['location']
    home_lat = location['lat']
    home_lng = location['lng']
    print(f"Target Coordinate Matrix established: ({home_lat}, {home_lng})")

    # 2. Query Google Places API for nearby water hazards within the target perimeter
    # We query specific keyword categories that represent high-risk drowning zones
    water_keywords = ['pond', 'canal', 'pool', 'lake', 'fountain', 'retention basin']
    detected_hazards = []

    for keyword in water_keywords:
        places_result = gmaps_client.places_nearby(
            location=(home_lat, home_lng),
            radius=radius_meters,
            keyword=keyword
        )
        
        for place in places_result.get('results', []):
            hazard_name = place.get('name')
            hazard_lat = place['geometry']['location']['lat']
            hazard_lng = place['geometry']['location']['lng']
            place_id = place.get('place_id')
            
            # Prevent duplicate entries of the same geographic hazard
            if not any(h['place_id'] == place_id for h in detected_hazards):
                detected_hazards.append({
                    "name": hazard_name,
                    "keyword_match": keyword,
                    "lat": hazard_lat,
                    "lng": hazard_lng,
                    "place_id": place_id
                })

    print(f"Scan complete. Found {len(detected_hazards)} local water hazards inside the {radius_meters}m safety buffer.")
    return {
        "status": "SUCCESS",
        "home_coordinates": {"lat": home_lat, "lng": home_lng},
        "hazards": detected_hazards
    }

# =====================================================================
# SYSTEM EXECUTION EXAMPLE
# =====================================================================
if __name__ == "__main__":
    try:
        client = initialize_hydro_shield(GOOGLE_API_KEY)
        
        # Test case placeholder property
        sample_address = "123 Main Street, Tampa, FL"
        results = scan_property_for_water_hazards(client, sample_address, radius_meters=500)
        
        if results["status"] == "SUCCESS":
            print("\n--- ACTIVE HYDROLOGY HAZARD RADAR MATRIX ---")
            for index, hazard in enumerate(results["hazards"]):
                print(f"[{index}] {hazard['name']} ({hazard['keyword_match'].upper()}) at Coordinates: {hazard['lat']}, {hazard['lng']}")
    except Exception as e:
        print(f"System Fault: {e}")
