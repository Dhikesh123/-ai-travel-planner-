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
