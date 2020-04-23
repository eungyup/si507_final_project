import datetime
import requests
from bs4 import BeautifulSoup
import json
import secrets
import csv
import sqlite3
import time
from flask import Flask, render_template, request
import plotly.graph_objects as go

# For Caching
CACHE_FILENAME = "cache.json"
CACHE_DICT = {}

# For Database
DB_NAME = "city_compare.sqlite"

# For Event
MICHIGAN_EVENT_URL= 'https://www.eventbrite.com/d/united-states--michigan/all-events/'

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

# For Restaurant
YELP_API_URL="https://api.yelp.com/v3/businesses/search"
YELP_API_KEY = secrets.YELP_API_KEY

# For US Cities
# Reference: The uscities csv file was downloaded from https://simplemaps.com/data/us-cities.
US_CITIES = "uscities.csv"

# For Flask
app = Flask(__name__)

# User's city to be retrieved later
user_city = []

'''
Part 1: Data Collection
'''
# Part1 - Eventbrite
# Scraping each page
def get_event_information(a_page_url):
    '''Get event information and store it in each event lists.

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
                    # Online Event
                    if len(location_split[1].strip().split(", ")) <= 1:
                        city = "City Not Available"
                        state = "Stat Not Available"
                        event_city.append(city)
                        event_state.append(state)
                    else:
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
            tomorrow_date_time = current_date_time + datetime.timedelta(days=1)

            if 'Today' in calendar_split[0]:
                day = current_date_time.strftime("%a")
                event_day.append(day)
                date = current_date_time.strftime("%b")+ " " + current_date_time.strftime("%d")
                event_date.append(date)
            else:
                day = tomorrow_date_time.strftime("%a")
                event_day.append(day)
                date = tomorrow_date_time.strftime("%b")+ " " + tomorrow_date_time.strftime("%d")
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
    event_brite_state_url: string
        i.e. https://www.eventbrite.com/d/united-states--michigan/all-events/
    event_crawling_numbers: int
        i.e. 52 (state_event_crawling_numbers)
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
        user's city

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
        # Because sometimes there are not 1000 restaurants in a city, the response may retrun 'error' key
        # instead of 'businesses' key. To prevent this, check if there is a 'business' key to exclude to append
        # error data
        if 'businesses' in response.keys():
            result_business = response['businesses']
            for item in result_business:
                total_result.append(item)

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
    offset_num =[]

    count = 0
    while count <= 950:
        offset_num.append(count)
        count += 50

    return offset_num


def get_cities_name(state_name):
    '''Get a cities list in a state.

    Parameters
    ----------
    state_name: string
        name of the state (two character)
        i.e. MI

    Returns
    -------
    list
        a list of lower cased cities names in the state
    '''
    cities_list = []

    file_contents = open(US_CITIES,'r')
    file_reader = csv.reader(file_contents)

    # Headers: "city","city_ascii","state_id","state_name","county_fips","county_name","county_fips_all","county_name_all","lat","lng",
    # "population","density","source","military","incorporated","timezone","ranking","zips","id"
    # i.e. Records: "South Creek","South Creek","WA","Washington","53053","Pierce","53053","Pierce","46.9994","-122.3921",
    # "2500","125","polygon","FALSE","TRUE","America/Los_Angeles","3","98580 98387 98338","1840042075"

    # Skip header row
    next(file_contents)

    for city_data in file_reader:
        if city_data[2] == state_name:
            # Get Lowered City Name (i.e. detroit, ann arbor)
            cities_list.append(city_data[0].lower())

    return cities_list


'''
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

    headers: dictionary
        A dictionary of headers
        i.e. headers = {'Authorization': f'Bearer {YELP_API_KEY}'}

    Returns
    -------
    dictionary
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
    '''Check the cache for a saved result for this baseurl+params+headers
    combo. If the result is found, return it. Otherwise send a new
    request, save it, then return it.

    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint

    params: dictionary
        A dictionary of param: param_value pairs

    headers: dictionary
        A dictionary of headers
        i.e. headers = {'Authorization': f'Bearer {YELP_API_KEY}'}

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
        CACHE_DICT[request_key] = make_request(baseurl, params, headers)
        save_cache(CACHE_DICT)
        return CACHE_DICT[request_key]


'''
Part 4 Database Access and Storage
'''
# Create Tables
def create_db():
    '''Create three tables (Locations, Events, and Restaurnts) in the database.

    Parameters
    ----------
    None

    Returns
    -------
    None
    '''
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
            "EventName" TEXT NOT NULL,
            "Day" TEXT,
            "Date" TEXT,
            "Time" TEXT,
            "LocationId" INTEGER
        )
    '''

    create_restaurants_sql = '''
        CREATE TABLE IF NOT EXISTS "Restaurants"(
            "RestaurantId" TEXT PRIMARY KEY,
            "RestaurantName" TEXT NOT NULL,
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
    Get cities data from uscities.csv, process data, and put the processed data into the Database.

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
    '''Insert data into the Dabatabe.
    Process event data retrieved from crawled & scraped website, and put the processed data into the Database.

    Parameters
    ----------
    events_list: list
        a list of state event dictionaries
        i.e. michigan_all_events -> a list of dictionaries of all michigan events
        i.e. [{'event_name': 'Drag Queen Bingo - Bus Stop Bar and Grille', 'event_location': 
        'The Bus Stop Bar & Grille', 'event_city': ' Birch Run', 'event_state': 'MI', 
        'event_day': 'Thu', 'event_date': 'Apr 16', 'event_time': '8:00 PM'}]

    Returns
    -------
    None
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
    '''Insert data into the Dabatabe.
    Process restaurnat data retrieved from Yelp Fusion API, and put the processed data into the Database.

    Parameters
    ----------
    restaurant_list: list
        a list of dictionaries of a user's city restaurant information
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

    a_city: string
        name of the city (i.e. detroit, ann arbor)

    Returns
    -------
    None
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

    '''
    Check if a user searches the city before and the database has one.
    (If I don't check it, the application crashes when the user checks the same city again.)
    '''

    q = '''
        SELECT Locations.City
        FROM Restaurants
        JOIN Locations
        ON Restaurants.LocationId = Locations.Id
    '''

    result_q = cur.execute(q).fetchall()
    # i.e. result_q: [('Detroit',), ('Detroit',), ('Detroit',), ('Detroit',), ('Detroit',), ('Detroit',), 
    # ('Detroit',), ('Detroit',), ('Detroit',), ('Detroit',), ('Detroit',), ('Detroit',), 
    # ('Detroit',), ('Detroit',), ('Detroit',), ('Detroit',),…]

    condition_check = 0

    # For the first time use, there will be empty item in result_q. For that case, just skip "for a_tuple in result_q:" iterataion
    # and go to "if condition_check == 0: for row in restaurant_list:"
    if result_q:
        for a_tuple in result_q:
            if a_city != a_tuple[0].lower():
                pass
            else:
                condition_check += 1

    if condition_check == 0:
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
    else:
        conn.commit()
        conn.close()


'''
Part 5: Data Processing
'''
# Restaurant Query
def restaurants_query_process(a_city, data_selection):
    '''Process restaurants query and return result as a list of tuple(s)

    Parameters
    ----------
    a_city: string (lower case)
        name of a city (i.e. detroit, ann arbor)

    data_selection: string
        name of the data selection
        (i.e. total_number_of_restaurants, average_restaurant_rating)

    Returns
    -------
    list
        result as a list of tuple(s)
        # i.e. [(696, 'Detroit')] <= Total Restaurants numbers in Detroit
        # i.e. [(3.9331896551724137, 'Detroit')] <= Average Rating in Detroit
    '''
    a_city_capital = capitalize_city_name(a_city)

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    if data_selection == 'total_number_of_restaurants':
        select_item = 'COUNT(*)'
    else:
        select_item = 'AVG(Restaurants.Rating)'

    query = f'''
        SELECT {select_item}, Locations.City
        FROM Restaurants
        JOIN Locations
        ON Restaurants.LocationId = Locations.Id
        WHERE Locations.City = "{a_city_capital}"
    '''

    print(f"SQL Query: {query}")

    cur.execute(query)
    result = cur.fetchall()

    conn.close()

    return result


# Events Query
def events_query_process(a_city, data_selection):
    '''Process event query and return result as a list of tuple(s)

    Parameters
    ----------
    a_city: string (lower case)
        name of a city (i.e. detroit, ann arbor)

    data_selection: string
        name of the data selection
        (i.e. total_number_of_events, total_number_of_events_on_weekend, total_number_of_events_on_weekday)

    Returns
    -------
    list
        result as a list of tuple(s)
        # i.e. [(180, 'Detroit')] <= Total Events numbers in Detroit
    '''
    a_city_capital = capitalize_city_name(a_city)

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    if data_selection == 'total_number_of_events':
        where_item = ""
    elif data_selection == 'total_number_of_events_on_weekend':
        where_item = 'AND (Events.Day = "Sat" or Events.Day = "Sun")'
    else:
        where_item  = 'AND (Events.Day != "Sat" AND Events.Day != "Sun")'

    query = f'''
        SELECT COUNT(*), Locations.City
        FROM Events
        JOIN Locations
        ON Events.LocationId = Locations.Id
        WHERE Locations.City = "{a_city_capital}" {where_item}
    '''

    print(f"SQL Query: {query}")

    cur.execute(query)
    result = cur.fetchall()

    conn.close()

    return result

# Assistive function to capitalize city name
def capitalize_city_name(a_city):
    '''Make city name capitalized.

    Parameters
    ----------
    a_city: string (lower case)
        name of a city (i.e. detroit, ann arbor)

    Returns
    -------
    string
        capitalized city name
        # i.e. (i.e. Detroit, Ann Arbor)
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



# Configure float formatting
def float_formatting(float_number):
    '''Configure flot numbers digits to one decimal.
    i.e. 3.9331896551724137 to 3.9

    Parameters
    ----------
    float_number: float
        float number

    Returns
    -------
    float
        formatted float number to one decimal
        (i.e 3.9)
    '''
    float_formatted = "{:.1f}".format(float_number)

    return float_formatted


'''
Part 6: Data Presentation (Flask and Plotly)
'''
# app -> defined on the top
# Home page
@app.route('/')
def index():
    ''' Control home page and return index.html template.

    Parameters
    ----------
    None

    Returns
    -------
    html template
        return index.html template
    '''
    # Clear user_city list so that it can take new one every time.
    user_city.clear()
    return render_template('index.html')

# Options Page
@app.route('/options', methods=['POST'])
def options():
    ''' Control options page and return 'options.html' template or 'error.html' tempate
    if there's an error with parameters.

    Parameters
    ----------
    None

    Returns
    -------
    html template
        return 'options.html' template or 'error.html' template if there's an error with user_city
        parameter.
    '''
    mi_cities_lowered = get_cities_name("MI")
    # mi_cities_lowered -> a list of MI chities lowered (i.e. ann arbor, lansing)
    user_input = request.form['city_input']
    user_input_lower = user_input.lower()

    # user_city (list) was defined on the top so that other function can use it too.
    user_city.append(capitalize_city_name(user_input))

    if user_input_lower in mi_cities_lowered:
        return render_template('options.html', user_city=user_city[0])
    else:
        return render_template('error.html', user_city=user_city[0])

# Category Page
@app.route('/category', methods=['POST'])
def category():
    ''' Control category page and return 'category.html' template with parameters.

    Parameters
    ----------
    None

    Returns
    -------
    html template with parameters
        return 'category.html' template with category and category_capitalize parameters.
    '''
    # category is either "events" or "restaurants"
    category = request.form['category_compare']

    # For category url (events)
    category_capitalize = category.capitalize()

    return render_template('category.html', category=category, category_capitalize=category_capitalize)

# Results Page
@app.route('/category/<category>/results', methods=['POST'])
def results(category):
    ''' Control results page and return 'results.html' template with parameters.
    If "barplot" was checked on the category page, the results page will show a bar graph from Plotly.
    If it was not checked, the results page will display a table instead.

    Parameters
    ----------
    category: string
        category name (either "events" or "restaurants")

    Returns
    -------
    html template
        return 'results.html' template with parameters.
    '''
    data_selection = request.form['category_radio']
    data_selection_split = data_selection.split('_')

    data_selection_configured = ''

    user_city_results = user_city[0]
    user_city_results_lower = user_city_results.lower()

    # Convert data_selection i.e. "total_number_of_restaurants" to "Total Number Of Restaurants"
    for i in range(len(data_selection_split)):
        if i < (len(data_selection_split)-1):
            data_selection_configured += data_selection_split[i].capitalize() + " "
        else:
            data_selection_configured += data_selection_split[i].capitalize()

    # Restaurants
    if data_selection == 'total_number_of_restaurants' or data_selection == 'average_restaurant_rating':
        '''
        Detroit's City's Restaurant (# Get Detroit's Restaurant information and put it to the DB)
        => should be already done in the main section.
        '''

        '''
        User's City's Restaurant
        '''
        # Get User's City's Restaurant information and put it to the DB
        user_city_restaurants = get_restaurant_information(user_city_results_lower)
        load_restaurants(user_city_restaurants, user_city_results_lower)

        '''
        Results of Restaurants
        '''
        # Result exmaple
        # i.e. Total Restaurants numbers in Detroit: [(696, 'Detroit')]
        # i.e. Average Rating in Detroit: [(3.9331896551724137, 'Detroit')]
        detroit_result = restaurants_query_process('detroit', data_selection)[0][0]
        user_result = restaurants_query_process(user_city_results_lower, data_selection)[0][0]

        if type(detroit_result) is float:
            detroit_result = float_formatting(detroit_result)
        if type(user_result) is float:
            user_result = float_formatting(user_result)

    # Events
    else:
        '''
        Events Crawling and Scraping should be already done in the main section.
        '''

        '''
        Results of Events
        '''
        # Result exmaple
        # i.e. Total Events numbers in Detroit: [(180, 'Detroit')]
        detroit_result = events_query_process('detroit', data_selection)[0][0]
        user_result = events_query_process(user_city_results_lower, data_selection)[0][0]

    # barplot -> True or False
    barplot = 'barplot' in request.form.keys()

    if barplot:
        x_axis = [user_city_results, 'Detroit']
        y_axis = [user_result, detroit_result]

        barplot_data = go.Bar(x=x_axis, y=y_axis)
        basic_layout = go.Layout(title=f"{data_selection_configured}: {user_city_results} v.s. Detroit")
        fig = go.Figure(data=barplot_data, layout=basic_layout)

        div = fig.to_html(full_html=False)

        return render_template('results.html', data_selection=data_selection_configured, barplot=barplot, plot_div=div)

    else:
        return render_template('results.html', 
        user_city=user_city_results, 
        data_selection=data_selection_configured,
        detroit_result=detroit_result,
        user_result=user_result,
        barplot=barplot
        )


if __name__ == "__main__":
    '''
    Part 4: Database Accessing
    '''
    # Create the database tables
    create_db()
    # Insert Cities Data to the database
    load_locations()

    '''
    Part 2: Caching
    '''
    # Use Cache
    CACHE_DICT = open_cache()

    '''
    Part 4 Database Access and Storage - Michigan Events Data and Detroit Restaurant Data
    Need to retrieve & configure Michigan Events Data and Detroit Restaurant Data before a user enters
    his/her city in MI.
    '''
    '''
    Events in Michigan
    '''
    crawl_event_pages(MICHIGAN_EVENT_URL, state_event_crawling_numbers)

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

    print(f"total # of michigan events data: {len(michigan_all_events)}")

    # Insert Michigan State Events records to the database
    load_events(michigan_all_events)

    '''
    Detroit's City's Restaurant
    '''
    # Insert Detroit Restaurants records to the database
    detroit_restaurants = get_restaurant_information("detroit")
    print(f"total # of restaurants in detroit + near detroit raw data: {len(detroit_restaurants)}")
    load_restaurants(detroit_restaurants, "detroit")

    '''
    Part 6 Data Presentation
    '''
    app.run(debug=False)