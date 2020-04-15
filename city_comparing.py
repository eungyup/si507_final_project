import datetime
import requests
from bs4 import BeautifulSoup
import json
import secrets
import csv
import sqlite3
import time

# For Caching
CACHE_FILENAME = "cache.json"
CACHE_DICT = {}

# For Database
DB_NAME = "city_compare.sqlite"

# For Event
BASIC_EVENT_BRITE_URL = "https://www.eventbrite.com/d/mi"

event_names = []

event_calendar = []
event_day = []
event_date = []
event_time = []

event_location = []
event_city = []
event_state = []

# Event Crawling Numbers for Michigan (State)
state_event_crawling_numbers = 52

# Event Carwling Numbers for each city
# city_event_crawling_numbers = 7

# For Restaurant
YELP_API_URL="https://api.yelp.com/v3/businesses/search"
YELP_API_KEY = secrets.YELP_API_KEY

# For Cities Names
US_CITIES = "uscities.csv"


'''
(my)
Part 1: Data Collection
'''
# (my) Part1 - Eventbrite
# (my) Scraping each page
def get_event_information(a_page_url):
    '''Get event information and store it in each event lists

    Parameters
    ----------
    a_page_url: string
        The URL for an eventbrite url
        i.e. (first page)  https://www.eventbrite.com/d/united-states--michigan/all-events/
        i.e. (second page) https://www.eventbrite.com/d/united-states--michigan/all-events/?page=2

    Returns
    -------
    none
    '''
    response = make_request_with_cache(a_page_url)
    soup = BeautifulSoup(response, "html.parser")
    '''
    For event name, location, and price
    '''
    header_div = soup.find_all('article', class_='eds-l-pad-all-4 eds-media-card-content eds-media-card-content--list eds-media-card-content--standard eds-media-card-content--fixed eds-l-pad-vert-3')
    for item in header_div:
        # Event name
        an_event = item.find('div', class_='eds-event-card__formatted-name--is-clamped eds-event-card__formatted-name--is-clamped-three eds-text-weight--heavy', role='presentation').text.strip()
        event_names.append(an_event)

        # Event Location: location name, city, state
        if item.find('div', class_='eds-media-card-content__sub-content'):
            location_container = item.find('div', class_='eds-media-card-content__sub-content')
            if location_container.find('div', class_='card-text--truncated__one'):
                location = location_container.find('div', class_='card-text--truncated__one').text.strip()
                if "•" in location:
                    # Location i.e. "Brightmoor Christian Church • Novi, MI"
                    # Location Name
                    location_split = location.split(" •")
                    event_location.append(location_split[0])
                    # City
                    city_split = location_split[1].strip().split(", ")
                    event_city.append(city_split[0])
                    # State
                    event_state.append(city_split[1])
                else:
                    # Location i.e. "Fisherman's Landing Launch and Campground"
                    event_location.append(location)
                    city = "City Not Available"
                    state = "Stat Not Available"
                    event_city.append(city)
                    event_state.append(state)
            else:
                location = "Location Not Available"
                city = "City Not Available"
                state = "Stat Not Available"
                event_location.append(location)
                event_city.append(city)
                event_state.append(state)
        else:
            location = "Location Not Available"
            city = "City Not Available"
            state = "Stat Not Available"
            event_location.append(location)
            event_city.append(city)
            event_state.append(state)

    '''
    For calendar
    '''
    calendar_price_container = soup.find_all('div', class_='search-event-card-square-image')
    # print(calendar_container)
    for item in calendar_price_container:
        # Event Calendar
        calendar = item.find('div', class_='eds-text-color--primary-brand eds-l-pad-bot-1 eds-text-weight--heavy eds-text-bs').text.strip()
        event_calendar.append(calendar)
        '''
        Get Day, Date, and Time
        '''
        calendar_split = calendar.split(', ')
        # If the event is today or tommorow, the Eventbrite shows like 'Tomorrow at 5:30 PM' or 'Today at 6:00 PM'
        if len(calendar_split) <= 1:
            # print(calendar_split)
            current_date_time = datetime.datetime.now()

            day = current_date_time.strftime("%a")
            event_day.append(day)

            date = current_date_time.strftime("%b")+ " " + current_date_time.strftime("%d")
            event_date.append(date)

            calendar_split_at = calendar_split[0].split('at')
            event_time.append(calendar_split_at[1])
        # If the event is not today or tomorrow, the Eventbrite shows like 'Sat, Apr 18, 3:00 PM'
        else:
            event_day.append(calendar_split[0])
            event_date.append(calendar_split[1])
            event_time.append(calendar_split[2])

# Crawling
def crawl_event_pages(event_brite_state_url, event_crawling_numbers):
    '''Crawling eventbrite pages and get event information from each page.

    Parameters
    ----------
    event_brite_city_url: string
        The combied event_brite_state_url (BASIC_EVENT_BRITE_URL + state)
        i.e. https://www.eventbrite.com/d/united-states--michigan/all-events/
    event_crawling_numbers: int
        i.e. michigan state => 25
    Returns
    -------
    none
    '''

    for i in range(event_crawling_numbers):
        if i == 0:
            get_event_information(event_brite_state_url)
        else:
            i += 1
            next_page = f"?page={i}"
            next_url = event_brite_state_url + next_page
            get_event_information(next_url)


def get_restaurant_information(a_city):
    '''Obtain restaurant API data from YELP Fusion API.

    Parameters
    ----------
    user_city: string
        user's state

    Returns
    -------
    dict
        a converted API return from YELP Fusion API
    '''

    offset_num = get_yelp_offset_number()

    total_result = []

    headers = {'Authorization': f'Bearer {YELP_API_KEY}'}

    for an_offset_num in offset_num:
        params = {
            'location': a_city,
            'offset': an_offset_num,
            'limit': 50,
        }
        response = make_request_with_cache(YELP_API_URL, params=params, headers=headers)
        # result = response.json()
        # Because sometimes there are not 1000 restaurants in a city, the response may retrun "error" key
        # instead of 'businesses' key. To prevent this, check if there is a 'business' key to exclude to append
        # error data
        if 'businesses' in response.keys():
            result_business = response['businesses']
            for item in result_business:
                total_result.append(item)
    # print(f"total_result: {total_result}")
    return total_result


def get_yelp_offset_number():
    '''Get a list of offset numbers increased by 50.
    i.e. 0, 50, 100, 150, 200, ...

    Parameters
    ----------
    None

    Returns
    -------
    list
        a list of offset numbers
    '''
    '''
    (my) Add Docstring
    '''
    offset_num =[]

    count = 0
    while count <= 950:
        offset_num.append(count)
        count += 50

    return offset_num


def get_cities_name(state_name):
    '''
    (my) Add Docstring
    got a whole list of cities names in US from https://simplemaps.com/data/us-cities
    state_name-> name of the state (two character)
    i.e."city","city_ascii","state_id","state_name","county_fips","county_name","county_fips_all","county_name_all","lat","lng","population","density","source","military","incorporated","timezone","ranking","zips","id"
    "South Creek","South Creek","WA","Washington","53053","Pierce","53053","Pierce","46.9994","-122.3921","2500","125","polygon","FALSE","TRUE","America/Los_Angeles","3","98580 98387 98338","1840042075"
    return -> a list of lower cased cities names in the state
    '''
    cities_list = []

    file_contents = open(US_CITIES,'r')
    file_reader = csv.reader(file_contents)

    # Skip header row
    next(file_contents)

    for city_data in file_reader:
        if city_data[2] == state_name:
            # Get Lowered City Name (i.e. detroit, ann arbor)
            cities_list.append(city_data[0].lower())

    return cities_list

'''
(my)
Part 2: Caching
'''
def open_cache():
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary.

    if the cache file doesn't exist, creates a new cache dictionary

    Parameters
    ----------
    None

    Returns
    -------
    The opened cache
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict


def save_cache(cache_dict):
    ''' saves the current state of the cache to disk

    Parameters
    ----------
    cache_dict: dict
        The dictionary to save

    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close()


def construct_unique_key(baseurl, params=None):
    ''' constructs a key that is guaranteed to uniquely and 
    repeatably identify an API request by its baseurl and params

    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint

    params: dictionary
        A dictionary of param: param_value pairs

    Returns
    -------
    string
        the unique key as a string
    '''
    param_strings = []
    connector = '_'
    if params:
        for k in params.keys():
            param_strings.append(f'{k}_{params[k]}')
        param_strings.sort()
        unique_key = baseurl + connector +  connector.join(param_strings)
        return unique_key
    else:
        unique_key = baseurl
        return unique_key


def make_request(baseurl, params=None, headers=None):
    '''Make a request to the Web API using the baseurl and params

    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint

    params: dictionary
        A dictionary of param: param_value pairs

    Returns
    -------
    dictionart
        the results of the query as a Python object loaded from JSON
    or
    string
        the results of the query as a HTML text loaded on the website
    '''
    response = requests.get(baseurl, params=params, headers=headers)

    if baseurl == YELP_API_URL:
        return response.json()
    else:
        # For beign a good citizen when scraping and crawling
        time.sleep(1)
        return response.text


def make_request_with_cache(baseurl, params=None, headers=None):
    '''Check the cache for a saved result for this baseurl+params
    combo. If the result is found, return it. Otherwise send a new
    request, save it, then return it.

    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint

    params: dictionary
        A dictionary of param: param_value pairs

    Returns
    -------
    string
        the results of the query as a Python object loaded from JSON
    '''
    request_key = construct_unique_key(baseurl, params)
    if request_key in CACHE_DICT.keys():
        print(f"Using cache! {request_key}")
        return CACHE_DICT[request_key]
    else:
        print(f"Fetching {request_key}")
        # print(f"request_key: {request_key}")
        CACHE_DICT[request_key] = make_request(baseurl, params, headers)
        save_cache(CACHE_DICT)
        return CACHE_DICT[request_key]


'''
Part 4 Database Acess and Storage
'''
# Create Tables
def create_db():
    # Create or connect database
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    drop_locations_sql = 'DROP TABLE IF EXISTS "Locations"'
    drop_events_sql = 'DROP TABLE IF EXISTS "Events"'
    drop_restaurants_sql = 'DROP TABLE IF EXISTS "Restaurants"'

    create_locations_sql = '''
        CREATE TABLE IF NOT EXISTS "Locations" (
            "Id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "City" TEXT NOT NULL,
            "State" TEXT NOT NULL,
            "Country" TEXT
        )
    '''

    create_events_sql = '''
        CREATE TABLE IF NOT EXISTS "Events"(
            "EventId" INTEGER PRIMARY KEY AUTOINCREMENT,
            "Name" TEXT NOT NULL,
            "Day" TEXT,
            "Date" TEXT,
            "Time" TEXT,
            "LocationId" INTEGER
        )
    '''

    create_restaurants_sql = '''
        CREATE TABLE IF NOT EXISTS "Restaurants"(
            "RestaurantId" TEXT PRIMARY KEY,
            "Name" TEXT NOT NULL,
            "Price" TEXT,
            "Rating" REAL,
            "TotalReviews" INTEGER,
            "PhoneNumber" TEXT,
            "LocationId" INTEGER
        )
    '''

    cur.execute(drop_locations_sql)
    cur.execute(drop_events_sql)
    cur.execute(drop_restaurants_sql)
    cur.execute(create_locations_sql)
    cur.execute(create_events_sql)
    cur.execute(create_restaurants_sql)
    conn.commit()
    conn.close()


# Part 4-b-i Load Cities Data
def load_locations():
    '''Insert data into the Dabatabe.
    Get data from uscities.csv, process data, and put the processed data into the Database.

    Parameters
    ----------
    None

    Returns
    -------
    None
    '''
    file_contents = open(US_CITIES,'r')
    file_reader = csv.reader(file_contents)

    # Skip header row
    next(file_contents)

    insert_location_sql = '''
            INSERT INTO Locations
            VALUES (NULL, ?, ?, ?)
        '''

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    for city_data in file_reader:
        cur.execute(insert_location_sql,
            [
                city_data[0], # City
                city_data[2], # State
                'USA',
            ]
        )
    conn.commit()
    conn.close()


def load_events(events_list):
    '''
    (my) Add Docstring
    events_list -> a list of state event dictionaries
    i.e. michigan_all_events -> a list of dictionaries of all michigan events
    i.e. [{'event_name': 'Drag Queen Bingo - Bus Stop Bar and Grille', 'event_location': 'The Bus Stop Bar & Grille', 'event_city': ' Birch Run', 'event_state': 'MI', 'event_day': 'Thu', 'event_date': 'Apr 16', 'event_time': '8:00 PM'}]

    retrun: none
    '''
    # Step 5
    select_location_id_sql = '''
        SELECT Id FROM Locations
        WHERE City = ? AND State = ?
    '''

    insert_event_sql = '''
        INSERT INTO Events
        VALUES (NULL, ?, ?, ?, ?, ?)
    '''

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    for row in events_list:
        cur.execute(select_location_id_sql, [
            row['event_city'], 
            row['event_state'],
            ])
        res = cur.fetchone()
        event_location_id = None
        if res is not None:
            event_location_id = res[0]

        cur.execute(insert_event_sql, [
            row['event_name'], # Event Name
            row['event_day'], # Event day 'Wed'
            row['event_date'], # Event date i.e. 'Sep 30'
            row['event_time'], # event_time i.e. 6:00 PM'
            event_location_id
        ])
    conn.commit()
    conn.close()


def load_restaurants(restaurant_list, a_city):
    '''
    (my) Add Docstring
    restaurant_list -> a list of a user's city restaurant information dicts
    i.e. michigan_one_thousand_restaurants -> a list of dictionaries of 1000 user's city restaurants info
    i.e. 	[{
		'id': 'HYrqw4xlLCNDptBHGrTIbQ',
		'alias': 'dime-store-detroit-4',
		'name': 'Dime Store',
		'image_url': 'https://s3-media4.fl.yelpcdn.com/bphoto/tBmxNQQCDvHYj4Fq_drkVw/o.jpg',
		'is_closed': False,
		'url': 'https://www.yelp.com/biz/dime-store-detroit-4?adjust_creative=tNtwZIWDRcDD5YP9E7ekhQ&utm_campaign=yelp_api_v3&utm_medium=api_v3_business_search&utm_source=tNtwZIWDRcDD5YP9E7ekhQ',
		'review_count': 1481,
        ...},
        {
            ...
        },
        {
            ...
        },
        ...
        ]
    a_city => string (i.e. detroit, ann arbor) -> use this to only get that city's restaurant
    (sometime i.e. detroit but get near restaurant)
    retrun: none
    '''
    # Step 5
    select_location_id_sql = '''
        SELECT Id FROM Locations
        WHERE City = ? AND State = ?
    '''

    # Becuase the resaurant bus id is unique, I didn't make it as auto increment.
    # Need to get the restaurant bus id as a PK 
    insert_restaurant_sql = '''
        INSERT INTO Restaurants
        VALUES (?, ?, ?, ?, ?, ?, ?)
    '''

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    for row in restaurant_list:
        if row['location']['city'].lower() == a_city and row['location']['state'].lower() == "mi":
            cur.execute(select_location_id_sql, [
                row['location']['city'], 
                row['location']['state'],
                ])
            res = cur.fetchone()
            restaurant_location_id = None
            if res is not None:
                restaurant_location_id = res[0]

            # Because sometimes there is no business ID which rarely happens, need to
            # configure this
            # id = None
            # if 'id' in row.keys():
            #     id = row['id']
            # else:
            #     id = f"No Business Id - {unique_counter}"
            #     counter += 1

            # name = None
            # if 'name' in row.keys():
            #     name = row['name']

            price = None
            if 'price' in row.keys():
                price = row['price']

            rating = None
            if 'rating' in row.keys():
                rating = row['rating']

            review_count = None
            if 'review_count' in row.keys():
                review_count = row['review_count']

            display_phone = None
            if 'display_phone' in row.keys():
                if row['display_phone'] == "":
                    pass
                else:
                    display_phone = row['display_phone']

            cur.execute(insert_restaurant_sql, [
                row['id'], # Restaurant Business Id
                row['name'], # Restaurant Name
                price, # Price
                rating, # Rating
                review_count, # Total Reviews Count
                display_phone, # Phone Number
                restaurant_location_id
            ])
    conn.commit()
    conn.close()


# Restaurant Query
# Total number of restaurant in a city
def total_number_of_restaurants(a_city):
    '''
    (my) Add Docstring
    a_city -> string (lower)
    i.e. detroit, ann arbor
    return a list of tuple(s) with average rating by city
    '''
    a_city_capital = capitalize_city_name(a_city)

    # print(f"city capitalized: {a_city_capital}")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    query = f'''
        SELECT COUNT(*), Locations.City
        FROM Restaurants
        JOIN Locations
        ON Restaurants.LocationId = Locations.Id
        WHERE Locations.City = "{a_city_capital}"
    '''

    print(f"SQL Query: {query}")

    cur.execute(query)
    result = cur.fetchall()

    # print(result)

    conn.close()

    return result


# Average restaurant rating for each cit
def average_city_restaurant_rating(a_city):
    '''
    (my) Add Docstring
    a_city -> string (lower)
    i.e. detroit, ann arbor
    return a list of tuple(s) with average rating by city
    '''
    a_city_capital = capitalize_city_name(a_city)

    # print(f"city capitalized: {a_city_capital}")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    query = f'''
        SELECT AVG(Restaurants.Rating), Locations.City
        FROM Restaurants
        JOIN Locations
        ON Restaurants.LocationId = Locations.Id
        WHERE Locations.City = "{a_city_capital}"
    '''

    print(f"SQL Query: {query}")

    cur.execute(query)
    result = cur.fetchall()

    # print(result)

    conn.close()

    return result


# Assistive function to capitalize city name
def capitalize_city_name(a_city):
    '''
    (my) Add Docstring
    a_city -> string (lower)
    i.e. detroit, ann arbor
    return a_city_capital (i.e. Detroit, Ann Arbor)
    '''
    a_city_capital = ""

    a_city_split = a_city.split(" ")

    print(a_city_split)

    if len(a_city_split) > 1:
        for i in range(len(a_city_split)):
            if (i + 1) < len(a_city_split):
                # Put a space in the end
                a_city_capital += f"{a_city_split[i].capitalize()} "
            else:
                # No space in the end for the last word
                a_city_capital += f"{a_city_split[i].capitalize()}"
    else:
        a_city_capital = a_city.capitalize()

    return a_city_capital


if __name__ == "__main__":

    '''
    Part 4 Database Accessing
    '''
    # Create the database tables
    create_db()
    # Insert Cities Data to the database
    load_locations()

    '''
    Test Part 1 and 2
    '''
    # Get all Michigan Events First
    CACHE_DICT = open_cache()
    michigan_event_url = 'https://www.eventbrite.com/d/united-states--michigan/all-events/'

    crawl_event_pages(michigan_event_url, state_event_crawling_numbers)

    # print(f"events name: {event_names}")
    # print(f"total # of events: {len(event_names)}")
    # print(f"location: {event_location}")
    # print(f"total # of locations: {len(event_location)}")
    # print(f"city: {event_city}")
    # print(f"total # of city: {len(event_city)}")
    # print(f"state: {event_state}")
    # print(f"total # of state: {len(event_state)}")
    # print(f"calendar: {event_calendar}")
    # print(f"total # of calendar: {len(event_calendar)}")
    # print(f"day: {event_day}")
    # print(f"total # of day: {len(event_day)}")
    # print(f"date: {event_date}")
    # print(f"total # of date: {len(event_date)}")
    # print(f"time: {event_time}")
    # print(f"total # of time: {len(event_time)}")

    michigan_all_events = []

    for i in range(len(event_names)):
        a_event_dict = {}
        a_event_dict["event_name"] = event_names[i]
        a_event_dict["event_location"] = event_location[i]
        a_event_dict["event_city"] = event_city[i]
        a_event_dict["event_state"] = event_state[i]
        a_event_dict["event_day"] = event_day[i]
        a_event_dict["event_date"] = event_date[i]
        a_event_dict["event_time"] = event_time[i]
        michigan_all_events.append(a_event_dict)

    # print(michigan_all_events)
    print(f"total # of michigan events data: {len(michigan_all_events)}")

    # Insert Michigan State Events records to the database
    load_events(michigan_all_events)

    # Insert Detroit Restaurants records to the database
    detroit_restaurants = get_restaurant_information("detroit")

    print(f"total # of restaurants in detroit + near detroit raw data: {len(detroit_restaurants)}")

    load_restaurants(detroit_restaurants, "detroit")

    # print(get_restaurant_information('detroit'))

    # Total number of restaurants in Detroit
    detroit_restaurants_numbers = total_number_of_restaurants("detroit")
    print(f"Total Restaurants numbers in Detroit: {detroit_restaurants_numbers}")

    # Detroit's Restaurants Average Rating
    # i.e. [(3.9340974212034383, 'Detroit')]
    detroit_restaurants_average_rating = average_city_restaurant_rating("detroit")
    print(f"Average Rating in Detroit: {detroit_restaurants_average_rating}")


    '''
    Part 3: Interactive: Midpoint Test
    '''

    # Get all cities name in Michigan
    mi_cities_lowered = get_cities_name("MI")
    # print(mi_cities)
    # There are 690 cities/townships
    # print(len(mi_cities))
    # i.e. an_event_city_name_for_url = "ann-arbor"
    an_event_city_name_for_url = ""

    print("Is your city in Michigan performing better than Detroit city (the largets city in MI)?")
    while True:
        user_input = input('Please type your city in Michigan (i.e. Ann Arbor, Lansing, etc) or type "exit" to end: ')

        # Because .isalpha() takes space between words no alphabet, use replace()
        if user_input.replace(' ','').isalpha():
            user_input_lower = user_input.lower()
            if user_input_lower == "exit":
                exit()
            else:
                if user_input_lower in mi_cities_lowered:
                    '''
                    Eventbrite
                    '''

                    # print(f"Your input is {user_input_lower}")
                    # user_city_restaurant_dict = get_restaurant_information(user_input_lower)
                    # print(user_city_restaurant_dict)

                    '''
                    User's City's Restaurant
                    '''
                    # Get User's City's Restaurant information and put it to the DB
                    # print("user input", user_input_lower)
                    user_city_restaurants = get_restaurant_information(user_input_lower)
                    # print(f"user city restaurants: {user_city_restaurants}")
                    load_restaurants(user_city_restaurants, user_input_lower)

                    # Total Number of Restaurant in the User's City
                    user_city_restaurants_numbers = total_number_of_restaurants(user_input_lower)
                    print(f"Total Restaurants numbers in {user_input_lower}: {user_city_restaurants_numbers}")
                    # User's Cities Average Restaurant Rating
                    # i.e. [(3.617879746835443, 'Ann Arbor')]
                    user_city_restaurants_rating = average_city_restaurant_rating(user_input_lower)
                    print(f"Average Restaurant Rating in {user_input_lower}: {user_city_restaurants_rating}")


                else:
                    print("Your city is not in Michigan or you put invalid input. Please try again.")
        else:
            print("Incorrect Input. Please try again")
