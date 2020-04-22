# SI507 Final Project - City Compare Python Flask App
The goal of the application is to compare a user’s city in Michigan (i.e. Ann Arbor, Lansing, etc.) with Detroit city, the largest city in Michigan, by checking how each city’s restaurants are performing and what types of events are available for each city.
For example, the application will compare the average restaurant rating in the user’s city (i.e. Ann Arbor, Lansing, etc.) with the one in Detroit. Also, the application will check how many weekend events are available for each city and compare them.

## Getting Started

Before you run the application, I recommend you to check if you have installed python packages such as requests, bs4 (BeautifulSoup), flask (Flask, render_template, request), and plotly.
Also, please get an API key from <a href="https://www.yelp.com/developers/documentation/v3">Yelp Fusion API</a>. 

```
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request
import plotly.graph_objects as go
```

### Installing
Example (for Mac)

**requests**
```
pip3 install request
```

or

```
pip install request
```

**bs4** (for web scraping)
```
pip3 install bs4
```

or

```
pip install bs4
```

**flask**
```
pip3 install flask
```

or

```
pip install flask
```

**plotly**
```
pip3 install plotly
```

or

```
pip install plotly
```

### Yelp Fusion API
Please go to <a href="https://www.yelp.com/developers/documentation/v3">Yelp Fusion API</a> website and get an API key.
Once you get the API key from the Yelp Fusion API, please create a "secrets.py" file and add your API key with a variable name "YELP_API_KEY".
```
YELP_API_KEY = "your_yelp_fusion_api_key"
```

## Data Resources
There are three data resources used for the application: uscities.csv, Eventbrite website, and Yelp Fusion API.

### 1. uscities.csv
The US Cities data in a CSV file format was downloaded from <a href="https://simplemaps.com/data/us-cities">Simple Maps</a>. 
The US Cities data contains information of all cities in the US such as city name, state_name, county_name, latitude, longitude, population, density, zips, etc. 

### 2. Eventbrite Website
I crawled and scraped the <a href="https://www.eventbrite.com/d/united-states--michigan/all-events/">Eventbrite</a> website to get events information in Michigan. I especially used “requests” and “BeautifulSoup” techniques.


### 3. Yelp Fusion API
I got restaurant data for Detroit city and the user’s city in MI from <a href="https://www.yelp.com/developers/documentation/v3">Yelp Fusion API</a>. I got an API key from the Yelp Fusion API and used “requests” and “json” techniques to access data from Yelp Fusion API.

## Interaction and Presentation Options
** Before you run the application, please make sure that you have installed the required python packages listed on the top and added your Yelp Fusion API key in the secrets.py. Also, please make sure that you download every file on the GitHub.

The user can run the “city_comparing.py” on the terminal to run the Python Flask Application. Once the user runs it, the user can open it on a browser and will see a home page of the “City Compre (CC)” website. The steps (interactions) will be… 
- Step 1: Run the “city_comparing.py” application on the terminal. 
- Step 2: Open the Flask app "city_comparing" on a browser. 
- Step 3: (Home page) Type a city in Michigan. 
- Step 4: (Options page) Select a category (Events or Restaurants). 
- Step 5: (Category page) Select what data to compare and how to see it. 
- Step 6: (Results page) Display results in a table. If “Bar Graph” was checked in step 5, the user will see the result in a bar graph (from Plotly) instead.

The data options that the user can select in Step 5 is “Total Number of Events”, “Events Numbers on the Weekend”, and “Events Numbers on the Weekday” if the user chose “Events” in Step 4. If the user chose “Restaurants” in Step 4, the data options that the user can select in Step 5 will be “ Total Number of Restaurants” and “Average Restaurant Rating”. 
Each data will be displayed in a table or in a bar graph (from Plotly) if the user checked “Bar Graph” in Step 5. 

For more details with screenshots, please check <a href="https://docs.google.com/document/d/1RhOX70C15jaHq6I7sNvL7VkJ8ZQPwxbqJtbdodGX6To/edit#heading=h.ugpnrzo7khuz">here</a>.

