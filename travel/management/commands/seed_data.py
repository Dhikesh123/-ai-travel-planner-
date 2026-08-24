"""
Fill the database with sample destinations, places, transport rates and
distances so the site is usable straight after installation.

Run it with:   python manage.py seed_data

Every price here is a DEMONSTRATION ESTIMATE, not a live market price.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from travel.models import (
    Destination,
    RouteDistance,
    Theme,
    TouristPlace,
    Transportation,
)

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
    {
        "name": "Delhi",
        "state": "Delhi",
        "description": "The capital: Mughal forts and tombs, wide colonial "
                       "avenues, and some of the country's best street food.",
        "cost": "2800",
        "days": 3,
        "places": [
            ("Red Fort", "historical", "35", 120,
             "9:30 AM - 4:30 PM, closed Monday",
             "The walled Mughal palace of Shah Jahan, built in red sandstone "
             "in 1648 and the site of the Independence Day address."),
            ("Qutub Minar", "historical", "35", 90,
             "Usually 7 AM - 5 PM",
             "A 73-metre victory tower begun in 1193, the tallest brick "
             "minaret in the world, ringed by early Indo-Islamic ruins."),
            ("Humayun's Tomb", "historical", "35", 90,
             "Usually sunrise to sunset",
             "The garden tomb that set the pattern later followed by the Taj "
             "Mahal, finished in 1572."),
            ("Lotus Temple", "temple", "0", 60,
             "9 AM - 5:30 PM, closed Monday",
             "A Bahai house of worship shaped as a white marble lotus, open "
             "to visitors of every faith for silent prayer."),
            ("Chandni Chowk", "shopping", "0", 120,
             "Shops usually 11 AM - 8 PM, quiet on Sunday",
             "The old city's market street: spices, sweets, fabric and "
             "parathas in lanes laid out in the 17th century."),
            ("India Gate", "historical", "0", 45,
             "Open all day; lit after dark",
             "A 42-metre war memorial to the Indian soldiers of the First "
             "World War, at the end of the ceremonial Rajpath."),
        ],
    },
    {
        "name": "Agra",
        "state": "Uttar Pradesh",
        "description": "A Mughal capital on the Yamuna, holding the Taj Mahal "
                       "and two more UNESCO World Heritage sites.",
        "cost": "2400",
        "days": 2,
        "places": [
            ("Taj Mahal", "historical", "50", 180,
             "Sunrise to sunset, closed Friday",
             "The marble mausoleum Shah Jahan built for Mumtaz Mahal between "
             "1632 and 1653. Best entered at opening for the light."),
            ("Agra Fort", "historical", "40", 120,
             "Usually sunrise to sunset",
             "The red sandstone fort that served as the main Mughal residence "
             "until 1638, with a view across the river to the Taj."),
            ("Fatehpur Sikri", "historical", "40", 150,
             "Usually sunrise to sunset",
             "Akbar's planned capital of 1571, abandoned within 15 years and "
             "left almost intact 40 km outside the city."),
            ("Mehtab Bagh", "nature", "25", 60,
             "Usually sunrise to sunset",
             "A riverside garden directly across from the Taj Mahal, laid out "
             "on the axis of the tomb and best at sunset."),
            ("Itmad-ud-Daulah", "historical", "30", 60,
             "Usually sunrise to sunset",
             "Known as the Baby Taj: the first Mughal tomb faced entirely in "
             "marble, with fine inlaid stonework."),
        ],
    },
    {
        "name": "Varanasi",
        "state": "Uttar Pradesh",
        "description": "One of the oldest continuously lived-in cities on "
                       "earth, built along the ghats of the Ganges.",
        "cost": "2000",
        "days": 3,
        "places": [
            ("Dashashwamedh Ghat", "temple", "0", 90,
             "Open all day; Ganga Aarti about 6:30 PM",
             "The main ghat on the Ganges, where the evening fire ceremony "
             "draws crowds onto the steps and into boats."),
            ("Kashi Vishwanath Temple", "temple", "0", 60,
             "Usually 3 AM - 11 PM",
             "One of the twelve Jyotirlinga shrines to Shiva, rebuilt in 1780 "
             "and the religious centre of the old city."),
            ("Sarnath", "historical", "25", 120,
             "Usually sunrise to sunset",
             "Where the Buddha gave his first sermon after enlightenment; "
             "stupas, a monastery ruin and an archaeological museum."),
            ("Assi Ghat", "nature", "0", 60,
             "Open all day; best at sunrise",
             "The southern-most main ghat, quieter than the centre and the "
             "usual starting point for a dawn boat ride."),
            ("Banaras Silk Weavers Market", "shopping", "0", 90,
             "Shops usually 10 AM - 8 PM",
             "Workshops and showrooms for Banarasi silk saris, woven on "
             "handlooms in the lanes around Peeli Kothi."),
        ],
    },
    {
        "name": "Amritsar",
        "state": "Punjab",
        "description": "Home of the Golden Temple, the spiritual centre of "
                       "Sikhism, and a border city with a strong food culture.",
        "cost": "2000",
        "days": 2,
        "places": [
            ("Golden Temple", "temple", "0", 150,
             "Open 24 hours",
             "The Harmandir Sahib, gilded and set in a sacred pool, serving a "
             "free community meal to tens of thousands every day."),
            ("Jallianwala Bagh", "historical", "0", 60,
             "Usually 6:30 AM - 7:30 PM",
             "The walled garden where troops fired on an unarmed gathering in "
             "1919; the bullet marks are still in the brickwork."),
            ("Wagah Border Ceremony", "historical", "0", 120,
             "Ceremony about 5:15 PM, arrive by 3:30 PM",
             "The daily flag-lowering drill at the India-Pakistan border, "
             "performed by both sides to a stadium crowd."),
            ("Partition Museum", "museum", "250", 120,
             "10 AM - 6 PM, closed Monday",
             "First-hand accounts, letters and objects from the 1947 "
             "partition, told largely through survivor testimony."),
            ("Hall Bazaar", "shopping", "0", 90,
             "Shops usually 11 AM - 9 PM",
             "A covered market for phulkari embroidery, juttis and papad, "
             "entered through a Victorian clock-tower gate."),
        ],
    },
    {
        "name": "Rishikesh",
        "state": "Uttarakhand",
        "description": "Where the Ganges leaves the Himalaya: ashrams, "
                       "suspension bridges and white-water rafting.",
        "cost": "1800",
        "days": 3,
        "places": [
            ("Laxman Jhula", "historical", "0", 45,
             "Open all day",
             "An iron suspension footbridge over the Ganges, built in 1929 on "
             "the spot where legend has Lakshmana crossing on jute rope."),
            ("Triveni Ghat", "temple", "0", 60,
             "Open all day; Aarti about 6 PM",
             "The main bathing ghat, where lamps are floated on the river at "
             "the evening ceremony."),
            ("Ganga Rafting", "adventure", "1200", 180,
             "Season roughly September to June",
             "Grade II-III white water on the run from Shivpuri down to town, "
             "about 16 km of rapids."),
            ("Beatles Ashram", "historical", "150", 90,
             "Usually 10 AM - 4 PM",
             "The abandoned Maharishi ashram where the Beatles wrote much of "
             "the White Album in 1968, now covered in murals."),
            ("Neelkanth Mahadev Temple", "temple", "0", 120,
             "Usually 5 AM - 7 PM",
             "A hill temple 32 km above the town, on the site where Shiva is "
             "said to have swallowed the poison of the churning ocean."),
        ],
    },
    {
        "name": "Shimla",
        "state": "Himachal Pradesh",
        "description": "The British summer capital, strung along a Himalayan "
                       "ridge with colonial architecture and pine forest.",
        "cost": "2600",
        "days": 3,
        "places": [
            ("The Ridge", "nature", "0", 60,
             "Open all day",
             "The open promenade along the crest of the town, with views to "
             "the snow line on a clear day."),
            ("Jakhoo Temple", "temple", "0", 90,
             "Usually 5 AM - 8 PM",
             "A Hanuman temple at the highest point in Shimla, reached by a "
             "steep walk up through cedar forest."),
            ("Kalka-Shimla Toy Train", "adventure", "500", 300,
             "Several departures daily",
             "A UNESCO-listed narrow gauge line of 1903, climbing 96 km "
             "through 102 tunnels."),
            ("Mall Road", "shopping", "0", 90,
             "Shops usually 10 AM - 9 PM",
             "The pedestrian shopping street below the Ridge, lined with "
             "half-timbered buildings and woollens shops."),
            ("Viceregal Lodge", "historical", "100", 90,
             "9 AM - 5 PM, closed Monday",
             "The 1888 residence of the British Viceroy, where the partition "
             "of India was discussed in 1947."),
        ],
    },
    {
        "name": "Manali",
        "state": "Himachal Pradesh",
        "description": "A high valley town under the Rohtang pass, the base "
                       "for snow, trekking and the road to Ladakh.",
        "cost": "2600",
        "days": 4,
        "places": [
            ("Hadimba Temple", "temple", "0", 60,
             "Usually 8 AM - 6 PM",
             "A 1553 pagoda of cedar and stone in a deodar grove, built "
             "around a natural rock rather than an idol."),
            ("Solang Valley", "adventure", "800", 180,
             "Open all year; snow roughly December to March",
             "A side valley used for paragliding and zorbing in summer and "
             "skiing in winter."),
            ("Old Manali", "shopping", "0", 90,
             "Cafes usually 9 AM - 11 PM",
             "Orchards, guesthouses and cafes on the far bank of the Manalsu, "
             "quieter than the main bazaar."),
            ("Vashisht Hot Springs", "nature", "0", 60,
             "Usually 6 AM - 8 PM",
             "Natural sulphur springs feeding stone bathing tanks beside a "
             "village temple."),
            ("Rohtang Pass", "nature", "550", 240,
             "Open roughly May to October, permit required",
             "A 3,978-metre pass on the road north, snowbound for much of the "
             "year and closed without notice in bad weather."),
        ],
    },
    {
        "name": "Udaipur",
        "state": "Rajasthan",
        "description": "The lake city of Mewar: palaces on the water, "
                       "havelis and the Aravalli hills behind.",
        "cost": "2800",
        "days": 3,
        "places": [
            ("City Palace", "historical", "300", 150,
             "Usually 9:30 AM - 5:30 PM",
             "The largest palace complex in Rajasthan, built up by 22 rulers "
             "over four centuries above Lake Pichola."),
            ("Lake Pichola Boat Ride", "nature", "400", 60,
             "Boats roughly 10 AM - 6 PM",
             "An hour on the water past Jag Mandir and the island palaces, "
             "best on the sunset departure."),
            ("Jagdish Temple", "temple", "0", 45,
             "Usually 4:15 AM - 1 PM and 5 PM - 8 PM",
             "An Indo-Aryan temple of 1651 to Vishnu, reached by 32 marble "
             "steps from the bazaar."),
            ("Saheliyon ki Bari", "nature", "50", 60,
             "Usually 9 AM - 7 PM",
             "A garden of fountains and lotus pools laid out in the 18th "
             "century for the queen's attendants."),
            ("Bagore ki Haveli", "museum", "100", 90,
             "Usually 10 AM - 7 PM, dance show 7 PM",
             "A restored 18th century mansion on the ghats, with a nightly "
             "programme of Rajasthani folk dance."),
        ],
    },
    {
        "name": "Jodhpur",
        "state": "Rajasthan",
        "description": "The blue city at the edge of the Thar, under one of "
                       "the largest hill forts in India.",
        "cost": "2400",
        "days": 2,
        "places": [
            ("Mehrangarh Fort", "historical", "200", 150,
             "Usually 9 AM - 5 PM",
             "A fort begun in 1459 standing 122 metres above the city, with "
             "its walls cut from the rock it sits on."),
            ("Jaswant Thada", "historical", "50", 45,
             "Usually 9 AM - 5 PM",
             "A marble cenotaph of 1899 beside the fort, carved thin enough "
             "that the sheets glow in direct sun."),
            ("Clock Tower Market", "shopping", "0", 90,
             "Shops usually 10 AM - 9 PM",
             "The Sardar Market around the 19th century clock tower: spices, "
             "textiles and lacquer bangles."),
            ("Umaid Bhawan Palace", "museum", "100", 60,
             "Museum usually 9 AM - 5 PM",
             "One of the world's largest private residences, finished in 1943 "
             "as a famine relief project. Part museum, part hotel."),
            ("Mandore Gardens", "nature", "0", 90,
             "Usually 8 AM - 8 PM",
             "The old Marwar capital 9 km north, with royal cenotaphs built "
             "as temples among rock terraces."),
        ],
    },
    {
        "name": "Bengaluru",
        "state": "Karnataka",
        "description": "A high-altitude garden city turned technology "
                       "capital, with parks, palaces and a long cafe culture.",
        "cost": "2800",
        "days": 2,
        "places": [
            ("Lalbagh Botanical Garden", "nature", "25", 120,
             "Usually 6 AM - 7 PM",
             "240 acres laid out by Hyder Ali in 1760, with a glass house "
             "modelled on the Crystal Palace."),
            ("Bangalore Palace", "historical", "230", 90,
             "Usually 10 AM - 5:30 PM",
             "An 1878 residence built in Tudor revival style, with fortified "
             "towers and wood-panelled interiors."),
            ("Cubbon Park", "nature", "0", 90,
             "Usually 6 AM - 6 PM",
             "300 acres of shade trees in the centre of the city, closed to "
             "traffic on Sundays."),
            ("ISKCON Temple Bengaluru", "temple", "0", 60,
             "Usually 4:15 AM - 8:20 PM",
             "A large hilltop Krishna temple opened in 1997, combining "
             "traditional and modern architecture."),
            ("Commercial Street", "shopping", "0", 120,
             "Shops usually 11 AM - 9 PM",
             "A dense grid of clothing, footwear and jewellery shops running "
             "back from the old cantonment."),
        ],
    },
    {
        "name": "Chennai",
        "state": "Tamil Nadu",
        "description": "A Coromandel coast capital with Dravidian temples, a "
                       "very long urban beach and Carnatic music.",
        "cost": "2400",
        "days": 3,
        "places": [
            ("Marina Beach", "beach", "0", 90,
             "Open all day; best early morning",
             "A 13 km stretch of sand along the Bay of Bengal, among the "
             "longest urban beaches anywhere."),
            ("Kapaleeshwarar Temple", "temple", "0", 60,
             "Usually 5 AM - 12 PM and 4 PM - 9 PM",
             "A 7th century Shiva temple rebuilt in the 16th, with a 37-metre "
             "gopuram covered in painted figures."),
            ("Fort St. George", "museum", "250", 90,
             "9 AM - 5 PM, closed Friday",
             "The first English fortress in India, begun in 1644 and still in "
             "government use, with a museum of the colonial period."),
            ("Government Museum Chennai", "museum", "75", 120,
             "9:30 AM - 5 PM, closed Friday",
             "Founded 1851, holding the finest collection of Chola bronzes "
             "anywhere in the country."),
            ("Mahabalipuram", "historical", "40", 180,
             "Usually sunrise to sunset",
             "Pallava rock-cut shrines and the Shore Temple, carved out of "
             "granite in the 7th and 8th centuries, 55 km south."),
        ],
    },
    {
        "name": "Mysuru",
        "state": "Karnataka",
        "description": "The old Wodeyar capital: a floodlit palace, "
                       "sandalwood and silk, under the Chamundi hills.",
        "cost": "2000",
        "days": 2,
        "places": [
            ("Mysore Palace", "historical", "70", 120,
             "10 AM - 5:30 PM; lit Sunday evenings",
             "The 1912 Indo-Saracenic seat of the Wodeyars, lit by nearly a "
             "hundred thousand bulbs on Sunday nights and during Dasara."),
            ("Chamundi Hill", "temple", "0", 120,
             "Temple usually 7:30 AM - 9 PM",
             "A 1,000-step climb past a monolithic Nandi bull to a temple "
             "1,062 metres above the plain."),
            ("Brindavan Gardens", "nature", "50", 120,
             "Usually 6:30 AM - 8 PM",
             "Terraced gardens below the Krishnarajasagara dam, with a "
             "musical fountain after dark."),
            ("Devaraja Market", "shopping", "0", 90,
             "Usually 6 AM - 8:30 PM",
             "A covered market from the reign of Tipu Sultan, stacked with "
             "flowers, bananas, kumkum powder and sandalwood oil."),
            ("St. Philomena Church", "historical", "0", 45,
             "Usually 5 AM - 6 PM",
             "A neo-Gothic cathedral of 1936 with twin 53-metre spires, "
             "modelled on Cologne."),
        ],
    },
    {
        "name": "Madurai",
        "state": "Tamil Nadu",
        "description": "A temple city on the Vaigai, continuously inhabited "
                       "for more than two thousand years.",
        "cost": "1800",
        "days": 2,
        "places": [
            ("Meenakshi Amman Temple", "temple", "0", 180,
             "Usually 5 AM - 12:30 PM and 4 PM - 9:30 PM",
             "Fourteen gopurams covered in thousands of painted figures, "
             "around shrines to Meenakshi and Sundareshwar."),
            ("Thirumalai Nayakkar Palace", "historical", "50", 60,
             "Usually 9 AM - 5 PM",
             "A 1636 palace of granite and stucco; only the entrance hall and "
             "dance chamber survive of the original."),
            ("Gandhi Memorial Museum", "museum", "0", 90,
             "10 AM - 1 PM and 2 PM - 5:45 PM",
             "Housed in a 17th century palace, holding the dhoti Gandhi was "
             "wearing when he was assassinated."),
            ("Alagar Kovil", "temple", "0", 120,
             "Usually 6 AM - 1 PM and 4 PM - 8 PM",
             "A hill temple to Vishnu 21 km north, central to the Chithirai "
             "festival procession."),
            ("Puthu Mandapam", "shopping", "0", 60,
             "Shops usually 9 AM - 9 PM",
             "A pillared 17th century hall outside the temple east gate, now "
             "a tailors and textile market."),
        ],
    },
    {
        "name": "Kochi",
        "state": "Kerala",
        "description": "A spice port layered with Portuguese, Dutch, Jewish "
                       "and British history, on a lagoon of islands.",
        "cost": "2400",
        "days": 3,
        "places": [
            ("Chinese Fishing Nets", "historical", "0", 45,
             "Best at sunrise and sunset",
             "Cantilevered shore-operated lift nets on the Fort Kochi "
             "waterfront, in use since the 14th century."),
            ("Mattancherry Palace", "museum", "10", 60,
             "10 AM - 5 PM, closed Friday",
             "A Portuguese-built palace of 1555, its walls covered in murals "
             "of the Ramayana in Kerala style."),
            ("Paradesi Synagogue", "historical", "10", 45,
             "10 AM - 5 PM, closed Friday and Saturday",
             "Built in 1568, the oldest active synagogue in the Commonwealth, "
             "floored in hand-painted Cantonese tiles."),
            ("Fort Kochi Beach", "beach", "0", 60,
             "Open all day",
             "A working shoreline rather than a swimming beach, lined with "
             "colonial godowns and cafes."),
            ("Kathakali Performance", "museum", "350", 120,
             "Make-up from about 5 PM, show 6:30 PM",
             "Kerala classical dance-drama, performed in costume and full "
             "face paint with the make-up done in view."),
        ],
    },
    {
        "name": "Alleppey",
        "state": "Kerala",
        "description": "The centre of the Kerala backwaters: canals, paddy "
                       "below sea level and converted rice barges.",
        "cost": "3000",
        "days": 2,
        "places": [
            ("Backwater Houseboat", "nature", "6000", 480,
             "Boats usually board about noon",
             "An overnight kettuvallam through the canals of Kuttanad, with a "
             "cook aboard. Priced per boat, not per person."),
            ("Alappuzha Beach", "beach", "0", 90,
             "Open all day",
             "A long shore with a 137-year-old pier running out into the "
             "Arabian Sea."),
            ("Marari Beach", "beach", "0", 120,
             "Open all day",
             "A quiet fishing village beach 11 km north, palm-backed and far "
             "less built up than the town."),
            ("Pathiramanal Island", "nature", "300", 120,
             "Daylight hours, reached by boat",
             "A ten-hectare island in Vembanad lake, a stopover for migratory "
             "birds between November and February."),
            ("Krishnapuram Palace", "museum", "25", 60,
             "9:30 AM - 4:30 PM, closed Monday",
             "An 18th century Travancore palace holding the Gajendra Moksha "
             "mural, one of the largest in Kerala."),
        ],
    },
    {
        "name": "Hampi",
        "state": "Karnataka",
        "description": "The ruined capital of Vijayanagara, spread over 26 "
                       "square kilometres of boulder-strewn river landscape.",
        "cost": "1600",
        "days": 3,
        "places": [
            ("Virupaksha Temple", "temple", "0", 90,
             "Usually 6 AM - 12:30 PM and 3 PM - 9 PM",
             "In continuous worship since the 7th century, making it one of "
             "the oldest functioning temples in India."),
            ("Vittala Temple", "historical", "40", 120,
             "Usually 8:30 AM - 5:30 PM",
             "Holds the stone chariot and the musical pillars that ring at "
             "different pitches when struck."),
            ("Hampi Bazaar", "historical", "0", 60,
             "Open all day",
             "A colonnaded street more than a kilometre long, once a market "
             "for horses and precious stones."),
            ("Matanga Hill", "adventure", "0", 90,
             "Best at sunrise",
             "The highest point in the ruins, a steep rock scramble with the "
             "whole site laid out below."),
            ("Lotus Mahal", "historical", "40", 60,
             "Usually 8:30 AM - 5:30 PM",
             "A two-storey pavilion in the royal enclosure, blending Islamic "
             "arches with Hindu bracketing."),
        ],
    },
    {
        "name": "Puducherry",
        "state": "Puducherry",
        "description": "A former French colony on the Coromandel coast, with "
                       "a gridded old quarter and an ashram.",
        "cost": "2200",
        "days": 2,
        "places": [
            ("Promenade Beach", "beach", "0", 60,
             "Traffic-free 6 PM - 7:30 AM",
             "A 1.5 km seafront walk past the old lighthouse and a Gandhi "
             "statue under carved pillars."),
            ("Sri Aurobindo Ashram", "temple", "0", 45,
             "8 AM - 12 PM and 2 PM - 6 PM",
             "Founded 1926; the samadhi in the courtyard is kept in silence."),
            ("Auroville", "nature", "0", 150,
             "Visitor centre 9 AM - 5:30 PM",
             "An experimental township begun in 1968, built around the golden "
             "Matrimandir sphere."),
            ("French Quarter", "historical", "0", 90,
             "Open all day",
             "Bougainvillea over mustard-yellow walls, on streets that kept "
             "their French names after 1954."),
            ("Paradise Beach", "beach", "150", 180,
             "Ferry roughly 9 AM - 4:30 PM",
             "A sandbar reached by boat across the Chunnambar backwater."),
        ],
    },
    {
        "name": "Tirupati",
        "state": "Andhra Pradesh",
        "description": "The hill shrine of Venkateswara at Tirumala, among the "
                       "most visited places of worship anywhere in the world.",
        "cost": "1800",
        "days": 2,
        "places": [
            ("Tirumala Venkateswara Temple", "temple", "300", 240,
             "Open almost around the clock; darshan by token",
             "The main shrine on the seventh hill. Queue times swing from two "
             "hours to more than twelve, so book a slotted darshan ahead."),
            ("Sri Padmavathi Temple", "temple", "0", 60,
             "Usually 6 AM - 8 PM",
             "At Tiruchanur, dedicated to the consort of Venkateswara. Custom "
             "is to visit here after Tirumala."),
            ("Sri Kapileswara Swamy Temple", "temple", "0", 60,
             "Usually 6 AM - 8 PM",
             "The only Shiva temple in Tirupati, beside a waterfall at the "
             "foot of the hills."),
            ("Silathoranam", "nature", "0", 45,
             "Daylight hours",
             "A natural rock arch on Tirumala, one of very few of its kind, "
             "dated to the Precambrian."),
        ],
    },
    {
        "name": "Srisailam",
        "state": "Andhra Pradesh",
        "description": "A Jyotirlinga and a Shakti Peetha on one hill above "
                       "the Krishna, inside a tiger reserve.",
        "cost": "1500",
        "days": 2,
        "places": [
            ("Mallikarjuna Jyotirlinga Temple", "temple", "0", 150,
             "Usually 4:30 AM - 10 PM",
             "One of the twelve Jyotirlingas and one of the eighteen Maha "
             "Shakti Peethas - a rare pairing at a single site."),
            ("Srisailam Dam", "nature", "0", 60,
             "Viewing usually 9 AM - 6 PM",
             "A masonry dam across the Krishna in a gorge, with a viewpoint "
             "over the reservoir."),
            ("Patala Ganga", "nature", "0", 60,
             "Daylight hours",
             "The bathing ghat on the Krishna below the temple, reached by a "
             "long stair or a ropeway."),
        ],
    },
    {
        "name": "Vijayawada",
        "state": "Andhra Pradesh",
        "description": "A Krishna-river city under the Indrakeeladri hill, "
                       "built around the Kanaka Durga temple.",
        "cost": "1800",
        "days": 2,
        "places": [
            ("Kanaka Durga Temple", "temple", "0", 120,
             "Usually 4 AM - 9 PM",
             "On Indrakeeladri hill above the Krishna, and one of the most "
             "visited Durga shrines in the south."),
            ("Undavalli Caves", "historical", "25", 90,
             "Usually 9 AM - 5:30 PM",
             "Four storeys cut into a sandstone hillside in the 7th century, "
             "holding a reclining Vishnu carved from one block."),
            ("Prakasam Barrage", "nature", "0", 45,
             "Open all day; lit after dark",
             "A 1,200-metre barrage across the Krishna, carrying road and "
             "canal traffic over the river."),
            ("Bhavani Island", "nature", "50", 120,
             "Ferries roughly 10 AM - 6 PM",
             "A river island upstream of the barrage, among the largest on "
             "any Indian river."),
        ],
    },
    {
        "name": "Srikalahasti",
        "state": "Andhra Pradesh",
        "description": "The Vayu Lingam temple on the Swarnamukhi, the place "
                       "people come to for Rahu-Ketu rituals.",
        "cost": "1400",
        "days": 1,
        "places": [
            ("Srikalahasteeswara Temple", "temple", "0", 150,
             "Usually 6 AM - 9 PM",
             "One of the Pancha Bhoota Sthalams, representing wind. The lamp "
             "in the inner shrine flickers in still air."),
            ("Kalahasti Fort", "historical", "0", 45,
             "Daylight hours",
             "Ruined ramparts on the hill behind the temple, with the town "
             "and the river below."),
            ("Bharadwaja Tirtham", "nature", "0", 45,
             "Daylight hours",
             "A spring and small waterfall in the hills a short way out of "
             "town, used for ritual bathing."),
        ],
    },
    {
        "name": "Annavaram",
        "state": "Andhra Pradesh",
        "description": "The Satyanarayana Swamy temple on Ratnagiri hill, "
                       "where vratam ceremonies run all day.",
        "cost": "1300",
        "days": 1,
        "places": [
            ("Sri Veera Venkata Satyanarayana Swamy Temple", "temple", "0", 150,
             "Usually 6 AM - 9 PM; vratam from early morning",
             "On Ratnagiri hill above the Pampa. Families come to perform the "
             "Satyanarayana vratam together."),
            ("Pampa River Ghat", "nature", "0", 45,
             "Daylight hours",
             "The bathing ghat at the foot of the hill, where pilgrims bathe "
             "before climbing."),
            ("Ratnagiri Hill Steps", "adventure", "0", 60,
             "Daylight hours",
             "The stepped path up the hill, an alternative to the ghat road "
             "for anyone walking."),
        ],
    },
    {
        "name": "Yadadri",
        "state": "Telangana",
        "description": "The Lakshmi Narasimha temple on Yadagirigutta, rebuilt "
                       "through the 2010s entirely in black granite.",
        "cost": "1400",
        "days": 1,
        "places": [
            ("Yadadri Lakshmi Narasimha Temple", "temple", "0", 150,
             "Usually 4 AM - 9 PM",
             "A cave shrine rebuilt as a granite complex, with the original "
             "rock sanctum kept at its heart."),
            ("Yadagirigutta Hill", "nature", "0", 45,
             "Daylight hours",
             "The hill the temple stands on, with the Telangana plain running "
             "out in every direction."),
            ("Sri Lakshmi Narasimha Pushkarini", "temple", "0", 30,
             "Daylight hours",
             "The temple tank below the complex, used for ritual bathing "
             "before darshan."),
        ],
    },
    {
        "name": "Bhadrachalam",
        "state": "Telangana",
        "description": "The Rama temple on the Godavari, at the place the "
                       "Ramayana associates with Parnasala.",
        "cost": "1400",
        "days": 2,
        "places": [
            ("Sri Sita Ramachandraswamy Temple", "temple", "0", 150,
             "Usually 4 AM - 9 PM",
             "Built in the 17th century by Kancherla Gopanna, whose songs to "
             "Rama are still sung as the Ramadasu kirtanas."),
            ("Parnasala", "historical", "0", 90,
             "Daylight hours",
             "35 km upriver, held by tradition to be where Sita was taken "
             "from the forest hut."),
            ("Godavari Ghat", "nature", "0", 45,
             "Open all day",
             "The riverfront steps below the temple, busiest during the "
             "Sri Rama Navami celebrations."),
        ],
    },
    {
        "name": "Basara",
        "state": "Telangana",
        "description": "One of very few Saraswati temples in India, where "
                       "children are brought for their first lesson.",
        "cost": "1200",
        "days": 1,
        "places": [
            ("Gnana Saraswati Temple", "temple", "0", 120,
             "Usually 4 AM - 8 PM",
             "On the Godavari. The Akshara Abhyasam ceremony, a child's first "
             "written letter, is performed here through the day."),
            ("Godavari Ghat Basara", "nature", "0", 45,
             "Daylight hours",
             "The bathing steps beside the temple, quieter than the larger "
             "river towns downstream."),
            ("Vyasa Maharshi Cave", "historical", "0", 30,
             "Daylight hours",
             "A small rock shrine near the temple, associated by tradition "
             "with the sage Vyasa."),
        ],
    },
    {
        "name": "Rameswaram",
        "state": "Tamil Nadu",
        "description": "An island temple town at the tip of the Pamban, both "
                       "a Char Dham site and a Jyotirlinga.",
        "cost": "1700",
        "days": 2,
        "places": [
            ("Ramanathaswamy Temple", "temple", "0", 180,
             "Usually 5 AM - 1 PM and 3 PM - 9 PM",
             "Its third corridor is the longest in any Indian temple at some "
             "1,200 metres. Twenty-two wells inside are bathed in in order."),
            ("Pamban Bridge", "historical", "0", 45,
             "Open all day",
             "India's first sea bridge, opened 1914, running two kilometres "
             "across the strait to the mainland."),
            ("Dhanushkodi", "beach", "0", 150,
             "Daylight hours only",
             "A town abandoned after the 1964 cyclone, at the sand spit where "
             "the Bay of Bengal meets the Indian Ocean."),
            ("Agnitheertham", "beach", "0", 45,
             "Best at sunrise",
             "The shore directly east of the temple, where pilgrims bathe "
             "before entering."),
        ],
    },
    {
        "name": "Kanchipuram",
        "state": "Tamil Nadu",
        "description": "The city of a thousand temples, and of the silk saris "
                       "woven in its lanes.",
        "cost": "1500",
        "days": 2,
        "places": [
            ("Kamakshi Amman Temple", "temple", "0", 120,
             "Usually 5:30 AM - 12 PM and 4 PM - 8:30 PM",
             "One of the principal Shakti Peethas, and the only temple in "
             "Kanchipuram to Kamakshi."),
            ("Ekambareswarar Temple", "temple", "0", 120,
             "Usually 6 AM - 12:30 PM and 4 PM - 8:30 PM",
             "The earth element among the Pancha Bhoota Sthalams, with a "
             "mango tree in the courtyard said to be very old."),
            ("Kailasanathar Temple", "historical", "0", 90,
             "Usually 6 AM - 6 PM",
             "The oldest structure in the city, built in sandstone by the "
             "Pallavas around 700 CE."),
            ("Kanchipuram Silk Weavers", "shopping", "0", 90,
             "Workshops usually 9 AM - 8 PM",
             "Handloom units where the zari-bordered saris are woven, often "
             "open to visitors."),
        ],
    },
    {
        "name": "Srirangam",
        "state": "Tamil Nadu",
        "description": "An island between two rivers holding the largest "
                       "working temple complex in the world.",
        "cost": "1500",
        "days": 2,
        "places": [
            ("Ranganathaswamy Temple", "temple", "0", 180,
             "Usually 6 AM - 1 PM and 3 PM - 9 PM",
             "156 acres inside 21 gopurams. The Rajagopuram at 72 metres is "
             "the tallest temple tower in Asia."),
            ("Jambukeswarar Temple", "temple", "0", 90,
             "Usually 6 AM - 1 PM and 4 PM - 9:30 PM",
             "The water element among the Pancha Bhoota Sthalams; a spring "
             "keeps the sanctum permanently wet."),
            ("Rockfort Temple", "temple", "10", 90,
             "Usually 6 AM - 8 PM",
             "437 steps cut through a rock 83 metres above Tiruchirappalli, "
             "to a Ganesha shrine at the top."),
        ],
    },
    {
        "name": "Guruvayur",
        "state": "Kerala",
        "description": "The Krishna temple Keralites call Bhuloka Vaikunta, "
                       "and the elephant sanctuary beside it.",
        "cost": "1600",
        "days": 1,
        "places": [
            ("Guruvayur Sri Krishna Temple", "temple", "0", 150,
             "Usually 3 AM - 1 PM and 4:30 PM - 9:30 PM",
             "Non-Hindus are not admitted, and a dress code applies. Among "
             "the most sought-after wedding venues in Kerala."),
            ("Punnathur Kotta Elephant Sanctuary", "wildlife", "50", 90,
             "Usually 8 AM - 6 PM",
             "The temple's elephants are kept in the grounds of a former "
             "palace three kilometres away."),
            ("Mammiyoor Temple", "temple", "0", 45,
             "Usually 5 AM - 8 PM",
             "A Shiva temple a short walk from the main shrine; custom is to "
             "visit both on the same day."),
        ],
    },
    {
        "name": "Shirdi",
        "state": "Maharashtra",
        "description": "The town Sai Baba lived in, and the samadhi mandir "
                       "built over his resting place.",
        "cost": "1600",
        "days": 1,
        "places": [
            ("Sai Baba Samadhi Mandir", "temple", "0", 150,
             "Open 4 AM - 11:30 PM",
             "Built over the samadhi in white marble. Darshan queues run long "
             "on Thursdays and through Ram Navami."),
            ("Dwarkamai", "historical", "0", 45,
             "Open with the main temple",
             "The mosque Sai Baba lived in for six decades; the fire he lit "
             "is still kept burning."),
            ("Chavadi", "historical", "0", 30,
             "Open with the main temple",
             "Where he slept on alternate nights, and where the Thursday "
             "palanquin procession ends."),
        ],
    },
    {
        "name": "Trimbakeshwar",
        "state": "Maharashtra",
        "description": "A Jyotirlinga at the source of the Godavari, in the "
                       "hills above Nashik.",
        "cost": "1500",
        "days": 1,
        "places": [
            ("Trimbakeshwar Temple", "temple", "0", 120,
             "Usually 5:30 AM - 9 PM",
             "Its lingam has three faces for Brahma, Vishnu and Shiva, which "
             "no other Jyotirlinga does."),
            ("Kushavarta Kund", "temple", "0", 45,
             "Daylight hours",
             "The stepped tank held to be the true source of the Godavari, "
             "and the bathing point during Simhastha Kumbh Mela."),
            ("Brahmagiri Hill", "adventure", "0", 180,
             "Daylight hours",
             "About 700 steps to the ridge where the river rises, with the "
             "Western Ghats laid out below."),
        ],
    },
    {
        "name": "Somnath",
        "state": "Gujarat",
        "description": "The first of the twelve Jyotirlingas, on the Arabian "
                       "Sea coast of Saurashtra.",
        "cost": "1700",
        "days": 1,
        "places": [
            ("Somnath Temple", "temple", "0", 120,
             "Usually 6 AM - 9:30 PM; sound and light show after dark",
             "Destroyed and rebuilt repeatedly over a thousand years; the "
             "present temple was completed in 1951."),
            ("Bhalka Tirth", "temple", "0", 45,
             "Usually 7 AM - 7 PM",
             "Where tradition places the death of Krishna, five kilometres "
             "along the coast."),
            ("Triveni Sangam Somnath", "nature", "0", 45,
             "Daylight hours",
             "Where the Hiran, Kapila and Saraswati are said to meet the sea."),
        ],
    },
    {
        "name": "Dwarka",
        "state": "Gujarat",
        "description": "One of the four Char Dham, on the westernmost point "
                       "of the Gujarat coast.",
        "cost": "1800",
        "days": 2,
        "places": [
            ("Dwarkadhish Temple", "temple", "0", 120,
             "Usually 6:30 AM - 1 PM and 5 PM - 9:30 PM",
             "A five-storey shrine on 72 pillars. The flag above it is "
             "changed five times a day."),
            ("Bet Dwarka", "beach", "0", 180,
             "Ferries in daylight hours",
             "An island reached by boat, held to be where Krishna lived; the "
             "crossing takes about 20 minutes."),
            ("Nageshwar Jyotirlinga", "temple", "0", 90,
             "Usually 6 AM - 9 PM",
             "One of the twelve Jyotirlingas, under a 25-metre statue of "
             "Shiva on the road to Bet Dwarka."),
            ("Rukmini Devi Temple", "historical", "0", 45,
             "Usually 6 AM - 8 PM",
             "A 12th century temple two kilometres out of town, carved on "
             "every outer face."),
        ],
    },
    {
        "name": "Ayodhya",
        "state": "Uttar Pradesh",
        "description": "A Sarayu-river city, the birthplace of Rama in the "
                       "Ramayana and one of the seven Sapta Puri.",
        "cost": "1600",
        "days": 2,
        "places": [
            ("Ram Janmabhoomi Temple", "temple", "0", 150,
             "Usually 7 AM - 11:30 AM and 2 PM - 7 PM",
             "The sandstone temple consecrated in January 2024, built in the "
             "Nagara style without structural steel."),
            ("Hanuman Garhi", "temple", "0", 90,
             "Usually 5 AM - 10 PM",
             "76 steps to a fortified hilltop shrine; custom is to come here "
             "before the Janmabhoomi."),
            ("Ram Ki Paidi", "nature", "0", 60,
             "Open all day; lit after dark",
             "A long run of bathing ghats on the Sarayu, where the Deepotsav "
             "lamps are floated at Diwali."),
        ],
    },
    {
        "name": "Ujjain",
        "state": "Madhya Pradesh",
        "description": "A Shipra-river city holding the Mahakaleshwar "
                       "Jyotirlinga, and one of the four Kumbh Mela sites.",
        "cost": "1500",
        "days": 2,
        "places": [
            ("Mahakaleshwar Jyotirlinga", "temple", "0", 150,
             "Usually 4 AM - 11 PM; Bhasma Aarti at dawn",
             "The only Jyotirlinga facing south, and the only one where the "
             "dawn aarti uses sacred ash. That slot books out well ahead."),
            ("Ram Ghat", "nature", "0", 45,
             "Open all day",
             "The main bathing ghat on the Shipra and the centre of the "
             "Simhastha Kumbh Mela."),
            ("Kal Bhairav Temple", "temple", "0", 60,
             "Usually 6 AM - 8 PM",
             "The offering here is liquor, poured to the deity - a practice "
             "particular to this shrine."),
            ("Vedh Shala Observatory", "museum", "25", 60,
             "Usually 9 AM - 6 PM",
             "Jantar Mantar of 1725, still used to compute the panchang."),
        ],
    },
    {
        "name": "Puri",
        "state": "Odisha",
        "description": "One of the four Char Dham, on the Bay of Bengal, "
                       "where the Rath Yatra draws a million people.",
        "cost": "1700",
        "days": 2,
        "places": [
            ("Jagannath Temple", "temple", "0", 150,
             "Usually 5 AM - 11 PM",
             "Open only to Hindus. The kitchen is among the largest anywhere, "
             "cooking for thousands each day in earthen pots."),
            ("Puri Beach", "beach", "0", 90,
             "Open all day; best at sunrise",
             "A wide shore beside the town, and the site of the annual sand "
             "art festival."),
            ("Konark Sun Temple", "historical", "40", 150,
             "Usually 6 AM - 8 PM",
             "A 13th century temple built as the sun god's chariot, its "
             "24 stone wheels working as sundials. 35 km up the coast."),
            ("Chilika Lake", "wildlife", "300", 240,
             "Boats in daylight hours",
             "Asia's largest brackish lagoon, with Irrawaddy dolphins and, "
             "in winter, very large numbers of migratory birds."),
        ],
    },
    {
        "name": "Bodh Gaya",
        "state": "Bihar",
        "description": "Where the Buddha attained enlightenment under the "
                       "Bodhi tree, and the holiest site in Buddhism.",
        "cost": "1500",
        "days": 2,
        "places": [
            ("Mahabodhi Temple", "temple", "0", 150,
             "Usually 5 AM - 9 PM",
             "A UNESCO World Heritage Site. The Bodhi tree beside it is grown "
             "from a cutting of the original."),
            ("Great Buddha Statue", "historical", "20", 45,
             "Usually 7 AM - 12 PM and 2 PM - 6 PM",
             "A 25-metre sandstone and granite figure finished in 1989, "
             "sitting on a lotus."),
            ("Thai Monastery", "temple", "0", 45,
             "Usually 6 AM - 6 PM",
             "One of many national monasteries in the town, each built in "
             "its own country's style."),
            ("Sujata Stupa", "historical", "0", 60,
             "Daylight hours",
             "Across the Falgu, marking where the Buddha is said to have "
             "been offered milk rice after abandoning fasting."),
        ],
    },
    {
        "name": "Haridwar",
        "state": "Uttarakhand",
        "description": "Where the Ganges reaches the plain, and one of the "
                       "four cities of the Kumbh Mela.",
        "cost": "1500",
        "days": 2,
        "places": [
            ("Har Ki Pauri", "temple", "0", 90,
             "Open all day; Ganga Aarti about 6:30 PM",
             "The ghat held to carry Vishnu's footprint. Lamps are set on the "
             "water at the evening aarti."),
            ("Mansa Devi Temple", "temple", "0", 120,
             "Usually 8 AM - 6:30 PM",
             "On Bilwa Parvat, reached by cable car or a steep walk; one of "
             "the Siddh Peethas."),
            ("Chandi Devi Temple", "temple", "0", 120,
             "Usually 6 AM - 8 PM",
             "On Neel Parvat across the river, a three-kilometre climb or a "
             "ropeway from Gauri Shankar."),
        ],
    },
    {
        "name": "Kedarnath",
        "state": "Uttarakhand",
        "description": "The highest of the twelve Jyotirlingas, at 3,583 "
                       "metres, open only for part of the year.",
        "cost": "2600",
        "days": 3,
        "places": [
            ("Kedarnath Temple", "temple", "0", 180,
             "Open roughly late April to early November only",
             "Stone-built and undated, it survived the 2013 floods when much "
             "around it did not. Registration is compulsory."),
            ("Kedarnath Trek", "adventure", "0", 480,
             "Daylight hours in season",
             "16 km on foot from Gaurikund, or by pony, palanquin or "
             "helicopter. Altitude is the real difficulty, not distance."),
            ("Bhairavnath Temple", "temple", "0", 60,
             "In season, daylight hours",
             "A short climb above the main shrine; the guardian said to watch "
             "the valley while the temple is closed for winter."),
        ],
    },
    {
        "name": "Badrinath",
        "state": "Uttarakhand",
        "description": "A Char Dham site on the Alaknanda between the Nar and "
                       "Narayana peaks, open in season only.",
        "cost": "2600",
        "days": 3,
        "places": [
            ("Badrinath Temple", "temple", "0", 150,
             "Open roughly late April to November",
             "A brightly painted facade below Neelkanth peak, holding a black "
             "stone Vishnu found in the Alaknanda."),
            ("Tapt Kund", "nature", "0", 45,
             "In season, daylight hours",
             "Hot sulphur springs below the temple, where pilgrims bathe "
             "before darshan even in near-freezing air."),
            ("Mana Village", "nature", "0", 120,
             "In season, daylight hours",
             "The last village before the Tibet border, three kilometres on, "
             "with the Saraswati emerging from under a rock bridge."),
        ],
    },
    {
        "name": "Vaishno Devi",
        "state": "Jammu and Kashmir",
        "description": "A cave shrine in the Trikuta hills reached by a "
                       "thirteen-kilometre walk from Katra.",
        "cost": "1900",
        "days": 2,
        "places": [
            ("Vaishno Devi Bhawan", "temple", "0", 180,
             "Open 24 hours; a yatra slip is required",
             "The cave holds three natural rock formations rather than "
             "sculpted idols. Among the busiest shrines in India."),
            ("Ardhkuwari", "temple", "0", 60,
             "Open with the yatra route",
             "Roughly halfway up, at the narrow cave where the goddess is "
             "said to have sheltered for nine months."),
            ("Bhairavnath Temple Katra", "temple", "0", 120,
             "Daylight hours",
             "Two and a half kilometres above the Bhawan; the yatra is held "
             "incomplete without it."),
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
    # North
    ("Delhi", "Agra", 230),
    ("Delhi", "Varanasi", 820),
    ("Delhi", "Amritsar", 450),
    ("Delhi", "Rishikesh", 240),
    ("Delhi", "Shimla", 350),
    ("Delhi", "Manali", 540),
    ("Delhi", "Mumbai", 1420),
    ("Shimla", "Manali", 250),
    ("Rishikesh", "Shimla", 240),
    ("Agra", "Jaipur", 240),
    ("Agra", "Varanasi", 600),
    ("Amritsar", "Shimla", 350),
    # Rajasthan
    ("Jaipur", "Udaipur", 400),
    ("Jaipur", "Jodhpur", 340),
    ("Udaipur", "Jodhpur", 250),
    ("Udaipur", "Mumbai", 750),
    ("Jodhpur", "Jaisalmer", 285),
    # West and Deccan
    ("Mumbai", "Bengaluru", 980),
    ("Pune", "Hyderabad", 560),
    ("Goa", "Bengaluru", 560),
    ("Hyderabad", "Hampi", 380),
    # South
    ("Bengaluru", "Mysuru", 145),
    ("Bengaluru", "Hampi", 340),
    ("Bengaluru", "Kochi", 550),
    ("Chennai", "Madurai", 460),
    ("Chennai", "Puducherry", 160),
    ("Chennai", "Visakhapatnam", 800),
    ("Madurai", "Kochi", 320),
    ("Madurai", "Puducherry", 330),
    ("Kochi", "Alleppey", 55),
    ("Alleppey", "Munnar", 170),
    ("Mysuru", "Kochi", 480),
]


# Themes answer "who is this trip for", which is a different question from
# TouristPlace.category ("what is this building"). display_order puts the broad
# ones first so the explorer's chips do not open alphabetically on Adventure.
THEMES = [
    ("family", "Family", 10),
    ("temple", "Temples & Spiritual", 20),
    ("beach", "Beaches", 30),
    ("mountain", "Mountains", 40),
    ("nature", "Nature", 50),
    ("adventure", "Adventure", 60),
    ("wildlife", "Wildlife", 70),
    ("historical", "Historical", 80),
    ("honeymoon", "Honeymoon", 90),
    ("weekend", "Weekend Trips", 100),
    ("budget", "Budget Trips", 110),
]

# destination -> (themes, best time to go)
#
# Best times are the broad season a visitor plans around, not a forecast.
# Hill stations invert the usual pattern - Manali and Shimla are the summer
# escape - which is exactly why this cannot be derived from latitude.
DESTINATION_THEMES = {
    "Mumbai":        (["family", "beach", "historical", "weekend"], "October to February"),
    "Goa":           (["beach", "family", "honeymoon", "weekend"], "November to February"),
    "Hyderabad":     (["family", "historical", "temple", "weekend", "budget"], "October to March"),
    "Jaipur":        (["family", "historical", "honeymoon"], "October to March"),
    "Munnar":        (["nature", "honeymoon", "mountain", "wildlife"], "September to May"),
    "Visakhapatnam": (["beach", "family", "temple", "budget"], "October to March"),
    "Delhi":         (["family", "historical", "temple"], "October to March"),
    "Agra":          (["historical", "family", "weekend"], "October to March"),
    "Varanasi":      (["temple", "historical", "budget"], "October to March"),
    "Amritsar":      (["temple", "family", "historical", "weekend"], "October to March"),
    "Rishikesh":     (["adventure", "temple", "nature", "budget"], "September to April"),
    "Shimla":        (["mountain", "family", "honeymoon", "nature"], "March to June, December for snow"),
    "Manali":        (["mountain", "adventure", "honeymoon", "nature"], "March to June, December for snow"),
    "Udaipur":       (["honeymoon", "historical", "family"], "September to March"),
    "Jodhpur":       (["historical", "family", "budget"], "October to March"),
    "Bengaluru":     (["family", "nature", "weekend"], "October to February"),
    "Chennai":       (["beach", "temple", "historical", "family"], "November to February"),
    "Mysuru":        (["family", "historical", "temple", "weekend", "budget"], "October to March"),
    "Madurai":       (["temple", "historical", "budget"], "October to March"),
    "Kochi":         (["family", "historical", "beach", "honeymoon"], "October to March"),
    "Alleppey":      (["honeymoon", "nature", "family"], "November to February"),
    "Hampi":         (["historical", "adventure", "budget"], "October to February"),
    "Puducherry":    (["beach", "honeymoon", "weekend", "family"], "October to March"),
}

# Illustrative only - see the field's help_text. Spread rather than uniform, so
# the sort has something to do, but never presented as a visitor review score.
SAMPLE_RATINGS = {
    "Goa": "4.6", "Jaipur": "4.5", "Udaipur": "4.7", "Munnar": "4.5",
    "Manali": "4.4", "Alleppey": "4.6", "Hampi": "4.5", "Agra": "4.6",
    "Amritsar": "4.7", "Varanasi": "4.4", "Mysuru": "4.5", "Kochi": "4.4",
    "Shimla": "4.2", "Rishikesh": "4.4", "Madurai": "4.3", "Chennai": "4.1",
    "Mumbai": "4.3", "Delhi": "4.2", "Bengaluru": "4.1", "Hyderabad": "4.3",
    "Jodhpur": "4.4", "Puducherry": "4.4", "Visakhapatnam": "4.2",
}


# Pilgrimage circuits. A separate row of chips from the trip themes because
# they answer a narrower question, but the same table and the same relation -
# Theme.kind is what keeps them apart.
PILGRIMAGE_THEMES = [
    ("jyotirlinga", "Jyotirlinga", 210),
    ("char-dham", "Char Dham", 220),
    ("shakti-peetha", "Shakti Peetha", 230),
    ("family-pilgrimage", "Family Pilgrimage", 240),
    ("weekend-pilgrimage", "Weekend Pilgrimage", 250),
]

# Circuit membership is a factual claim, so only the well-established ones are
# recorded. Srisailam is deliberately in two: Mallikarjuna is counted among
# both the twelve Jyotirlingas and the eighteen Maha Shakti Peethas, which few
# sites are. "Family pilgrimage" means reachable and manageable with children -
# which is why Kedarnath and Badrinath are not in it despite being Char Dham.
DESTINATION_CIRCUITS = {
    "Srisailam":       ["jyotirlinga", "shakti-peetha", "weekend-pilgrimage"],
    "Varanasi":        ["jyotirlinga"],
    "Trimbakeshwar":   ["jyotirlinga", "weekend-pilgrimage"],
    "Somnath":         ["jyotirlinga", "family-pilgrimage"],
    "Ujjain":          ["jyotirlinga", "family-pilgrimage"],
    "Dwarka":          ["jyotirlinga", "char-dham", "family-pilgrimage"],
    "Rameswaram":      ["jyotirlinga", "char-dham", "family-pilgrimage"],
    "Puri":            ["char-dham", "family-pilgrimage"],
    "Badrinath":       ["char-dham"],
    "Kedarnath":       ["jyotirlinga"],
    "Kanchipuram":     ["shakti-peetha", "family-pilgrimage", "weekend-pilgrimage"],
    "Vaishno Devi":    ["shakti-peetha"],
    "Vijayawada":      ["shakti-peetha", "weekend-pilgrimage", "family-pilgrimage"],
    "Tirupati":        ["family-pilgrimage"],
    "Srikalahasti":    ["weekend-pilgrimage"],
    "Annavaram":       ["weekend-pilgrimage", "family-pilgrimage"],
    "Yadadri":         ["weekend-pilgrimage", "family-pilgrimage"],
    "Basara":          ["weekend-pilgrimage", "family-pilgrimage"],
    "Bhadrachalam":    ["weekend-pilgrimage", "family-pilgrimage"],
    "Srirangam":       ["family-pilgrimage"],
    "Guruvayur":       ["family-pilgrimage", "weekend-pilgrimage"],
    "Shirdi":          ["family-pilgrimage", "weekend-pilgrimage"],
    "Haridwar":        ["family-pilgrimage"],
    "Ayodhya":         ["family-pilgrimage"],
    "Madurai":         ["family-pilgrimage"],
    "Amritsar":        ["family-pilgrimage"],
}

# Trip themes and best season for the pilgrimage towns.
TEMPLE_THEMES = {
    "Tirupati":      (["temple", "family", "budget"], "September to February"),
    "Srisailam":     (["temple", "nature", "wildlife", "weekend"], "October to March"),
    "Vijayawada":    (["temple", "family", "budget", "weekend"], "October to March"),
    "Srikalahasti":  (["temple", "weekend", "budget"], "September to March"),
    "Annavaram":     (["temple", "family", "weekend", "budget"], "October to March"),
    "Yadadri":       (["temple", "family", "weekend", "budget"], "October to March"),
    "Bhadrachalam":  (["temple", "family", "budget"], "October to March"),
    "Basara":        (["temple", "family", "weekend", "budget"], "October to March"),
    "Rameswaram":    (["temple", "beach", "family"], "October to April"),
    "Kanchipuram":   (["temple", "historical", "family", "weekend"], "October to March"),
    "Srirangam":     (["temple", "historical", "family"], "October to March"),
    "Guruvayur":     (["temple", "family", "wildlife"], "September to March"),
    "Shirdi":        (["temple", "family", "weekend"], "July to March"),
    "Trimbakeshwar": (["temple", "mountain", "weekend"], "August to February"),
    "Somnath":       (["temple", "beach", "family"], "October to March"),
    "Dwarka":        (["temple", "beach", "family"], "October to March"),
    "Ayodhya":       (["temple", "family", "historical"], "October to March"),
    "Ujjain":        (["temple", "historical", "family", "budget"], "October to March"),
    "Puri":          (["temple", "beach", "family", "wildlife"], "October to February"),
    "Bodh Gaya":     (["temple", "historical", "budget"], "October to March"),
    "Haridwar":      (["temple", "family", "nature"], "September to April"),
    "Kedarnath":     (["temple", "mountain", "adventure"], "May to June, September to October"),
    "Badrinath":     (["temple", "mountain", "nature"], "May to June, September to October"),
    "Vaishno Devi":  (["temple", "mountain", "adventure", "family"], "March to October"),
}

TEMPLE_RATINGS = {
    "Tirupati": "4.7", "Srisailam": "4.5", "Vijayawada": "4.3",
    "Srikalahasti": "4.4", "Annavaram": "4.4", "Yadadri": "4.5",
    "Bhadrachalam": "4.4", "Basara": "4.3", "Rameswaram": "4.6",
    "Kanchipuram": "4.5", "Srirangam": "4.7", "Guruvayur": "4.6",
    "Shirdi": "4.6", "Trimbakeshwar": "4.5", "Somnath": "4.7",
    "Dwarka": "4.6", "Ayodhya": "4.6", "Ujjain": "4.6", "Puri": "4.6",
    "Bodh Gaya": "4.5", "Haridwar": "4.5", "Kedarnath": "4.8",
    "Badrinath": "4.7", "Vaishno Devi": "4.7",
}


DESTINATION_THEMES.update(TEMPLE_THEMES)
SAMPLE_RATINGS.update(TEMPLE_RATINGS)


# Photographs for the destination cards and the place pickers.
#
# These are Wikimedia Commons files that now live inside the project, in
# static/images/. They used to be hot-linked from upload.wikimedia.org, which
# meant every page view begged a picture off someone else's servers: pages
# were slow, images broke without internet, and a file renamed on Commons
# turned a card blank.
#
# static/ rather than media/ on purpose: Render's free plan and Vercel both
# have an ephemeral filesystem, so anything written into media/ disappears on
# the next deploy, while static/ is committed and shipped with the code.
# WhiteNoise serves it in production.
#
# To refresh them, or after adding a new place here:
#
#     python manage.py localize_images
#
# That downloads anything still written as a web address, resizes it, records
# the photographer in static/images/CREDITS.md, and rewrites the lines below.
# Both models still prefer an uploaded file when one exists, so uploading
# through the admin overrides these.
IMAGES = {
    # --- destinations ---
    "Mumbai":                              "/static/images/destinations/mumbai.jpg",
    "Goa":                                 "/static/images/destinations/goa.jpg",
    "Hyderabad":                           "/static/images/destinations/hyderabad.jpg",
    "Jaipur":                              "/static/images/destinations/jaipur.jpg",
    "Munnar":                              "/static/images/destinations/munnar.jpg",
    "Visakhapatnam":                       "/static/images/destinations/visakhapatnam.jpg",
    # --- tourist places ---
    "Gateway of India":                    "/static/images/places/gateway-of-india.jpg",
    "Marine Drive":                        "/static/images/places/marine-drive.jpg",
    "Juhu Beach":                          "/static/images/places/juhu-beach.jpg",
    "Colaba Causeway":                     "/static/images/places/colaba-causeway.jpg",
    "Siddhivinayak Temple":                "/static/images/places/siddhivinayak-temple.jpg",
    "Elephanta Caves":                     "/static/images/places/elephanta-caves.jpg",
    "Chhatrapati Shivaji Maharaj Museum":  "/static/images/places/chhatrapati-shivaji-maharaj-museum.jpg",
    "Baga Beach":                          "/static/images/places/baga-beach.jpg",
    "Basilica of Bom Jesus":               "/static/images/places/basilica-of-bom-jesus.jpg",
    "Dudhsagar Falls":                     "/static/images/places/dudhsagar-falls.jpg",
    "Anjuna Flea Market":                  "/static/images/places/anjuna-flea-market.jpg",
    "Charminar":                           "/static/images/places/charminar.jpg",
    "Golconda Fort":                       "/static/images/places/golconda-fort.jpg",
    "Ramoji Film City":                    "/static/images/places/ramoji-film-city.jpg",
    "Laad Bazaar":                         "/static/images/places/laad-bazaar.jpg",
    "Birla Mandir":                        "/static/images/places/birla-mandir.jpg",
    "Amber Fort":                          "/static/images/places/amber-fort.jpg",
    "Hawa Mahal":                          "/static/images/destinations/jaipur.jpg",
    "City Palace":                         "/static/images/places/city-palace.jpg",
    "Johari Bazaar":                       "/static/images/places/johari-bazaar.jpg",
    "Tea Museum":                          "/static/images/places/tea-museum.jpg",
    "Eravikulam National Park":            "/static/images/places/eravikulam-national-park.jpg",
    "Attukad Waterfalls":                  "/static/images/places/attukad-waterfalls.jpg",
    "RK Beach":                            "/static/images/places/rk-beach.jpg",
    "Kailasagiri":                         "/static/images/places/kailasagiri.jpg",
    "Borra Caves":                         "/static/images/places/borra-caves.jpg",
    "Simhachalam Temple":                  "/static/images/places/simhachalam-temple.jpg",
    "Delhi":                       "/static/images/destinations/delhi.jpg",
    "Agra":                        "/static/images/destinations/agra.jpg",
    "Varanasi":                    "/static/images/destinations/varanasi.jpg",
    "Amritsar":                    "/static/images/destinations/amritsar.jpg",
    "Rishikesh":                   "/static/images/destinations/rishikesh.jpg",
    "Shimla":                      "/static/images/destinations/shimla.jpg",
    "Manali":                      "/static/images/destinations/manali.jpg",
    "Udaipur":                     "/static/images/destinations/udaipur.jpg",
    "Jodhpur":                     "/static/images/destinations/jodhpur.jpg",
    "Bengaluru":                   "/static/images/destinations/bengaluru.jpg",
    "Chennai":                     "/static/images/destinations/chennai.jpg",
    "Mysuru":                      "/static/images/destinations/mysuru.jpg",
    "Madurai":                     "/static/images/destinations/madurai.jpg",
    "Kochi":                       "/static/images/destinations/kochi.jpg",
    "Alleppey":                    "/static/images/destinations/alleppey.jpg",
    "Hampi":                       "/static/images/destinations/hampi.jpg",
    "Red Fort":                    "/static/images/places/red-fort.jpg",
    "Qutub Minar":                 "/static/images/places/qutub-minar.jpg",
    "Humayun's Tomb":              "/static/images/places/humayuns-tomb.jpg",
    "Lotus Temple":                "/static/images/places/lotus-temple.jpg",
    "Chandni Chowk":               "/static/images/places/chandni-chowk.jpg",
    "India Gate":                  "/static/images/places/india-gate.jpg",
    "Taj Mahal":                   "/static/images/places/taj-mahal.jpg",
    "Agra Fort":                   "/static/images/places/agra-fort.jpg",
    "Fatehpur Sikri":              "/static/images/places/fatehpur-sikri.jpg",
    "Mehtab Bagh":                 "/static/images/places/mehtab-bagh.jpg",
    "Itmad-ud-Daulah":             "/static/images/places/itmad-ud-daulah.jpg",
    "Dashashwamedh Ghat":          "/static/images/places/dashashwamedh-ghat.jpg",
    "Kashi Vishwanath Temple":     "/static/images/places/kashi-vishwanath-temple.jpg",
    "Sarnath":                     "/static/images/places/sarnath.jpg",
    "Assi Ghat":                   "/static/images/places/assi-ghat.jpg",
    "Golden Temple":               "/static/images/places/golden-temple.jpg",
    "Jallianwala Bagh":            "/static/images/places/jallianwala-bagh.jpg",
    "Wagah Border Ceremony":       "/static/images/places/wagah-border-ceremony.jpg",
    "Partition Museum":            "/static/images/places/partition-museum.jpg",
    "Laxman Jhula":                "/static/images/places/laxman-jhula.jpg",
    "Neelkanth Mahadev Temple":    "/static/images/places/neelkanth-mahadev-temple.jpg",
    "The Ridge":                   "/static/images/places/the-ridge.jpg",
    "Jakhoo Temple":               "/static/images/places/jakhoo-temple.jpg",
    "Kalka-Shimla Toy Train":      "/static/images/places/kalka-shimla-toy-train.jpg",
    "Mall Road":                   "/static/images/places/mall-road.jpg",
    "Viceregal Lodge":             "/static/images/places/viceregal-lodge.jpg",
    "Hadimba Temple":              "/static/images/places/hadimba-temple.jpg",
    "Solang Valley":               "/static/images/places/solang-valley.jpg",
    "Rohtang Pass":                "/static/images/places/rohtang-pass.jpg",
    "Vashisht Hot Springs":        "/static/images/places/vashisht-hot-springs.jpg",
    "City Palace":                 "/static/images/places/city-palace.jpg",
    "Lake Pichola Boat Ride":      "/static/images/places/lake-pichola-boat-ride.jpg",
    "Jagdish Temple":              "/static/images/places/jagdish-temple.jpg",
    "Saheliyon ki Bari":           "/static/images/places/saheliyon-ki-bari.jpg",
    "Bagore ki Haveli":            "/static/images/places/bagore-ki-haveli.jpg",
    "Mehrangarh Fort":             "/static/images/destinations/jodhpur.jpg",
    "Jaswant Thada":               "/static/images/places/jaswant-thada.jpg",
    "Umaid Bhawan Palace":         "/static/images/places/umaid-bhawan-palace.jpg",
    "Mandore Gardens":             "/static/images/places/mandore-gardens.jpg",
    "Bangalore Palace":            "/static/images/places/bangalore-palace.jpg",
    "Cubbon Park":                 "/static/images/places/cubbon-park.jpg",
    "ISKCON Temple Bengaluru":     "/static/images/places/iskcon-temple-bengaluru.jpg",
    "Commercial Street":           "/static/images/places/commercial-street.jpg",
    "Marina Beach":                "/static/images/places/marina-beach.jpg",
    "Kapaleeshwarar Temple":       "/static/images/places/kapaleeshwarar-temple.jpg",
    "Fort St. George":             "/static/images/places/fort-st-george.jpg",
    "Government Museum Chennai":   "/static/images/places/government-museum-chennai.jpg",
    "Mahabalipuram":               "/static/images/places/mahabalipuram.jpg",
    "Mysore Palace":               "/static/images/places/mysore-palace.jpg",
    "Chamundi Hill":               "/static/images/places/chamundi-hill.jpg",
    "Brindavan Gardens":           "/static/images/places/brindavan-gardens.jpg",
    "Devaraja Market":             "/static/images/places/devaraja-market.jpg",
    "St. Philomena Church":        "/static/images/places/st-philomena-church.jpg",
    "Meenakshi Amman Temple":      "/static/images/places/meenakshi-amman-temple.jpg",
    "Thirumalai Nayakkar Palace":  "/static/images/places/thirumalai-nayakkar-palace.jpg",
    "Gandhi Memorial Museum":      "/static/images/places/gandhi-memorial-museum.jpg",
    "Alagar Kovil":                "/static/images/places/alagar-kovil.jpg",
    "Chinese Fishing Nets":        "/static/images/places/chinese-fishing-nets.jpg",
    "Mattancherry Palace":         "/static/images/places/mattancherry-palace.jpg",
    "Paradesi Synagogue":          "/static/images/places/paradesi-synagogue.jpg",
    "Fort Kochi Beach":            "/static/images/places/fort-kochi-beach.jpg",
    "Kathakali Performance":       "/static/images/places/kathakali-performance.jpg",
    "Backwater Houseboat":         "/static/images/places/backwater-houseboat.jpg",
    "Alappuzha Beach":             "/static/images/places/alappuzha-beach.jpg",
    "Marari Beach":                "/static/images/places/marari-beach.jpg",
    "Pathiramanal Island":         "/static/images/places/pathiramanal-island.jpg",
    "Krishnapuram Palace":         "/static/images/places/krishnapuram-palace.jpg",
    "Virupaksha Temple":           "/static/images/places/virupaksha-temple.jpg",
    "Hampi Bazaar":                "/static/images/destinations/hampi.jpg",
    "Matanga Hill":                "/static/images/places/matanga-hill.jpg",
    "Lotus Mahal":                 "/static/images/places/lotus-mahal.jpg",
    "Promenade Beach":             "/static/images/places/promenade-beach.jpg",
    "Sri Aurobindo Ashram":        "/static/images/places/sri-aurobindo-ashram.jpg",
    "Auroville":                   "/static/images/places/auroville.jpg",
    "Puducherry":                          "/static/images/places/promenade-beach.jpg",
    "Triveni Ghat":                        "/static/images/places/triveni-ghat.jpg",
    "Lalbagh Botanical Garden":            "/static/images/places/lalbagh-botanical-garden.jpg",
    "Hall Bazaar":                           "/static/images/places/hall-bazaar.jpg",
    "Ganga Rafting":                         "/static/images/places/ganga-rafting.jpg",
    "Clock Tower Market":                    "/static/images/places/clock-tower-market.jpg",
    "Vittala Temple":                        "/static/images/places/vittala-temple.jpg",
    "Paradise Beach":                        "/static/images/places/paradise-beach.jpg",
    "Banaras Silk Weavers Market":           "/static/images/places/banaras-silk-weavers-market.jpg",
    "Beatles Ashram":                        "/static/images/places/beatles-ashram.jpg",
    "French Quarter":                        "/static/images/places/french-quarter.jpg",
    "Tirupati":                          "/static/images/destinations/tirupati.jpg",
    "Tirumala Venkateswara Temple":      "/static/images/destinations/tirupati.jpg",
    "Sri Padmavathi Temple":             "/static/images/places/sri-padmavathi-temple.jpg",
    "Srisailam":                         "/static/images/destinations/srisailam.jpg",
    "Mallikarjuna Jyotirlinga Temple":   "/static/images/places/mallikarjuna-jyotirlinga-temple.jpg",
    "Srisailam Dam":                     "/static/images/places/srisailam-dam.jpg",
    "Vijayawada":                        "/static/images/destinations/vijayawada.jpg",
    "Kanaka Durga Temple":               "/static/images/places/kanaka-durga-temple.jpg",
    "Undavalli Caves":                   "/static/images/places/undavalli-caves.jpg",
    "Prakasam Barrage":                  "/static/images/places/prakasam-barrage.jpg",
    "Bhavani Island":                    "/static/images/places/bhavani-island.jpg",
    "Srikalahasti":                      "/static/images/destinations/srikalahasti.jpg",
    "Srikalahasteeswara Temple":         "/static/images/places/srikalahasteeswara-temple.jpg",
    "Yadadri Lakshmi Narasimha Temple":  "/static/images/places/yadadri-lakshmi-narasimha-temple.jpg",
    "Bhadrachalam":                      "/static/images/destinations/bhadrachalam.jpg",
    "Sri Sita Ramachandraswamy Temple":  "/static/images/destinations/bhadrachalam.jpg",
    "Parnasala":                         "/static/images/places/parnasala.jpg",
    "Godavari Ghat":                     "/static/images/places/godavari-ghat.jpg",
    "Basara":                            "/static/images/destinations/basara.jpg",
    "Gnana Saraswati Temple":            "/static/images/destinations/basara.jpg",
    "Rameswaram":                        "/static/images/destinations/rameswaram.jpg",
    "Ramanathaswamy Temple":             "/static/images/places/ramanathaswamy-temple.jpg",
    "Pamban Bridge":                     "/static/images/places/pamban-bridge.jpg",
    "Dhanushkodi":                       "/static/images/places/dhanushkodi.jpg",
    "Agnitheertham":                     "/static/images/destinations/rameswaram.jpg",
    "Kanchipuram":                       "/static/images/destinations/kanchipuram.jpg",
    "Kamakshi Amman Temple":             "/static/images/places/kamakshi-amman-temple.jpg",
    "Kailasanathar Temple":              "/static/images/places/kailasanathar-temple.jpg",
    "Srirangam":                         "/static/images/destinations/srirangam.jpg",
    "Ranganathaswamy Temple":            "/static/images/places/ranganathaswamy-temple.jpg",
    "Jambukeswarar Temple":              "/static/images/places/jambukeswarar-temple.jpg",
    "Guruvayur":                           "/static/images/destinations/guruvayur.jpg",
    "Guruvayur Sri Krishna Temple":        "/static/images/places/guruvayur-sri-krishna-temple.jpg",
    "Punnathur Kotta Elephant Sanctuary":  "/static/images/places/punnathur-kotta-elephant-sanctuary.jpg",
    "Mammiyoor Temple":                    "/static/images/places/mammiyoor-temple.jpg",
    "Shirdi":                              "/static/images/destinations/shirdi.jpg",
    "Sai Baba Samadhi Mandir":             "/static/images/destinations/shirdi.jpg",
    "Dwarkamai":                           "/static/images/destinations/shirdi.jpg",
    "Trimbakeshwar":                       "/static/images/destinations/trimbakeshwar.jpg",
    "Trimbakeshwar Temple":                "/static/images/destinations/trimbakeshwar.jpg",
    "Kushavarta Kund":                     "/static/images/destinations/trimbakeshwar.jpg",
    "Somnath":                             "/static/images/destinations/somnath.jpg",
    "Somnath Temple":                      "/static/images/destinations/somnath.jpg",
    "Bhalka Tirth":                        "/static/images/places/bhalka-tirth.jpg",
    "Dwarka":                              "/static/images/destinations/dwarka.jpg",
    "Dwarkadhish Temple":                  "/static/images/destinations/dwarka.jpg",
    "Bet Dwarka":                          "/static/images/places/bet-dwarka.jpg",
    "Nageshwar Jyotirlinga":               "/static/images/places/nageshwar-jyotirlinga.jpg",
    "Ayodhya":                             "/static/images/destinations/ayodhya.jpg",
    "Ram Janmabhoomi Temple":              "/static/images/destinations/ayodhya.jpg",
    "Hanuman Garhi":                       "/static/images/places/hanuman-garhi.jpg",
    "Ram Ki Paidi":                        "/static/images/places/ram-ki-paidi.jpg",
    "Ujjain":                              "/static/images/destinations/ujjain.jpg",
    "Mahakaleshwar Jyotirlinga":           "/static/images/destinations/ujjain.jpg",
    "Ram Ghat":                            "/static/images/destinations/ujjain.jpg",
    "Kal Bhairav Temple":                  "/static/images/places/kal-bhairav-temple.jpg",
    "Vedh Shala Observatory":              "/static/images/places/vedh-shala-observatory.jpg",
    "Jagannath Temple":                    "/static/images/places/jagannath-temple.jpg",
    "Puri Beach":                          "/static/images/places/puri-beach.jpg",
    "Konark Sun Temple":                   "/static/images/places/konark-sun-temple.jpg",
    "Chilika Lake":                        "/static/images/places/chilika-lake.jpg",
    "Bodh Gaya":                           "/static/images/destinations/bodh-gaya.jpg",
    "Mahabodhi Temple":                    "/static/images/places/mahabodhi-temple.jpg",
    "Sujata Stupa":                        "/static/images/places/sujata-stupa.jpg",
    "Haridwar":                            "/static/images/destinations/haridwar.jpg",
    "Har Ki Pauri":                        "/static/images/places/har-ki-pauri.jpg",
    "Mansa Devi Temple":                   "/static/images/places/mansa-devi-temple.jpg",
    "Chandi Devi Temple":                  "/static/images/places/chandi-devi-temple.jpg",
    "Kedarnath":                           "/static/images/destinations/kedarnath.jpg",
    "Kedarnath Temple":                    "/static/images/places/kedarnath-temple.jpg",
    "Badrinath":                           "/static/images/destinations/badrinath.jpg",
    "Badrinath Temple":                    "/static/images/places/badrinath-temple.jpg",
    "Tapt Kund":                           "/static/images/destinations/badrinath.jpg",
    "Mana Village":                        "/static/images/places/mana-village.jpg",
    "Vaishno Devi":                        "/static/images/destinations/vaishno-devi.jpg",
    "Vaishno Devi Bhawan":                 "/static/images/destinations/vaishno-devi.jpg",
    "Ardhkuwari":                          "/static/images/places/ardhkuwari.jpg",
    "Puri":                                  "/static/images/destinations/puri.jpg",
    # The hilltop temple is the town, so its photograph is the destination's.
    "Yadadri":                               "/static/images/places/yadadri-lakshmi-narasimha-temple.jpg",
    "Annavaram":                             "/static/images/destinations/annavaram.jpg",
    "Sri Veera Venkata Satyanarayana Swamy Temple": "/static/images/destinations/annavaram.jpg",
    # --- places that had no photograph until now ---
    "Old Manali":                              "/static/images/places/old-manali.jpg",
    "Puthu Mandapam":                          "/static/images/places/puthu-mandapam.jpg",
    "Sri Kapileswara Swamy Temple":            "/static/images/places/sri-kapileswara-swamy-temple.jpg",
    "Silathoranam":                            "/static/images/places/silathoranam.jpg",
    "Patala Ganga":                            "/static/images/places/patala-ganga.jpg",
    "Kalahasti Fort":                          "/static/images/places/kalahasti-fort.jpg",
    "Bharadwaja Tirtham":                      "/static/images/places/bharadwaja-tirtham.jpg",
    "Pampa River Ghat":                        "/static/images/places/pampa-river-ghat.jpg",
    "Ratnagiri Hill Steps":                    "/static/images/places/ratnagiri-hill-steps.jpg",
    "Yadagirigutta Hill":                      "/static/images/places/yadagirigutta-hill.jpg",
    "Sri Lakshmi Narasimha Pushkarini":        "/static/images/places/sri-lakshmi-narasimha-pushkarini.jpg",
    "Godavari Ghat Basara":                    "/static/images/places/godavari-ghat-basara.jpg",
    "Vyasa Maharshi Cave":                     "/static/images/places/vyasa-maharshi-cave.jpg",
    "Ekambareswarar Temple":                   "/static/images/places/ekambareswarar-temple.jpg",
    "Kanchipuram Silk Weavers":                "/static/images/places/kanchipuram-silk-weavers.jpg",
    "Rockfort Temple":                         "/static/images/places/rockfort-temple.jpg",
    "Chavadi":                                 "/static/images/places/chavadi.jpg",
    "Brahmagiri Hill":                         "/static/images/places/brahmagiri-hill.jpg",
    "Triveni Sangam Somnath":                  "/static/images/places/triveni-sangam-somnath.jpg",
    "Rukmini Devi Temple":                     "/static/images/places/rukmini-devi-temple.jpg",
    "Great Buddha Statue":                     "/static/images/places/great-buddha-statue.jpg",
    "Thai Monastery":                          "/static/images/places/thai-monastery.jpg",
    "Kedarnath Trek":                          "/static/images/places/kedarnath-trek.jpg",
    "Bhairavnath Temple":                      "/static/images/places/bhairavnath-temple.jpg",
    "Bhairavnath Temple Katra":                "/static/images/places/bhairavnath-temple-katra.jpg",
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

        # --- themes ---------------------------------------------------------
        theme_by_slug = {}
        for slug, name, order in THEMES:
            theme, _ = Theme.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "display_order": order,
                    "kind": Theme.KIND_TRIP,
                },
            )
            theme_by_slug[slug] = theme
        for slug, name, order in PILGRIMAGE_THEMES:
            theme, _ = Theme.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "display_order": order,
                    "kind": Theme.KIND_PILGRIMAGE,
                },
            )
            theme_by_slug[slug] = theme
        self.stdout.write(
            self.style.SUCCESS(
                f"Themes: {len(THEMES)} trip, {len(PILGRIMAGE_THEMES)} pilgrimage"
            )
        )

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
                    "best_time": DESTINATION_THEMES.get(item["name"], ((), ""))[1],
                    "sample_rating": Decimal(
                        SAMPLE_RATINGS.get(item["name"], "4.0")
                    ),
                },
            )
            slugs = list(DESTINATION_THEMES.get(item["name"], ((), ""))[0])
            slugs += DESTINATION_CIRCUITS.get(item["name"], [])
            # set() rather than add(): re-running the seeder should leave the
            # themes matching this file, not accumulate whatever was there.
            destination.themes.set(theme_by_slug[s] for s in slugs)
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
