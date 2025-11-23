"""
Enhanced Itinerary Agent with Integrated Dining and Travel Time Management
Organizes attractions AND meals into a complete day schedule with accurate timing
"""
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import List, Dict, Tuple, Optional
import json
from math import radians, cos, sin, asin, sqrt

from config import Config
from utils.logger import logger
from services.ors_api import geocode, matrix_distances, ORSError


class ItineraryAgent:
    """Agent that creates day-by-day itinerary with attractions AND dining"""
    
    BUFFER_TIME_HOURS = 0.25  # 15 minutes buffer between activities
    MAX_DAY_TRIP_DISTANCE = 100  # Maximum km for day trip attractions
    MAX_REASONABLE_DISTANCE = 50  # Maximum km from city center for geocoding validation
    
    def __init__(self):
        """Initialize the agent with OpenAI"""
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=Config.OPENAI_TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )
        logger.info("Itinerary Agent initialized with ORS and dining integration")
    
    def _geocode_attractions(self, attractions: List[Dict], destination: str) -> List[Dict]:
        """Add coordinates to attractions using ORS geocoding"""
        logger.info("Geocoding attractions for distance calculations")
        
        for attraction in attractions:
            query = f"{attraction['name']}, {destination}"
            try:
                coords = geocode(query, limit=1)
                if coords:
                    attraction['coordinates'] = {
                        'lat': coords[0][0],
                        'lng': coords[0][1]
                    }
                    logger.info(f"  Geocoded: {attraction['name']}")
                else:
                    attraction['coordinates'] = None
                    logger.warning(f"  Could not geocode: {attraction['name']}")
            except Exception as e:
                logger.warning(f"  Geocoding failed for {attraction['name']}: {e}")
                attraction['coordinates'] = None
        
        return attractions
    
    def _validate_geocoding(self, attractions: List[Dict], destination: str) -> List[Dict]:
        """Validate geocoded attractions are within reasonable distance"""
        logger.info("Validating geocoded locations")
        
        # Get center coordinates for the destination
        try:
            center_coords = geocode(destination, limit=1)
            if not center_coords:
                logger.warning("Could not geocode destination center, skipping validation")
                return attractions
            
            center_lat, center_lng = center_coords[0]
            
            for attraction in attractions:
                if attraction.get('coordinates'):
                    distance = self._haversine_distance(
                        (center_lat, center_lng),
                        (attraction['coordinates']['lat'], attraction['coordinates']['lng'])
                    )
                    
                    if distance > self.MAX_REASONABLE_DISTANCE:
                        logger.warning(f"  {attraction['name']} geocoded {distance:.0f}km from city center - likely error, removing coordinates")
                        attraction['coordinates'] = None
                        attraction['geocoding_error'] = True
                    else:
                        logger.info(f"  {attraction['name']} validated: {distance:.1f}km from center")
        except Exception as e:
            logger.error(f"Geocoding validation failed: {e}")
        
        return attractions
    
    def _haversine_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate haversine distance between two coordinates in km"""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of Earth in km
        
        return c * r
    
    def _calculate_travel_times(self, attractions: List[Dict]) -> List[Dict]:
        """Calculate travel times between consecutive attractions with validation"""
        for i in range(len(attractions) - 1):
            if attractions[i].get('coordinates') and attractions[i+1].get('coordinates'):
                start = (attractions[i]['coordinates']['lat'], attractions[i]['coordinates']['lng'])
                end = (attractions[i+1]['coordinates']['lat'], attractions[i+1]['coordinates']['lng'])
                
                try:
                    results = matrix_distances(start, [end], profile="driving-car")
                    if results and results[0].get('status') == 'OK':
                        distance_km = results[0]['distance_km']
                        
                        # Validate reasonable distance
                        if distance_km > self.MAX_DAY_TRIP_DISTANCE:
                            logger.error(f"  Unrealistic distance {distance_km:.0f}km between {attractions[i]['name']} and {attractions[i+1]['name']} - skipping")
                            continue
                        
                        attractions[i]['travel_to_next'] = {
                            'distance_km': distance_km,
                            'duration_h': results[0]['duration_h']
                        }
                        logger.info(f"  Travel from {attractions[i]['name']} to {attractions[i+1]['name']}: {distance_km:.1f}km, {results[0]['duration_h']*60:.0f} min")
                except Exception as e:
                    logger.warning(f"  Could not calculate travel time: {e}")
        
        return attractions
    
    def _filter_day_trip_attractions(self, attractions: List[Dict], center_location: Tuple[float, float], days: int) -> List[Dict]:
        """Filter attractions suitable for day trips"""
        if days > 1:  # Only filter for single-day trips
            return attractions
        
        logger.info("Filtering attractions for day trip feasibility")
        valid_attractions = []
        
        for attr in attractions:
            if not attr.get('coordinates'):
                # Keep attractions without coordinates (but warn about them)
                if not attr.get('geocoding_error'):
                    valid_attractions.append(attr)
                    logger.warning(f"  Including {attr['name']} despite missing coordinates")
            else:
                distance = self._haversine_distance(
                    center_location,
                    (attr['coordinates']['lat'], attr['coordinates']['lng'])
                )
                if distance <= self.MAX_DAY_TRIP_DISTANCE:
                    valid_attractions.append(attr)
                    logger.info(f"  {attr['name']}: {distance:.1f}km - included")
                else:
                    logger.warning(f"  {attr['name']}: {distance:.0f}km - TOO FAR for day trip, excluded")
        
        return valid_attractions
    
    def _optimize_daily_routes(self, daily_groups: List[List[Dict]], start_location: Optional[Tuple[float, float]] = None) -> List[List[Dict]]:
        """Reorder attractions within each day to minimize travel distance"""
        logger.info("Optimizing daily routes to minimize travel time")
        optimized_days = []
        
        for day_num, day_attractions in enumerate(daily_groups, 1):
            if not day_attractions or len(day_attractions) <= 2:
                optimized_days.append(day_attractions)
                continue
            
            # Filter out attractions without coordinates
            geocoded = [a for a in day_attractions if a.get('coordinates')]
            non_geocoded = [a for a in day_attractions if not a.get('coordinates')]
            
            if len(geocoded) <= 2:
                optimized_days.append(day_attractions)
                continue
            
            # Simple nearest-neighbor optimization
            ordered = []
            remaining = geocoded.copy()
            current_loc = start_location if start_location else (geocoded[0]['coordinates']['lat'], geocoded[0]['coordinates']['lng'])
            
            while remaining:
                nearest = min(remaining, key=lambda a: 
                    self._haversine_distance(current_loc, (a['coordinates']['lat'], a['coordinates']['lng']))
                )
                ordered.append(nearest)
                remaining.remove(nearest)
                current_loc = (nearest['coordinates']['lat'], nearest['coordinates']['lng'])
            
            # Add non-geocoded attractions at the end
            ordered.extend(non_geocoded)
            optimized_days.append(ordered)
            logger.info(f"  Day {day_num}: Optimized route for {len(ordered)} attractions")
        
        return optimized_days

    def _find_nearest_restaurant(
        self,
        location: Tuple[float, float],
        restaurants: List[Dict],
        meal_type: str
    ) -> Dict:
        """Find the nearest restaurant of specific meal type"""
        
        # Filter by meal type
        matching_restaurants = [
            r for r in restaurants 
            if r.get('meal_type') == meal_type and r.get('coordinates')
        ]
        
        if not matching_restaurants:
            # Fallback to any restaurant
            matching_restaurants = [r for r in restaurants if r.get('coordinates')]
        
        if not matching_restaurants:
            return None
        
        # Find nearest
        min_distance = float('inf')
        nearest = None
        
        for restaurant in matching_restaurants:
            rest_loc = (restaurant['coordinates']['lat'], restaurant['coordinates']['lng'])
            
            try:
                results = matrix_distances(location, [rest_loc], profile="driving-car")
                if results and results[0].get('status') == 'OK':
                    distance = results[0]['distance_km']
                    if distance < min_distance:
                        min_distance = distance
                        nearest = restaurant.copy()
                        nearest['distance_from_current'] = {
                            'distance_km': distance,
                            'duration_minutes': int(results[0]['duration_h'] * 60)
                        }
            except:
                pass
        
        return nearest
    
    def _parse_duration(self, duration_str: str) -> float:
        """Parse duration string to hours"""
        try:
            if 'half' in duration_str.lower():
                return 4
            elif 'full' in duration_str.lower():
                return 8
            else:
                # Extract first number from string like "2 hours" or "2-3 hours"
                return float(duration_str.split()[0].split('-')[0])
        except:
            return 2  # Default to 2 hours
    
    def _calculate_travel_from_restaurant(
        self,
        restaurant_coords: Tuple[float, float],
        next_attraction_coords: Tuple[float, float]
    ) -> Optional[Dict]:
        """Calculate travel time from restaurant to next attraction"""
        try:
            results = matrix_distances(restaurant_coords, [next_attraction_coords], profile="driving-car")
            if results and results[0].get('status') == 'OK':
                distance_km = results[0]['distance_km']
                
                # Validate distance
                if distance_km > self.MAX_DAY_TRIP_DISTANCE:
                    logger.warning(f"Restaurant to attraction distance {distance_km:.0f}km exceeds day trip limit")
                    return None
                
                return {
                    'distance_km': distance_km,
                    'duration_h': results[0]['duration_h']
                }
        except Exception as e:
            logger.warning(f"Could not calculate restaurant to attraction travel: {e}")
        return None
    
    def _format_time_with_overflow(self, time_hours: float) -> str:
        """Format time handling multi-day overflow"""
        time_minutes = int((time_hours % 1) * 60)
        
        if time_hours >= 24:
            # Handle multi-day overflow
            days_ahead = int(time_hours // 24)
            display_hours = int(time_hours % 24)
            return f"Day+{days_ahead} {display_hours:02d}:{time_minutes:02d}"
        else:
            return f"{int(time_hours):02d}:{time_minutes:02d}"

    def _integrate_dining(
        self,
        daily_attractions: List[List[Dict]],
        restaurants: List[Dict],
        accommodation_location: Tuple[float, float]
    ) -> List[List[Dict]]:
        """Integrate meal recommendations into daily schedules with accurate timing"""
        logger.info("Integrating dining recommendations into itinerary")
        
        integrated_days = []
        used_restaurants = set()
        
        for day_num, day_attractions in enumerate(daily_attractions, 1):
            # Calculate travel times between attractions first
            day_attractions = self._calculate_travel_times(day_attractions)
            
            day_schedule = []
            current_time = 9  # Start at 9 AM
            overflow_warning = False
            
            for idx, attraction in enumerate(day_attractions):
                # Check for day overflow
                if current_time >= 24 and not overflow_warning:
                    logger.warning(f"  Day {day_num}: Schedule overflowing into next day!")
                    overflow_warning = True
                
                # Store scheduled time for attraction
                attraction['scheduled_time'] = self._format_time_with_overflow(current_time)
                day_schedule.append(attraction)
                
                # Parse and add duration
                duration_hours = self._parse_duration(attraction.get('duration', '2 hours'))
                current_time += duration_hours + self.BUFFER_TIME_HOURS  # Add buffer
                
                # Add travel time to next attraction
                if attraction.get('travel_to_next'):
                    travel_hours = attraction['travel_to_next']['duration_h']
                    # Skip if travel time is unreasonable
                    if travel_hours > 2:  # More than 2 hours travel
                        logger.warning(f"  Skipping {travel_hours:.1f}h travel time - too long for day trip")
                    else:
                        current_time += travel_hours
                
                # Check if it's meal time (with overflow handling)
                effective_time = current_time % 24  # Get time within 24-hour cycle
                is_lunch_time = 11.5 <= effective_time <= 14 and not any(a.get('is_meal') and a.get('meal_type_scheduled') == 'lunch' for a in day_schedule)
                is_dinner_time = (17.5 <= effective_time <= 20 or idx == len(day_attractions) - 1) and effective_time > 17 and not any(a.get('is_meal') and a.get('meal_type_scheduled') == 'dinner' for a in day_schedule)
                
                if is_lunch_time or is_dinner_time:
                    meal_type = 'lunch' if is_lunch_time else 'dinner'
                    
                    # Find restaurant near current location
                    current_loc = None
                    if attraction.get('coordinates'):
                        current_loc = (attraction['coordinates']['lat'], attraction['coordinates']['lng'])
                    elif accommodation_location:
                        current_loc = accommodation_location
                    
                    if current_loc:
                        # Find nearest unused restaurant
                        available_restaurants = [
                            r for r in restaurants 
                            if r.get('name') not in used_restaurants
                        ]
                        
                        restaurant = self._find_nearest_restaurant(
                            current_loc,
                            available_restaurants,
                            meal_type
                        )
                        
                        if restaurant:
                            # Add travel time to restaurant
                            if restaurant.get('distance_from_current'):
                                travel_time_h = restaurant['distance_from_current']['duration_minutes'] / 60
                                current_time += travel_time_h
                            
                            used_restaurants.add(restaurant['name'])
                            restaurant['is_meal'] = True
                            restaurant['meal_type_scheduled'] = meal_type
                            restaurant['scheduled_time'] = self._format_time_with_overflow(current_time)
                            
                            # Calculate travel to next attraction if exists
                            if idx + 1 < len(day_attractions) and day_attractions[idx + 1].get('coordinates') and restaurant.get('coordinates'):
                                rest_coords = (restaurant['coordinates']['lat'], restaurant['coordinates']['lng'])
                                next_coords = (day_attractions[idx + 1]['coordinates']['lat'], day_attractions[idx + 1]['coordinates']['lng'])
                                travel_to_next = self._calculate_travel_from_restaurant(rest_coords, next_coords)
                                if travel_to_next:
                                    restaurant['travel_to_next'] = travel_to_next
                            
                            day_schedule.append(restaurant)
                            logger.info(f"  Day {day_num}: Added {meal_type} at {restaurant['name']} scheduled for {restaurant['scheduled_time']}")
                            
                            # Add meal duration and travel time if exists
                            current_time += 1  # 1 hour for meal
                            current_time += self.BUFFER_TIME_HOURS  # Buffer after meal
                            
                            if restaurant.get('travel_to_next'):
                                travel_hours = restaurant['travel_to_next']['duration_h']
                                if travel_hours <= 2:  # Reasonable travel time
                                    current_time += travel_hours
            
            integrated_days.append(day_schedule)
        
        return integrated_days
    
    def create_schedule(
        self,
        attractions: List[Dict],
        days: int,
        trip_type: str,
        destination: str,
        restaurants: List[Dict] = None,
        accommodation_location: Tuple[float, float] = None
    ) -> Dict:
        """
        Create schedule with attractions AND dining integrated
        
        Args:
            attractions: List of attractions
            days: Number of days
            trip_type: Type of trip
            destination: City name
            restaurants: List of restaurant recommendations
            accommodation_location: Hotel coordinates
            
        Returns:
            Complete itinerary with meals integrated
        """
        logger.info(f"Creating {days}-day itinerary with integrated dining")
        
        # Step 1: Geocode attractions
        attractions = self._geocode_attractions(attractions, destination)
        
        # Step 2: Validate geocoding
        attractions = self._validate_geocoding(attractions, destination)
        
        # Step 3: Filter attractions for day trips if needed
        if days == 1:
            # Get city center or use accommodation as reference
            try:
                center_location = accommodation_location or geocode(destination, limit=1)[0]
                attractions = self._filter_day_trip_attractions(attractions, center_location, days)
            except:
                logger.warning("Could not determine center location for day trip filtering")
        
        if not attractions:
            logger.warning("No valid attractions after filtering!")
            return self._generate_empty_schedule(days, trip_type)
        
        # Step 4: Split attractions across days
        per_day = max(1, len(attractions) // days)
        daily_groups = []
        
        for day in range(days):
            start_idx = day * per_day
            end_idx = start_idx + per_day if day < days - 1 else len(attractions)
            daily_groups.append(attractions[start_idx:end_idx])
        
        # Step 5: Optimize routes within each day
        daily_groups = self._optimize_daily_routes(daily_groups, accommodation_location)
        
        # Step 6: Integrate dining if restaurants provided
        if restaurants and accommodation_location:
            # Geocode restaurants first
            for restaurant in restaurants:
                if not restaurant.get('coordinates'):
                    query = f"{restaurant['name']}, {destination}"
                    try:
                        coords = geocode(query, limit=1)
                        if coords:
                            restaurant['coordinates'] = {
                                'lat': coords[0][0],
                                'lng': coords[0][1]
                            }
                    except:
                        pass
            
            daily_groups = self._integrate_dining(
                daily_groups,
                restaurants,
                accommodation_location
            )
        
        # Step 7: Create detailed schedule
        schedule = self._generate_complete_schedule(daily_groups, days, trip_type)
        
        return schedule
    
    def _generate_empty_schedule(self, days: int, trip_type: str) -> Dict:
        """Generate empty schedule when no valid attractions found"""
        return {
            "itinerary": [{
                "day": day + 1,
                "theme": f"Day {day + 1} - No valid attractions found",
                "activities": [],
                "total_activities": 0,
                "total_meals": 0
            } for day in range(days)],
            "summary": {
                "total_days": days,
                "total_attractions": 0,
                "total_meals_planned": 0,
                "optimization_applied": False,
                "warning": "No valid attractions found within reasonable distance"
            },
            "travel_tips": ["Consider expanding search radius or checking destination name"],
            "packing_suggestions": []
        }
    
    def _generate_complete_schedule(
        self,
        daily_groups: List[List[Dict]],
        days: int,
        trip_type: str
    ) -> Dict:
        """Generate complete schedule with attractions and meals using pre-calculated times"""
        
        itinerary = []
        total_warnings = []
        
        for day_num, day_items in enumerate(daily_groups, 1):
            activities = []
            day_warnings = []
            
            for idx, item in enumerate(day_items):
                # Check for overflow times
                if item.get('scheduled_time', '').startswith('Day+'):
                    day_warnings.append(f"{item['name']} scheduled beyond day boundary")
                
                if item.get('is_meal'):
                    # This is a restaurant
                    activity = {
                        "time": item.get('scheduled_time', '12:00'),
                        "type": "meal",
                        "meal_type": item.get('meal_type_scheduled', 'meal'),
                        "name": item['name'],
                        "cuisine": item.get('cuisine', 'various'),
                        "price_range": item.get('price_range', '$$'),
                        "location": item.get('location', 'N/A'),
                        "must_try": item.get('must_try', ''),
                        "duration": "1 hour",
                        "description": f"{item.get('meal_type_scheduled', 'Meal').title()} at {item['name']}"
                    }
                    
                    if item.get('distance_from_current'):
                        activity['travel_to_restaurant'] = {
                            'distance_km': round(item['distance_from_current']['distance_km'], 1),
                            'duration_minutes': item['distance_from_current']['duration_minutes']
                        }
                    
                    if item.get('travel_to_next'):
                        activity['travel_after'] = {
                            'distance_km': round(item['travel_to_next']['distance_km'], 1),
                            'duration_h': item['travel_to_next']['duration_h']
                        }
                    
                    activities.append(activity)
                    
                else:
                    # This is an attraction
                    activity = {
                        "time": item.get('scheduled_time', '09:00'),
                        "type": "attraction",
                        "name": item.get("name", "Unknown"),
                        "duration": item.get('duration', '2 hours'),
                        "category": item.get("category", "activity"),
                        "description": item.get("description", ""),
                        "notes": f"Best time: {item.get('best_time', 'anytime')}"
                    }
                    
                    if item.get('travel_to_next'):
                        activity['travel_after'] = {
                            'distance_km': round(item['travel_to_next']['distance_km'], 1),
                            'duration_h': item['travel_to_next']['duration_h']
                        }
                    
                    activities.append(activity)
            
            # Calculate day end time (handling overflow)
            if activities:
                last_activity_time = activities[-1]['time']
                if 'Day+' in last_activity_time:
                    end_time = "Beyond day boundary"
                else:
                    last_hour = int(last_activity_time.split(':')[0])
                    last_duration = self._parse_duration(activities[-1].get('duration', '1 hour'))
                    end_time_hours = last_hour + last_duration
                    end_time = self._format_time_with_overflow(end_time_hours)
                
                day_summary = {
                    "day": day_num,
                    "theme": f"Day {day_num} - {trip_type.title()} Experience",
                    "start_time": activities[0]['time'] if activities else "09:00",
                    "end_time": end_time,
                    "activities": activities,
                    "total_activities": len([a for a in activities if a.get('type') != 'meal']),
                    "total_meals": len([a for a in activities if a.get('type') == 'meal']),
                    "total_travel_time_hours": round(sum(
                        a.get('travel_after', {}).get('duration_h', 0) + 
                        (a.get('travel_to_restaurant', {}).get('duration_minutes', 0) / 60)
                        for a in activities
                    ), 1)
                }
                
                if day_warnings:
                    day_summary["warnings"] = day_warnings
                    total_warnings.extend(day_warnings)
            else:
                day_summary = {
                    "day": day_num,
                    "theme": f"Day {day_num} - Free Day",
                    "activities": [],
                    "total_activities": 0,
                    "total_meals": 0,
                    "total_travel_time_hours": 0
                }
            
            itinerary.append(day_summary)
        
        result = {
            "itinerary": itinerary,
            "summary": {
                "total_days": days,
                "total_attractions": sum(day['total_activities'] for day in itinerary),
                "total_meals_planned": sum(day['total_meals'] for day in itinerary),
                "optimization_applied": True,
                "total_travel_hours": round(sum(day.get('total_travel_time_hours', 0) for day in itinerary), 1)
            },
            "travel_tips": [
                "Schedule includes 15-minute buffers between activities",
                "Meal times are strategically placed near attractions",
                "Routes are optimized to minimize travel time",
                "Check opening hours and book restaurants in advance",
                "For day trips, stay within 50km of city center"
            ],
            "packing_suggestions": [
                "Comfortable walking shoes",
                "Water bottle and snacks",
                "Phone charger/power bank",
                "Weather-appropriate clothing",
                "Small backpack for day trips"
            ]
        }
        
        if total_warnings:
            result["warnings"] = list(set(total_warnings))
        
        return result