"""
Fill the database with sample destinations, places, transport rates and
distances so the site is usable straight after installation.

Run it with:   python manage.py seed_data

Every price here is a DEMONSTRATION ESTIMATE, not a live market price.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from travel.models import Destination, RouteDistance, TouristPlace, Transportation

TRANSPORT = [
    # code, name, Rs/km, km/h, seats per vehicle, ticket per person?
    ("car", "Car", "12.00", 55, 4, False),
    ("bike", "Bike", "3.50", 45, 2, False),
    ("bus", "Bus", "1.80", 45, 1, True),
    ("train", "Train", "1.20", 65, 1, True),
    # Flight is a per-person ticket, like bus and train, so seats_per_unit is 1
    # and charged_per_person is True - the cost rules need no special case.
    #
    # 300 km/h is deliberately well under how fast an aircraft flies. The speed
    # here produces the "travel time" shown to the customer, and that journey
    # is door to door: reaching the airport, checking in, security, boarding
    # and the trip into the city at the far end. Quoting cruising speed would
    # tell someone a 450 km hop takes 50 minutes, which no traveller has ever
    # experienced.
    ("flight", "Flight", "7.00", 300, 1, True),
]

DESTINATIONS = [
    {
        "name": "Mumbai",
        "state": "Maharashtra",
        "description": "India's busiest coastal city: colonial landmarks, long "
                       "sea-facing promenades, street food and Bollywood.",
        "cost": "3000",
        "days": 3,
        "places": [
            ("Gateway of India", "historical", "0", 60,
             "Open all day; busiest in the evening",
             "The 26-metre arch on the waterfront, built in 1924. The starting "
             "point for ferries to Elephanta Caves."),
            ("Marine Drive", "nature", "0", 90,
             "Open all day; best at sunset",
             "A 3.6 km curved promenade along the Arabian Sea, nicknamed the "
             "Queen's Necklace for its night-time street lights."),
            ("Juhu Beach", "beach", "0", 120,
             "Open all day; evenings are liveliest",
             "A wide, busy beach in the suburbs known for its food stalls "
             "selling pav bhaji and bhel puri."),
            ("Colaba Causeway", "shopping", "0", 90,
             "Shops usually 10 AM - 9 PM",
             "A long street market for clothes, jewellery and souvenirs, "
             "surrounded by cafes and old buildings."),
            ("Siddhivinayak Temple", "temple", "0", 60,
             "Usually 5:30 AM - 9:30 PM",
             "One of Mumbai's most visited Hindu temples, dedicated to Lord "
             "Ganesha. Expect queues on Tuesdays."),
            ("Elephanta Caves", "historical", "40", 240,
             "Closed Mondays; ferry from Gateway of India",
             "Rock-cut cave temples on an island, a UNESCO World Heritage Site. "
             "Allow half a day including the ferry."),
            ("Chhatrapati Shivaji Maharaj Museum", "museum", "85", 120,
             "Usually 10 AM - 6 PM",
             "A large museum of Indian art, archaeology and natural history in "
             "a domed heritage building."),
        ],
    },
    {
        "name": "Goa",
        "state": "Goa",
        "description": "Beaches, Portuguese churches, spice plantations and a "
                       "relaxed pace of life.",
        "cost": "3500",
        "days": 4,
        "places": [
            ("Baga Beach", "beach", "0", 150, "Open all day",
             "A lively north Goa beach with water sports and shacks."),
            ("Basilica of Bom Jesus", "historical", "0", 60,
             "Usually 9 AM - 6:30 PM",
             "A UNESCO-listed 16th century church in Old Goa."),
            ("Dudhsagar Falls", "nature", "400", 300,
             "Jeep safari; best after the monsoon",
             "A four-tiered waterfall on the Mandovi river."),
            ("Anjuna Flea Market", "shopping", "0", 120,
             "Wednesdays in season",
             "A long-running market for clothes, spices and handicrafts."),
        ],
    },
    {
        "name": "Hyderabad",
        "state": "Telangana",
        "description": "The city of pearls and biryani, with Qutb Shahi "
                       "monuments and a large modern tech district.",
        "cost": "2400",
        "days": 3,
        "places": [
            ("Charminar", "historical", "25", 60, "Usually 9:30 AM - 5:30 PM",
             "The 1591 four-minaret monument at the centre of the old city."),
            ("Golconda Fort", "historical", "25", 180, "Usually 9 AM - 5:30 PM",
             "A hilltop fort famous for its acoustics and sound-and-light show."),
            ("Ramoji Film City", "adventure", "1350", 480, "Usually 9 AM - 5:30 PM",
             "A very large film studio complex and theme park."),
            ("Laad Bazaar", "shopping", "0", 90, "Shops usually 11 AM - 9 PM",
             "The lane beside Charminar known for lacquer bangles and pearls."),
            ("Birla Mandir", "temple", "0", 60, "Usually 7 AM - 9 PM",
             "A white marble hilltop temple with views over the city."),
        ],
    },
    {
        "name": "Jaipur",
        "state": "Rajasthan",
        "description": "The Pink City: forts, palaces, block-printed textiles "
                       "and desert cuisine.",
        "cost": "2800",
        "days": 3,
        "places": [
            ("Amber Fort", "historical", "100", 180, "Usually 8 AM - 5:30 PM",
             "A hilltop fort-palace of sandstone and marble."),
            ("Hawa Mahal", "historical", "50", 60, "Usually 9 AM - 4:30 PM",
             "The five-storey 'Palace of Winds' with 953 small windows."),
            ("City Palace", "museum", "200", 120, "Usually 9:30 AM - 5 PM",
             "The royal residence complex with museums and courtyards."),
            ("Johari Bazaar", "shopping", "0", 90, "Shops usually 11 AM - 8 PM",
             "The old jewellery market of the walled city."),
        ],
    },
    {
        "name": "Munnar",
        "state": "Kerala",
        "description": "Cool hill station covered in tea plantations, with "
                       "waterfalls and wildlife nearby.",
        "cost": "2600",
        "days": 3,
        "places": [
            ("Tea Museum", "museum", "125", 90, "Closed Mondays",
             "Working tea factory and museum showing how tea is processed."),
            ("Eravikulam National Park", "nature", "150", 180, "Usually 8 AM - 4 PM",
             "Home of the Nilgiri tahr, with rolling grassland views."),
            ("Attukad Waterfalls", "nature", "0", 90, "Open all day",
             "A wide waterfall reached by a short walk through spice gardens."),
        ],
    },
    {
        "name": "Visakhapatnam",
        "state": "Andhra Pradesh",
        "description": "A port city between the hills and the Bay of Bengal, "
                       "with beaches and the Araku valley nearby.",
        "cost": "2200",
        "days": 3,
        "places": [
            ("RK Beach", "beach", "0", 120, "Open all day",
             "The main city beach with a promenade and a submarine museum."),
            ("Kailasagiri", "nature", "50", 120, "Usually 9 AM - 8 PM",
             "A hilltop park with a ropeway and views over the coastline."),
            ("Borra Caves", "adventure", "60", 150, "Usually 10 AM - 5 PM",
             "Million-year-old limestone caves in the Araku valley."),
            ("Simhachalam Temple", "temple", "0", 90, "Usually 7 AM - 8 PM",
             "An 11th century hilltop temple in Kalinga architecture."),
        ],
    },
]

DISTANCES = [
    ("Pune", "Mumbai", 150),
    ("Hyderabad", "Bengaluru", 570),
    ("Hyderabad", "Goa", 660),
    ("Hyderabad", "Mumbai", 710),
    ("Hyderabad", "Visakhapatnam", 620),
    ("Vijayawada", "Hyderabad", 275),
    ("Vijayawada", "Visakhapatnam", 350),
    ("Mumbai", "Goa", 590),
    ("Delhi", "Jaipur", 280),
    ("Chennai", "Bengaluru", 350),
    ("Kochi", "Munnar", 130),
    ("Pune", "Goa", 450),
]


# Photographs for the destination cards and the place pickers.
#
# These are Wikimedia Commons files, served straight from upload.wikimedia.org
# at their pre-rendered 500px width - roughly 77 KB each rather than the 1-7 MB
# originals. Commons only serves a fixed set of widths; 500 is one of them, and
# asking for an arbitrary size returns HTTP 400.
#
# They are URLs rather than uploaded files on purpose: Render's free plan has an
# ephemeral filesystem, so anything written into media/ disappears on the next
# deploy. Both models already prefer an uploaded file when one exists and fall
# back to this URL, so uploading through the admin later overrides these.
#
# Every URL here was checked to return 200 with an image content-type.
IMAGES = {
    # --- destinations ---
    "Mumbai":                              "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Mumbai_Bandra-Worli_Sea_Link.jpg/500px-Mumbai_Bandra-Worli_Sea_Link.jpg",
    "Goa":                                 "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/BeachFun.jpg/500px-BeachFun.jpg",
    "Hyderabad":                           "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Downtown_hyderabad_drone.png/500px-Downtown_hyderabad_drone.png",
    "Jaipur":                              "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/East_facade_Hawa_Mahal_Jaipur_from_ground_level_%28July_2022%29_-_img_01.jpg/500px-East_facade_Hawa_Mahal_Jaipur_from_ground_level_%28July_2022%29_-_img_01.jpg",
    "Munnar":                              "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Munnar_Overview.jpg/500px-Munnar_Overview.jpg",
    "Visakhapatnam":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/What_is_Shipyard.jpg/500px-What_is_Shipyard.jpg",
    # --- tourist places ---
    "Gateway of India":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Mumbai_03-2016_30_Gateway_of_India.jpg/500px-Mumbai_03-2016_30_Gateway_of_India.jpg",
    "Marine Drive":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/74/Mumbai_03-2016_27_skyline_at_Marine_Drive.jpg/500px-Mumbai_03-2016_27_skyline_at_Marine_Drive.jpg",
    "Juhu Beach":                          "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/Juhu_beach_%28Arial%29.jpg/500px-Juhu_beach_%28Arial%29.jpg",
    "Colaba Causeway":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Colaba_Causeway%2CMumbai_-_panoramio.jpg/500px-Colaba_Causeway%2CMumbai_-_panoramio.jpg",
    "Siddhivinayak Temple":                "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Shree_Siddhivinayak_Temple_Mumbai.jpg/500px-Shree_Siddhivinayak_Temple_Mumbai.jpg",
    "Elephanta Caves":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Elephanta_Caves_Trimurti.jpg/500px-Elephanta_Caves_Trimurti.jpg",
    "Chhatrapati Shivaji Maharaj Museum":  "https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/Chhatrapati_Shivaji_Maharaj_Vastu_Sangrahalaya.jpg/500px-Chhatrapati_Shivaji_Maharaj_Vastu_Sangrahalaya.jpg",
    "Baga Beach":                          "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Baga_Beach%2C_Calangute%2C_Goa.jpg/500px-Baga_Beach%2C_Calangute%2C_Goa.jpg",
    "Basilica of Bom Jesus":               "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Front_Elevation_of_Basilica_of_Bom_Jesus.jpg/500px-Front_Elevation_of_Basilica_of_Bom_Jesus.jpg",
    "Dudhsagar Falls":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Doodhsagar_Fall.jpg/500px-Doodhsagar_Fall.jpg",
    "Anjuna Flea Market":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/Anjuna_Beach%2C_Goa%2C_India%2C_Legendary_Curlies_beach_shack.jpg/500px-Anjuna_Beach%2C_Goa%2C_India%2C_Legendary_Curlies_beach_shack.jpg",
    "Charminar":                           "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Charminar_Hyderabad_1.jpg/500px-Charminar_Hyderabad_1.jpg",
    "Golconda Fort":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Golconda_Fort_005.jpg/500px-Golconda_Fort_005.jpg",
    "Ramoji Film City":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Ramoji_Film_City.jpg/500px-Ramoji_Film_City.jpg",
    "Laad Bazaar":                         "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Laad_Bazaar.jpg/500px-Laad_Bazaar.jpg",
    "Birla Mandir":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/Birla_Mandir%2C_Hyderabad.png/500px-Birla_Mandir%2C_Hyderabad.png",
    "Amber Fort":                          "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/20191219_Fort_Amber%2C_Amer%2C_Jaipur_0955_9481.jpg/500px-20191219_Fort_Amber%2C_Amer%2C_Jaipur_0955_9481.jpg",
    "Hawa Mahal":                          "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/East_facade_Hawa_Mahal_Jaipur_from_ground_level_%28July_2022%29_-_img_01.jpg/500px-East_facade_Hawa_Mahal_Jaipur_from_ground_level_%28July_2022%29_-_img_01.jpg",
    "City Palace":                         "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Chandra_Mahal%2C_City_Palace%2C_Jaipur%2C_20191218_0951_9043.jpg/500px-Chandra_Mahal%2C_City_Palace%2C_Jaipur%2C_20191218_0951_9043.jpg",
    "Johari Bazaar":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Johari_Bazaar%2C_Jaipur.jpg/500px-Johari_Bazaar%2C_Jaipur.jpg",
    "Tea Museum":                          "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Stepwise_processing_of_tea_in_Tea_Museum_%2C_Munnar_05.jpg/500px-Stepwise_processing_of_tea_in_Tea_Museum_%2C_Munnar_05.jpg",
    "Eravikulam National Park":            "https://upload.wikimedia.org/wikipedia/commons/thumb/6/60/Eravikulam_National_Park_%2849444006652%29.jpg/500px-Eravikulam_National_Park_%2849444006652%29.jpg",
    "Attukad Waterfalls":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Attukad_Waterfalls1.jpg/500px-Attukad_Waterfalls1.jpg",
    "RK Beach":                            "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/RK_Beach_Night.jpg/500px-RK_Beach_Night.jpg",
    "Kailasagiri":                         "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Kailasagiri.jpg/500px-Kailasagiri.jpg",
    "Borra Caves":                         "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Borra_caves%2C_Viskhapatnam.jpg/500px-Borra_caves%2C_Viskhapatnam.jpg",
    "Simhachalam Temple":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Simhachalam_temple_from_a_hilltop.jpg/500px-Simhachalam_temple_from_a_hilltop.jpg",
}

class Command(BaseCommand):
    help = "Load sample destinations, tourist places, transport rates and distances."

    def handle(self, *args, **options):
        # --- transportation ------------------------------------------------
        for code, name, rate, speed, seats, per_person in TRANSPORT:
            Transportation.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "cost_per_km": Decimal(rate),
                    "average_speed_kmph": speed,
                    "seats_per_unit": seats,
                    "charged_per_person": per_person,
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Transportation options: {len(TRANSPORT)}"))

        # --- destinations and places ---------------------------------------
        place_total = 0
        for item in DESTINATIONS:
            destination, _ = Destination.objects.update_or_create(
                name=item["name"],
                defaults={
                    "state": item["state"],
                    "country": "India",
                    "description": item["description"],
                    "estimated_cost_per_day": Decimal(item["cost"]),
                    "recommended_days": item["days"],
                    "is_popular": True,
                    "image_url": IMAGES.get(item["name"], ""),
                },
            )
            for name, category, fee, minutes, opening, description in item["places"]:
                TouristPlace.objects.update_or_create(
                    destination=destination,
                    name=name,
                    defaults={
                        "category": category,
                        "entry_fee": Decimal(fee),
                        "visit_duration_minutes": minutes,
                        "opening_info": opening,
                        "description": description,
                        "image_url": IMAGES.get(name, ""),
                    },
                )
                place_total += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Destinations: {len(DESTINATIONS)}, tourist places: {place_total}"
            )
        )

        # --- distances ------------------------------------------------------
        for source, target, km in DISTANCES:
            RouteDistance.objects.update_or_create(
                from_city=source, to_city=target, defaults={"distance_km": km}
            )
        self.stdout.write(self.style.SUCCESS(f"Route distances: {len(DISTANCES)}"))

        self.stdout.write(
            self.style.WARNING(
                "\nReminder: every price and distance loaded here is a "
                "DEMONSTRATION ESTIMATE, not a live market price."
            )
        )
