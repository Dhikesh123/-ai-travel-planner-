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
    "Delhi":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Jama_Masjid_2011.jpg/500px-Jama_Masjid_2011.jpg",
    "Agra":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Taj_Mahal%2C_Agra%2C_India.jpg/500px-Taj_Mahal%2C_Agra%2C_India.jpg",
    "Varanasi":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/Varanasi%2C_India%2C_Ghats%2C_Cremation_ceremony_in_progress.jpg/500px-Varanasi%2C_India%2C_Ghats%2C_Cremation_ceremony_in_progress.jpg",
    "Amritsar":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Golden_Temple_Amritsar_Gurudwara_%28cropped%29.jpg/500px-Golden_Temple_Amritsar_Gurudwara_%28cropped%29.jpg",
    "Rishikesh":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/7/74/Trayambakeshwar_Temple_VK.jpg/500px-Trayambakeshwar_Temple_VK.jpg",
    "Shimla":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Landscape_of_Shimla_%2C_Himachal_Pradesh.jpg/500px-Landscape_of_Shimla_%2C_Himachal_Pradesh.jpg",
    "Manali":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/0/03/Manali_City.jpg/500px-Manali_City.jpg",
    "Udaipur":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Evening_view%2C_City_Palace%2C_Udaipur.jpg/500px-Evening_view%2C_City_Palace%2C_Udaipur.jpg",
    "Jodhpur":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Mehrangarh_Fort_sanhita.jpg/500px-Mehrangarh_Fort_sanhita.jpg",
    "Bengaluru":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/View_from_Visvesvaraya_Industrial_and_Technological_Museum_%282025%29_02.jpg/500px-View_from_Visvesvaraya_Industrial_and_Technological_Museum_%282025%29_02.jpg",
    "Chennai":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/3/32/Chennai_Central.jpg/500px-Chennai_Central.jpg",
    "Mysuru":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Mysuru_Montage.jpg/500px-Mysuru_Montage.jpg",
    "Madurai":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Meenakshi_Amman_West_Tower.jpg/500px-Meenakshi_Amman_West_Tower.jpg",
    "Kochi":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Kochi_Skyline.jpg/500px-Kochi_Skyline.jpg",
    "Alleppey":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Alappuzha_Boat_Beauty_W.jpg/500px-Alappuzha_Boat_Beauty_W.jpg",
    "Hampi":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Wide_angle_of_Galigopuram_of_Virupaksha_Temple%2C_Hampi_%2804%29_%28cropped%29.jpg/500px-Wide_angle_of_Galigopuram_of_Virupaksha_Temple%2C_Hampi_%2804%29_%28cropped%29.jpg",
    "Red Fort":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Delhi_fort.jpg/500px-Delhi_fort.jpg",
    "Qutub Minar":                 "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/Qutb_Minar_2022.jpg/500px-Qutb_Minar_2022.jpg",
    "Humayun's Tomb":              "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Tomb_of_Humayun%2C_Delhi.jpg/500px-Tomb_of_Humayun%2C_Delhi.jpg",
    "Lotus Temple":                "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/LotusDelhi.jpg/500px-LotusDelhi.jpg",
    "Chandni Chowk":               "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Gurudwara_Sisganj_Sahib_Chandni_Chowk_19.jpg/500px-Gurudwara_Sisganj_Sahib_Chandni_Chowk_19.jpg",
    "India Gate":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/India_Gate_in_the_Evening.jpg/500px-India_Gate_in_the_Evening.jpg",
    "Taj Mahal":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Taj_Mahal_%28Edited%29.jpeg/500px-Taj_Mahal_%28Edited%29.jpeg",
    "Agra Fort":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Agra_03-2016_10_Agra_Fort.jpg/500px-Agra_03-2016_10_Agra_Fort.jpg",
    "Fatehpur Sikri":              "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Fatehput_Sikiri_Buland_Darwaza_gate_2010.jpg/500px-Fatehput_Sikiri_Buland_Darwaza_gate_2010.jpg",
    "Mehtab Bagh":                 "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Mehtab_Bagh_facing_Taj_Mahal.JPG/500px-Mehtab_Bagh_facing_Taj_Mahal.JPG",
    "Itmad-ud-Daulah":             "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/I%27tim%C4%81d-ud-Daulah%2C_Agra.jpg/500px-I%27tim%C4%81d-ud-Daulah%2C_Agra.jpg",
    "Dashashwamedh Ghat":          "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Dasaswamedh_ghat-varanasi_india-andres_larin.jpg/500px-Dasaswamedh_ghat-varanasi_india-andres_larin.jpg",
    "Kashi Vishwanath Temple":     "https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Kashi_Vishwanath.jpg/500px-Kashi_Vishwanath.jpg",
    "Sarnath":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Ancient_Buddhist_monasteries_near_Dhamekh_Stupa_Monument_Site%2C_Sarnath.jpg/500px-Ancient_Buddhist_monasteries_near_Dhamekh_Stupa_Monument_Site%2C_Sarnath.jpg",
    "Assi Ghat":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Assi_Ghat_Varanasi_morning_Aarti.jpg/500px-Assi_Ghat_Varanasi_morning_Aarti.jpg",
    "Golden Temple":               "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/The_Golden_Temple_of_Amrithsar_7.jpg/500px-The_Golden_Temple_of_Amrithsar_7.jpg",
    "Jallianwala Bagh":            "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Jallianwala_Bagh%2C_Amritsar_01.jpg/500px-Jallianwala_Bagh%2C_Amritsar_01.jpg",
    "Wagah Border Ceremony":       "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Wagah_border_ceremony2.jpg/500px-Wagah_border_ceremony2.jpg",
    "Partition Museum":            "https://upload.wikimedia.org/wikipedia/en/thumb/b/b3/Partition_museum_logo.jpg/500px-Partition_museum_logo.jpg",
    "Laxman Jhula":                "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Rishikesh-Lakshman_Jhula_by_Kaustubh_Nayyar.jpg/500px-Rishikesh-Lakshman_Jhula_by_Kaustubh_Nayyar.jpg",
    "Neelkanth Mahadev Temple":    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/NeelKanth_Mahadev_Temple.JPG/500px-NeelKanth_Mahadev_Temple.JPG",
    "The Ridge":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/The_Ridge_Shimla_5.jpg/500px-The_Ridge_Shimla_5.jpg",
    "Jakhoo Temple":               "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Jakhoo_temple.jpg/500px-Jakhoo_temple.jpg",
    "Kalka-Shimla Toy Train":      "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/KSR_Steam_special_at_Taradevi_05-02-13_56.jpeg/500px-KSR_Steam_special_at_Taradevi_05-02-13_56.jpeg",
    "Mall Road":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Mall_Road_Shimla_1.jpg/500px-Mall_Road_Shimla_1.jpg",
    "Viceregal Lodge":             "https://upload.wikimedia.org/wikipedia/en/8/83/IIAS_Shimla_logo.jpg",
    "Hadimba Temple":              "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Hidimba_Devi_Temple_-_North-east_View_-_Manali_2014-05-11_2648-2649.TIF/lossy-page1-330px-Hidimba_Devi_Temple_-_North-east_View_-_Manali_2014-05-11_2648-2649.TIF.jpg",
    "Solang Valley":               "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f1/Solang_Valley_%2CManali%2C_Himachal_Pardes%2C_India.JPG/500px-Solang_Valley_%2CManali%2C_Himachal_Pardes%2C_India.JPG",
    "Rohtang Pass":                "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Kullu_Valley_from_Rohtang_Pass%2C_India.jpg/500px-Kullu_Valley_from_Rohtang_Pass%2C_India.jpg",
    "Vashisht Hot Springs":        "https://upload.wikimedia.org/wikipedia/en/thumb/e/eb/Vashisht_temple.jpg/500px-Vashisht_temple.jpg",
    "City Palace":                 "https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Udaipur_City_Palace.jpg/500px-Udaipur_City_Palace.jpg",
    "Lake Pichola Boat Ride":      "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Udaipur_Lake_India.JPG/500px-Udaipur_Lake_India.JPG",
    "Jagdish Temple":              "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Jagdish_Temple_Udaipur.jpg/500px-Jagdish_Temple_Udaipur.jpg",
    "Saheliyon ki Bari":           "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Saheliyon-ki-Bari_Fountain.JPG/500px-Saheliyon-ki-Bari_Fountain.JPG",
    "Bagore ki Haveli":            "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Bagore_ki_Haveli%2C_Rajasthan.jpg/500px-Bagore_ki_Haveli%2C_Rajasthan.jpg",
    "Mehrangarh Fort":             "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Mehrangarh_Fort_sanhita.jpg/500px-Mehrangarh_Fort_sanhita.jpg",
    "Jaswant Thada":               "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Jaswant_Thada_Dawn.jpg/500px-Jaswant_Thada_Dawn.jpg",
    "Umaid Bhawan Palace":         "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/1996_-218-20A_Jodhpur_Hotel_Umaid_Bhawan_Palace_%282233393509%29.jpg/500px-1996_-218-20A_Jodhpur_Hotel_Umaid_Bhawan_Palace_%282233393509%29.jpg",
    "Mandore Gardens":             "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Temples_at_Mandor_%284571805346%29.jpg/500px-Temples_at_Mandor_%284571805346%29.jpg",
    "Bangalore Palace":            "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Bangalore_Mysore_Maharaja_Palace.jpg/500px-Bangalore_Mysore_Maharaja_Palace.jpg",
    "Cubbon Park":                 "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Cubbon_Park_W.jpg/500px-Cubbon_Park_W.jpg",
    "ISKCON Temple Bengaluru":     "https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/ISKCON_Banglaore_Temple.jpg/500px-ISKCON_Banglaore_Temple.jpg",
    "Commercial Street":           "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Commercial_Street%2C_Bangalore_%287870987476%29.jpg/500px-Commercial_Street%2C_Bangalore_%287870987476%29.jpg",
    "Marina Beach":                "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Chennai_-_bird%27s-eye_view.jpg/500px-Chennai_-_bird%27s-eye_view.jpg",
    "Kapaleeshwarar Temple":       "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Kapaleeswarar1.jpg/500px-Kapaleeswarar1.jpg",
    "Fort St. George":             "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Fort_St._George%2C_Chennai_2.jpg/500px-Fort_St._George%2C_Chennai_2.jpg",
    "Government Museum Chennai":   "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Madras_museum_theatre_in_October_2007.jpg/500px-Madras_museum_theatre_in_October_2007.jpg",
    "Mahabalipuram":               "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/A_collage_of_Mamallapuram_town_Tamil_Nadu_India.jpg/500px-A_collage_of_Mamallapuram_town_Tamil_Nadu_India.jpg",
    "Mysore Palace":               "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Mysore_Palace_Morning.jpg/500px-Mysore_Palace_Morning.jpg",
    "Chamundi Hill":               "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/J.C.Nagar_Welcome_Board_to_Chamundi_Hills.jpg/500px-J.C.Nagar_Welcome_Board_to_Chamundi_Hills.jpg",
    "Brindavan Gardens":           "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/Brindavan_Gardens.JPG/500px-Brindavan_Gardens.JPG",
    "Devaraja Market":             "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Devaraja_Market%2C_Mysore_%28306989724%29.jpg/500px-Devaraja_Market%2C_Mysore_%28306989724%29.jpg",
    "St. Philomena Church":        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/India_-_St._Philomena%27s_Church_02.jpg/500px-India_-_St._Philomena%27s_Church_02.jpg",
    "Meenakshi Amman Temple":      "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/An_aerial_view_of_Madurai_city_from_atop_of_Meenakshi_Amman_temple.jpg/500px-An_aerial_view_of_Madurai_city_from_atop_of_Meenakshi_Amman_temple.jpg",
    "Thirumalai Nayakkar Palace":  "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Madurai_Nayak_Palace_Collage.jpg/500px-Madurai_Nayak_Palace_Collage.jpg",
    "Gandhi Memorial Museum":      "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Gandhi_Memorial_Museum.jpg/500px-Gandhi_Memorial_Museum.jpg",
    "Alagar Kovil":                "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/AzhagarKovil_Madurai.JPG/500px-AzhagarKovil_Madurai.JPG",
    "Chinese Fishing Nets":        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Chinese_Fishing_Net_Raising_Birds_Sunrise_Ashtamudi_Kollam_Mar22_A7C_01784.jpg/500px-Chinese_Fishing_Net_Raising_Birds_Sunrise_Ashtamudi_Kollam_Mar22_A7C_01784.jpg",
    "Mattancherry Palace":         "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Mattancherry_Palace_DSC_0899.JPG/500px-Mattancherry_Palace_DSC_0899.JPG",
    "Paradesi Synagogue":          "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Jewish_synagouge_kochi_india.jpg/500px-Jewish_synagouge_kochi_india.jpg",
    "Fort Kochi Beach":            "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Kochi%2C_Fishing_nets_at_sunset%2C_Kerala%2C_India.jpg/500px-Kochi%2C_Fishing_nets_at_sunset%2C_Kerala%2C_India.jpg",
    "Kathakali Performance":       "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Kathakali_-Play_with_Kaurava.jpg/500px-Kathakali_-Play_with_Kaurava.jpg",
    "Backwater Houseboat":         "https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/Kerala_Houseboat_%28191490747%29.jpeg/500px-Kerala_Houseboat_%28191490747%29.jpeg",
    "Alappuzha Beach":             "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Alleppey_beach.jpg/500px-Alleppey_beach.jpg",
    "Marari Beach":                "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/Sunset_from_Mararikulam_beach%2C_Kerala%2C_India.jpg/500px-Sunset_from_Mararikulam_beach%2C_Kerala%2C_India.jpg",
    "Pathiramanal Island":         "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Pathiramanal_Island%2C_Muhamma.jpg/500px-Pathiramanal_Island%2C_Muhamma.jpg",
    "Krishnapuram Palace":         "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Krishnapuram_Palace_in_2021.jpeg/500px-Krishnapuram_Palace_in_2021.jpeg",
    "Virupaksha Temple":           "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Complex_of_Virupaksha_Temple%2C_Hampi_%2804%29.jpg/500px-Complex_of_Virupaksha_Temple%2C_Hampi_%2804%29.jpg",
    "Hampi Bazaar":                "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Wide_angle_of_Galigopuram_of_Virupaksha_Temple%2C_Hampi_%2804%29_%28cropped%29.jpg/500px-Wide_angle_of_Galigopuram_of_Virupaksha_Temple%2C_Hampi_%2804%29_%28cropped%29.jpg",
    "Matanga Hill":                "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Enroute_to_Matanga_hills%2C_Hampi.jpg/500px-Enroute_to_Matanga_hills%2C_Hampi.jpg",
    "Lotus Mahal":                 "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/Flat_elevation_of_Lotus_Mahal%2C_Hampi_%28Closeup%29.jpg/500px-Flat_elevation_of_Lotus_Mahal%2C_Hampi_%28Closeup%29.jpg",
    "Promenade Beach":             "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Pondicherry-Rock_beach_aerial_view.jpg/500px-Pondicherry-Rock_beach_aerial_view.jpg",
    "Sri Aurobindo Ashram":        "https://upload.wikimedia.org/wikipedia/commons/f/f3/The-Mothers-Symbol.png",
    "Auroville":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Town_Hall_of_Auroville.jpg/500px-Town_Hall_of_Auroville.jpg",
    "Puducherry":                          "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Pondicherry-Rock_beach_aerial_view.jpg/500px-Pondicherry-Rock_beach_aerial_view.jpg",
    "Triveni Ghat":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Triveni_Ghat_Krishna_Arjun_Rath.jpg/500px-Triveni_Ghat_Krishna_Arjun_Rath.jpg",
    "Lalbagh Botanical Garden":            "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Glasshouse_and_fountain_at_lalbagh.jpg/500px-Glasshouse_and_fountain_at_lalbagh.jpg",
    "Hall Bazaar":                           "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Hall_Gate.jpg/500px-Hall_Gate.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
    "Ganga Rafting":                         "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Rafting_in_Rishikesh.jpg/500px-Rafting_in_Rishikesh.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
    "Clock Tower Market":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Clock_Tower%2C_Sardar_Market%2C_Jodhpur.jpg/500px-Clock_Tower%2C_Sardar_Market%2C_Jodhpur.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
    "Vittala Temple":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Hampi_Garuda_stone_chariot.jpg/500px-Hampi_Garuda_stone_chariot.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
    "Paradise Beach":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Paradise_beach.jpg/500px-Paradise_beach.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
    "Banaras Silk Weavers Market":           "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Alkama_Ansari_-_A_Banarasi_Saree_Weaver.jpg/500px-Alkama_Ansari_-_A_Banarasi_Saree_Weaver.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
    "Beatles Ashram":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/A_cave_at_Beatles_Ashram_at_Rishikesh.jpg/500px-A_cave_at_Beatles_Ashram_at_Rishikesh.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
    "French Quarter":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Aurobindo_Ashram_Press_at_Goubert_Ave%2C_White_Town%2C_Puducherry_06.jpg/500px-Aurobindo_Ashram_Press_at_Goubert_Ave%2C_White_Town%2C_Puducherry_06.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
    "Tirupati":                          "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Tirumala_090615.jpg/500px-Tirumala_090615.jpg",
    "Tirumala Venkateswara Temple":      "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Tirumala_090615.jpg/500px-Tirumala_090615.jpg",
    "Sri Padmavathi Temple":             "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Padmavathi_Ammavari_Temple.JPG/500px-Padmavathi_Ammavari_Temple.JPG",
    "Srisailam":                         "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Srisailam.jpg/500px-Srisailam.jpg",
    "Mallikarjuna Jyotirlinga Temple":   "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Srisailam-temple-entrance.jpg/500px-Srisailam-temple-entrance.jpg",
    "Srisailam Dam":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/NSRS_Srisailam_Dam.jpg/500px-NSRS_Srisailam_Dam.jpg",
    "Vijayawada":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/92/Prakasham_Barriage%2C_Vijayawada.jpg/500px-Prakasham_Barriage%2C_Vijayawada.jpg",
    "Kanaka Durga Temple":               "https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Kanakadurga_Temple_gopuram.jpg/500px-Kanakadurga_Temple_gopuram.jpg",
    "Undavalli Caves":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/Undavalli_Caves%2C_Vijayawada%2C_Guntur%2C_Andhra_Pradesh%2C_India_%282018%29_1.jpg/500px-Undavalli_Caves%2C_Vijayawada%2C_Guntur%2C_Andhra_Pradesh%2C_India_%282018%29_1.jpg",
    "Prakasam Barrage":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Prakasam_Barrage_from_Vijayawada_to_Guntur_2_%28November_2018%29.jpg/500px-Prakasam_Barrage_from_Vijayawada_to_Guntur_2_%28November_2018%29.jpg",
    "Bhavani Island":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Man_Made_Island_near_Bhavani_Island.jpg/500px-Man_Made_Island_near_Bhavani_Island.jpg",
    "Srikalahasti":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Srikalahasti_temple_and_Hill.jpg/500px-Srikalahasti_temple_and_Hill.jpg",
    "Srikalahasteeswara Temple":         "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Sri_Kala_Hasti.jpg/500px-Sri_Kala_Hasti.jpg",
    "Yadadri Lakshmi Narasimha Temple":  "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Yadadri_Temple_on_the_hilltop.jpg/500px-Yadadri_Temple_on_the_hilltop.jpg",
    "Bhadrachalam":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Sri_sita_rama_temple_bhadrachalam_temple_view.jpg/500px-Sri_sita_rama_temple_bhadrachalam_temple_view.jpg",
    "Sri Sita Ramachandraswamy Temple":  "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Sri_sita_rama_temple_bhadrachalam_temple_view.jpg/500px-Sri_sita_rama_temple_bhadrachalam_temple_view.jpg",
    "Parnasala":                         "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/View_of_Parnasala_in_Khammam_District.JPG/500px-View_of_Parnasala_in_Khammam_District.JPG",
    "Godavari Ghat":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/NashikViewfromPandavLeni.jpg/500px-NashikViewfromPandavLeni.jpg",
    "Basara":                            "https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Basar_Temple_view_02.jpg/500px-Basar_Temple_view_02.jpg",
    "Gnana Saraswati Temple":            "https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Basar_Temple_view_02.jpg/500px-Basar_Temple_view_02.jpg",
    "Rameswaram":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Rameswaram_Morning.jpg/500px-Rameswaram_Morning.jpg",
    "Ramanathaswamy Temple":             "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Ramanathaswamy_temple7.JPG/500px-Ramanathaswamy_temple7.JPG",
    "Pamban Bridge":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Pamban_Bridge_Train_Passing.jpg/500px-Pamban_Bridge_Train_Passing.jpg",
    "Dhanushkodi":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Final_Dhanush_002.jpg/500px-Final_Dhanush_002.jpg",
    "Agnitheertham":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Rameswaram_Morning.jpg/500px-Rameswaram_Morning.jpg",
    "Kanchipuram":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Parameswara_Vinnagaram.JPG/500px-Parameswara_Vinnagaram.JPG",
    "Kamakshi Amman Temple":             "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Kanchipuram.in_Kamakshi-Amman_Temple_-_panoramio_-_SINHA_%28cropped%29.jpg/500px-Kanchipuram.in_Kamakshi-Amman_Temple_-_panoramio_-_SINHA_%28cropped%29.jpg",
    "Kailasanathar Temple":              "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/7th_century_Sri_Kailashnathar_Temple_Kanchipuram_Tamil_Nadu_India_01_%2811%29.jpg/500px-7th_century_Sri_Kailashnathar_Temple_Kanchipuram_Tamil_Nadu_India_01_%2811%29.jpg",
    "Srirangam":                         "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/Aerial_view_of_Sri_Rangam_temple_near_Tiruchirapalli_1.jpg/500px-Aerial_view_of_Sri_Rangam_temple_near_Tiruchirapalli_1.jpg",
    "Ranganathaswamy Temple":            "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Ranganathaswamy_temple_tiruchirappalli.jpg/500px-Ranganathaswamy_temple_tiruchirappalli.jpg",
    "Jambukeswarar Temple":              "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Tiruvanaikaval5.jpg/500px-Tiruvanaikaval5.jpg",
    "Guruvayur":                           "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/009392022_Guruvayur_temple%2C_Kerala_004.jpg/500px-009392022_Guruvayur_temple%2C_Kerala_004.jpg",
    "Guruvayur Sri Krishna Temple":        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/Guruvayoor_Temple_1.jpg/500px-Guruvayoor_Temple_1.jpg",
    "Punnathur Kotta Elephant Sanctuary":  "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/PunathurKotta2.jpg/500px-PunathurKotta2.jpg",
    "Mammiyoor Temple":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/Mammiyoor_sree_mahadeva_temple.JPG/500px-Mammiyoor_sree_mahadeva_temple.JPG",
    "Shirdi":                              "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Sai_baba_samadhi_mandir_.jpg/500px-Sai_baba_samadhi_mandir_.jpg",
    "Sai Baba Samadhi Mandir":             "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Sai_baba_samadhi_mandir_.jpg/500px-Sai_baba_samadhi_mandir_.jpg",
    "Dwarkamai":                           "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Sai_baba_samadhi_mandir_.jpg/500px-Sai_baba_samadhi_mandir_.jpg",
    "Trimbakeshwar":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Trimbakeshwar_Temple-Nashik-Maharashtra-1.jpg/500px-Trimbakeshwar_Temple-Nashik-Maharashtra-1.jpg",
    "Trimbakeshwar Temple":                "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Trimbakeshwar_Temple-Nashik-Maharashtra-1.jpg/500px-Trimbakeshwar_Temple-Nashik-Maharashtra-1.jpg",
    "Kushavarta Kund":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Trimbakeshwar_Temple-Nashik-Maharashtra-1.jpg/500px-Trimbakeshwar_Temple-Nashik-Maharashtra-1.jpg",
    "Somnath":                             "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Somanath_mandir_%28cropped%29.jpg/500px-Somanath_mandir_%28cropped%29.jpg",
    "Somnath Temple":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Somanath_mandir_%28cropped%29.jpg/500px-Somanath_mandir_%28cropped%29.jpg",
    "Bhalka Tirth":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/BHALKA-06.jpg/500px-BHALKA-06.jpg",
    "Dwarka":                              "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Dwarakadheesh_Temple%2C_2014.jpg/500px-Dwarakadheesh_Temple%2C_2014.jpg",
    "Dwarkadhish Temple":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Dwarakadheesh_Temple%2C_2014.jpg/500px-Dwarakadheesh_Temple%2C_2014.jpg",
    "Bet Dwarka":                          "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Bet_Dwarka_Okha_Gujarat_Map.jpg/500px-Bet_Dwarka_Okha_Gujarat_Map.jpg",
    "Nageshwar Jyotirlinga":               "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Nageshwar.JPG/500px-Nageshwar.JPG",
    "Ayodhya":                             "https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Shri_Ram_Janambhoomi_Mandir%2C_Ayodhya_Dham.jpg/500px-Shri_Ram_Janambhoomi_Mandir%2C_Ayodhya_Dham.jpg",
    "Ram Janmabhoomi Temple":              "https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Shri_Ram_Janambhoomi_Mandir%2C_Ayodhya_Dham.jpg/500px-Shri_Ram_Janambhoomi_Mandir%2C_Ayodhya_Dham.jpg",
    "Hanuman Garhi":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/Hanuman_Garhi_Temple%2C_a_major_religious_site_in_Ayodhya_utter_pradesh.jpg/500px-Hanuman_Garhi_Temple%2C_a_major_religious_site_in_Ayodhya_utter_pradesh.jpg",
    "Ram Ki Paidi":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Sarayu_River_night_view%2C_Ayodhya_001.jpg/500px-Sarayu_River_night_view%2C_Ayodhya_001.jpg",
    "Ujjain":                              "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Mahakaleshwar_Temple%2C_Ujjain.jpg/500px-Mahakaleshwar_Temple%2C_Ujjain.jpg",
    "Mahakaleshwar Jyotirlinga":           "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Mahakaleshwar_Temple%2C_Ujjain.jpg/500px-Mahakaleshwar_Temple%2C_Ujjain.jpg",
    "Ram Ghat":                            "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Mahakaleshwar_Temple%2C_Ujjain.jpg/500px-Mahakaleshwar_Temple%2C_Ujjain.jpg",
    "Kal Bhairav Temple":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Kal_Bhairav_temple_Ujjain.jpg/500px-Kal_Bhairav_temple_Ujjain.jpg",
    "Vedh Shala Observatory":              "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Sun_Dial_Ved_Shala_Ujjain.jpg/500px-Sun_Dial_Ved_Shala_Ujjain.jpg",
    "Jagannath Temple":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/Shri_Jagannath_temple.jpg/500px-Shri_Jagannath_temple.jpg",
    "Puri Beach":                          "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ee/Puri_Sea_Beach_viewed_from_the_light_house.jpg/500px-Puri_Sea_Beach_viewed_from_the_light_house.jpg",
    "Konark Sun Temple":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/Konarka_Temple.jpg/500px-Konarka_Temple.jpg",
    "Chilika Lake":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/Birds_eyeview_of_Chilika_Lake.jpg/500px-Birds_eyeview_of_Chilika_Lake.jpg",
    "Bodh Gaya":                           "https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/Mahabodhi_temple_at_Bodhgaya_in_Bihar_21.jpg/500px-Mahabodhi_temple_at_Bodhgaya_in_Bihar_21.jpg",
    "Mahabodhi Temple":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Mahabodhitemple.jpg/500px-Mahabodhitemple.jpg",
    "Sujata Stupa":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Sujata_Garh.JPG/500px-Sujata_Garh.JPG",
    "Haridwar":                            "https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/Ganga_aarti_haridwar_01.jpg/500px-Ganga_aarti_haridwar_01.jpg",
    "Har Ki Pauri":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/Evening_view_of_Har-ki-Pauri%2C_Haridwar.jpg/500px-Evening_view_of_Har-ki-Pauri%2C_Haridwar.jpg",
    "Mansa Devi Temple":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/3/31/Mansa_Devi_Temple%2C_Haridwar.JPG/500px-Mansa_Devi_Temple%2C_Haridwar.JPG",
    "Chandi Devi Temple":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Chandi_Devi_Mandir%2CHaridwar.JPG/500px-Chandi_Devi_Mandir%2CHaridwar.JPG",
    "Kedarnath":                           "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Kedarnath_View1.jpg/500px-Kedarnath_View1.jpg",
    "Kedarnath Temple":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Kedarnath_Temple_in_Rainy_season.jpg/500px-Kedarnath_Temple_in_Rainy_season.jpg",
    "Badrinath":                           "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Badrinath_Temple-_Uttarakhand.jpg/500px-Badrinath_Temple-_Uttarakhand.jpg",
    "Badrinath Temple":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Badrinath_Temple_%2C_Uttarakhand.jpg/500px-Badrinath_Temple_%2C_Uttarakhand.jpg",
    "Tapt Kund":                           "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Badrinath_Temple-_Uttarakhand.jpg/500px-Badrinath_Temple-_Uttarakhand.jpg",
    "Mana Village":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/India_lsat_village.jpg/500px-India_lsat_village.jpg",
    "Vaishno Devi":                        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Snowfall_in_Vaishno_Devi.jpg/500px-Snowfall_in_Vaishno_Devi.jpg",
    "Vaishno Devi Bhawan":                 "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Snowfall_in_Vaishno_Devi.jpg/500px-Snowfall_in_Vaishno_Devi.jpg",
    "Ardhkuwari":                          "https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Ardhkuwari_temple_at_night.jpg/500px-Ardhkuwari_temple_at_night.jpg",
    "Puri":                                  "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Shri_Jagannatha_Temple.jpg/500px-Shri_Jagannatha_Temple.jpg",
    # The hilltop temple is the town, so its photograph is the destination's.
    "Yadadri":                               "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Yadadri_Temple_on_the_hilltop.jpg/500px-Yadadri_Temple_on_the_hilltop.jpg",
    "Annavaram":                             "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Night_view_of_Raja_Gopuram_Annvaram.jpg/500px-Night_view_of_Raja_Gopuram_Annvaram.jpg",
    "Sri Veera Venkata Satyanarayana Swamy Temple": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Night_view_of_Raja_Gopuram_Annvaram.jpg/500px-Night_view_of_Raja_Gopuram_Annvaram.jpg",
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
