import streamlit as st
from msal import PublicClientApplication
import requests, json
from datetime import datetime, timedelta
import random


def fetch_prayer_times(date, country, city, add_for):
    if add_for == "Month":
        response = requests.get(f"https://api.aladhan.com/v1/calendarByCity/{date.year}/{date.month}", 
                                params={'city': city,
                                        'country': country})

        prayer_times = response.json()['data']
        filtered_dates = [prayer_time for prayer_time in prayer_times
                        if datetime.strptime(prayer_time['date']['gregorian']['date'], "%d-%m-%Y").date() >= date]


    elif add_for == "Year":
        response = requests.get(f"https://api.aladhan.com/v1/calendarByCity/{date.year}", 
                                params={'city': city,
                                        'country': country})

        prayer_times = response.json()['data']
        filtered_dates = [time for _, times in prayer_times.items() for time in times
                        if datetime.strptime(time['date']['gregorian']['date'], "%d-%m-%Y").date() >= date]
        
    return filtered_dates
    

def authenticate():
    CLIENT_ID         = "dc019d2f-56b2-493b-9b80-87ec157b1e3a"
    # TENANT_ID         = "f081ce87-83ce-4726-bea5-783eaa04fdfc"
    # authority_url     = f'https://login.microsoftonline.com/{TENANT_ID}'


    app = PublicClientApplication(CLIENT_ID,
                                authority="https://login.microsoftonline.com/common")

    # initialize result variable to hole the token response
    result = None 

    # We now check the cache to see
    # whether we already have some accounts that the end user already used to sign in before.
    accounts = app.get_accounts()
    if accounts:
        # If so, you could then somehow display these accounts and let end user choose
        print("Pick the account you want to use to proceed:")
        for a in accounts:
            print(a["username"])
        # Assuming the end user chose this one
        chosen = accounts[0]
        # Now let's try to find a token in cache for this account
        result = app.acquire_token_silent(["User.Read", "Calendars.ReadWrite"], account=chosen)


    if not result:
    # So no suitable token exists in cache. Let's get a new one from Azure AD.
        result = app.acquire_token_interactive(scopes=["User.Read", 'Calendars.ReadWrite'])

        if 'access_token' in result:
            return result['access_token']
        else:
            st.error("Authentication failed.")
            return None

# Function to send batch request
def send_batch_create(batch_meetings, access_token):
    # Prepare batch requests (maximum 20 per batch)
    batch_requests = []
    for i, meeting in enumerate(batch_meetings):
        request = {
            "id": str(i),  # Unique ID for each request in the batch
            "method": "POST",
            "url": "/me/events",
            "headers": {
                "Content-Type": "application/json"
            },
            "body": meeting
        }
        batch_requests.append(request)

    # Create batch body
    batch_body = {
        "requests": batch_requests
    }

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Microsoft Graph API endpoint for batch requests
    batch_url = 'https://graph.microsoft.com/v1.0/$batch'

    # Send batch request
    response = requests.post(batch_url, headers=headers, data=json.dumps(batch_body))

    # Check the response
    if response.status_code == 200:
        batch_response = response.json()
        for sub_response in batch_response['responses']:
            if sub_response['status'] == 201:
                print(f"Meeting created successfully with ID: {sub_response['body']['id']}")
            else:
                print(f"Failed to create meeting with status: {sub_response['status']}")
    else:
        print(f"Batch request failed with status: {response.status_code}")
        print(response.json())


def add_prayers_to_calendar(access_token, dates_data, minutes_between, meeting_color):
    meetings = []

    hadithes = [
    "قال رسول الله -صلى الله عليه وسلم-: (فضلُ الجماعَةِ علَى صلاةِ أحدِكُم وحدَهُ خمسٌ وَعِشرونَ جُزءًا).",
    "قال رسول الله -صلى الله عليه وسلم-: (صَلَاةُ الجَمَاعَةِ تَفْضُلُ صَلَاةَ الفَذِّ بسَبْعٍ وعِشْرِينَ دَرَجَةً).",
    "قال رسول الله -صلى الله عليه وسلم-: (ما مِن ثلاثةٍ في قريةٍ ولا بدوٍ لا تقامُ فيهمُ الصَّلاةُ إلَّا قدِ استحوذَ عليْهمُ الشَّيطانُ فعليْكم بالجماعةِ فإنَّما يأْكلُ الذِّئبُ القاصيةَ)",
    "قال رسول الله -صلى الله عليه وسلم-: (مَن خرجَ من بيتِه متطَهرًا إلى صلاةٍ مَكتوبةٍ فأجرُه كأجرِ الحاجِّ المحرمِ ومَن خرجَ إلى تسبيحِ الضُّحى لا ينصبُه إلَّا إيَّاهُ فأجرُه كأجرِ المعتمرِ وصلاةٌ علَى أثرِ صلاةٍ لا لغوَ بينَهما كتابٌ في علِّيِّينَ)",
    "عن أبي هريرة -رضي الله عنه- قال: (أَتَى النبيَّ صَلَّى اللَّهُ عليه وسلَّمَ رَجُلٌ أَعْمَى، فَقالَ: يا رَسولَ اللهِ، إنَّه ليسَ لي قَائِدٌ يَقُودُنِي إلى المَسْجِدِ، فَسَأَلَ رَسولَ اللهِ صَلَّى اللَّهُ عليه وسلَّمَ أَنْ يُرَخِّصَ له، فيُصَلِّيَ في بَيْتِهِ، فَرَخَّصَ له، فَلَمَّا وَلَّى، دَعَاهُ، فَقالَ: هلْ تَسْمَعُ النِّدَاءَ بالصَّلَاةِ؟ قالَ: نَعَمْ، قالَ: فأجِبْ).",
    "عن عبد الله بن مسعود -رضي الله عنه- قال: (لقَدْ رَأَيْتُنَا وَما يَتَخَلَّفُ عَنِ الصَّلَاةِ إلَّا مُنَافِقٌ قدْ عُلِمَ نِفَاقُهُ، أَوْ مَرِيضٌ، إنْ كانَ المَرِيضُ لَيَمْشِي بيْنَ رَجُلَيْنِ حتَّى يَأْتِيَ الصَّلَاةِ، وَقالَ: إنْ رَسولَ اللهِ صَلَّى اللَّهُ عليه وسلَّمَ عَلَّمَنَا سُنَنَ الهُدَى، وإنَّ مِن سُنَنَ الهُدَى الصَّلَاةَ في المَسْجِدِ الذي يُؤَذَّنُ فِيهِ).",
    "قال رسول الله -صلى الله عليه وسلم-: (لقَدْ هَمَمْتُ أنْ آمُرَ بالصَّلاةِ فَتُقامَ، ثُمَّ أُخالِفَ إلى مَنازِلِ قَوْمٍ لا يَشْهَدُونَ الصَّلاةَ، فَأُحَرِّقَ عليهم).",
    "قال رسول الله -صلى الله عليه وسلم-: (مَن غَدَا إلى المَسْجِدِ ورَاحَ، أعَدَّ اللَّهُ له نُزُلَهُ مِنَ الجَنَّةِ كُلَّما غَدَا أوْ رَاحَ)."
]

    for prayer_times in dates_data:
        date = prayer_times['date']['gregorian']['date']
        timezone = prayer_times['meta']['timezone']

        for i, (prayer_name, prayer_time) in enumerate(prayer_times['timings'].items()):
            if prayer_name in ['Fajr', 'Asr', 'Dhuhr', 'Maghrib', 'Isha']:
                start_datetime  = datetime.strptime(f"{date} {prayer_time[:5]}", "%d-%m-%Y %H:%M")
                end_date_time   = (start_datetime + timedelta(minutes=minutes_between)).isoformat() # Add time in between
                start_date_time = start_datetime.isoformat()

                event_data = {
                    "subject": f"{prayer_name} Prayer [{timezone}]",
                    "body": {
                        "contentType": "HTML",
                        "content": random.choice(hadithes)
                    },
                    "start": {
                        "dateTime": start_date_time,
                        "timeZone": timezone
                    },
                    "end": {
                        "dateTime": end_date_time,
                        "timeZone": timezone
                    },
                    "location": {
                        "displayName": "Mosque"
                    },
                    "attendees": [],
                    "showAs": "busy",
                    "categories": [f"{meeting_color.split(' ')[-1]} category"]  
                }
                meetings.append(event_data)


    # Split meetings into batches of 20
    batch_size = 20
    for i in range(0, len(meetings), batch_size):
        batch_meetings = meetings[i:i+batch_size]  # Get the next batch of 20 meetings
        print(f"Creating batch {i // batch_size + 1} of {batch_size} meetings...")
        send_batch_create(batch_meetings, access_token=access_token)  # Send batch create request for this chunk
    

def send_batch_delete(event_ids, access_token):
    # Microsoft Graph API batch endpoint
    batch_url = 'https://graph.microsoft.com/v1.0/$batch'
    
    # Prepare batch delete requests (maximum 20 per batch)
    batch_requests = []
    for i, event_id in enumerate(event_ids):
        request = {
            "id": str(i),  # Unique ID for each request in the batch
            "method": "DELETE",
            "url": f"/me/events/{event_id}"
        }
        batch_requests.append(request)
    
    # Create batch body
    batch_body = {
        "requests": batch_requests
    }

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Send batch request
    delete_response = requests.post(batch_url, headers=headers, data=json.dumps(batch_body))

    # Check the response
    if delete_response.status_code == 200:
        batch_response = delete_response.json()
        for sub_response in batch_response['responses']:
            if sub_response['status'] == 204:
                print(f"Successfully deleted event with ID: {sub_response['id']}")
            else:
                print(f"Failed to delete event with ID: {sub_response['id']}, status: {sub_response['status']}")
    else:
        print(f"Batch delete request failed with status: {delete_response.status_code}")
        print(delete_response.json())

def get_all_events(url, headers):
    events = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            events.extend(data.get('value', []))
            url = data.get('@odata.nextLink')  # Get the next page URL if there is more data
        else:
            print(f"Error fetching events: {response.status_code}")
            break
    return events


def delete_prayers_from_calendar(access_token):
    # Define the prayer name you're looking for
    event_name = "Prayer"

    # Microsoft Graph API endpoint to search for events by subject
    search_url = f'https://graph.microsoft.com/v1.0/me/events?$filter=contains(subject,\'{event_name}\')'

    # Set up the headers with the access token
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    events = get_all_events(search_url, headers)
    print(f"Got [{len(events)}] prayer meetings.")

    if len(events) == 0:
        print(f"No events found with '{event_name}' in the subject.")
    else:
        event_ids = [event['id'] for event in events]

        batch_size = 20
        for i in range(0, len(event_ids), batch_size):
            batch_event_ids = event_ids[i:i+batch_size]  # Get the next batch of 20 or fewer
            print(f"Deleting batch of {len(batch_event_ids)} events...")
            send_batch_delete(batch_event_ids, access_token=access_token)  # Send batch delete request for this chunk


country_city_map = {
    'Egypt': ['Cairo', 'Alexandria', 'Giza', 'Sharm El Sheikh', 'Luxor', 'Aswan', 'Port Said', 'Suez', 'Tanta', 'Ismailia'],
    'Saudi Arabia': ['Riyadh', 'Jeddah', 'Mecca', 'Medina', 'Dhahran', 'Khobar', 'Dammam', 'Najran', 'Abha', 'Hail'],
    'United Arab Emirates': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Ras al-Khaimah', 'Fujairah', 'Umm al-Quwain', 'Al Ain', 'Khor Fakkan', 'Kalba'],
    'Jordan': ['Amman', 'Zarqa', 'Irbid', 'Aqaba', 'Madaba', 'Karak', 'Mafraq', 'Salt', 'Ajloun', 'Jerash'],
    'Lebanon': ['Beirut', 'Tripoli', 'Sidon', 'Tyre', 'Jounieh', 'Zahle', 'Batroun', 'Baalbek', 'Nabatieh', 'Byblos'],
    'Syria': ['Damascus', 'Aleppo', 'Homs', 'Latakia', 'Hama', 'Deir ez-Zor', 'Raqqa', 'Qamishli', 'Daraa', 'Tartus'],
    'Iraq': ['Baghdad', 'Basra', 'Mosul', 'Erbil', 'Kirkuk', 'Najaf', 'Kufa', 'Sulaymaniyah', 'Duhok', 'Ramadi'],
    'Kuwait': ['Kuwait City', 'Hawalli', 'Salmiya', 'Jahra', 'Ahmadi', 'Farwaniya', 'Mubarak Al-Kabeer', 'Sabah Al-Salem', 'Shuwaikh', 'Shamiya'],
    'Qatar': ['Doha', 'Al Wakrah', 'Al Khor', 'Messaieed', 'Umm Salal', 'Al Rayyan', 'Lusail', 'Madinat ash Shamal', 'Al Shamal', 'Zubara'],
    'Bahrain': ['Manama', 'Riffa', 'Muharraq', 'Hamad Town', 'Sitra', 'Budaiya', 'Aali', 'Juffair', 'Isa Town', 'Sanabis'],
    'Oman': ['Muscat', 'Salalah', 'Sohar', 'Nizwa', 'Sur', 'Ibra', 'Buraimi', 'Khasab', 'Ruwi', 'Saham'],
    'Yemen': ['Sanaa', 'Aden', 'Taiz', 'Hodeidah', 'Ibb', 'Dhamar', 'Mukalla', 'Al Hudaydah', 'Rada', 'Al Bayda'],
    'Libya': ['Tripoli', 'Benghazi', 'Misrata', 'Sebha', 'Zintan', 'Al Khums', 'Tobruk', 'Derna', 'Sirt', 'Ajdabiya'],
    'Algeria': ['Algiers', 'Oran', 'Constantine', 'Annaba', 'Blida', 'Batna', 'Setif', 'Tlemcen', 'Ouargla', 'Bejaia'],
    'Morocco': ['Casablanca', 'Rabat', 'Marrakech', 'Fes', 'Tangier', 'Agadir', 'Oujda', 'Taza', 'Meknes', 'El Jadida'],
    'Tunisia': ['Tunis', 'Sfax', 'Sousse', 'Kairouan', 'Bizerte', 'Gabes', 'Medenine', 'Tataouine', 'Mahdia', 'Nabeul'],
    'Mauritania': ['Nouakchott', 'Nouadhibou', 'Rosso', 'Kiffa', 'Atar', 'Tidjikja', 'Aleg', 'Boutilimit', 'Zouérat', 'Ksar'],
    'Palestine': ['Ramallah', 'Gaza City', 'Hebron', 'Nablus', 'Jericho', 'Bethlehem', 'Qalqilya', 'Jenin', 'Salfit', 'Tulkarem'],
    'Somalia': ['Mogadishu', 'Hargeisa', 'Bosaso', 'Kismayo', 'Baidoa', 'Galkayo', 'Berbera', 'Burao', 'Jowhar', 'Las Anod'],
    'Sudan': ['Khartoum', 'Omdurman', 'Port Sudan', 'Nyala', 'Kassala', 'Wad Madani', 'Dongola', 'El Obeid', 'Sennar', 'Juba'],
    'USA': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose'],
    'Canada': ['Toronto', 'Vancouver', 'Montreal', 'Calgary', 'Edmonton', 'Ottawa', 'Quebec City', 'Winnipeg', 'Hamilton', 'Kitchener'],
    'UK': ['London', 'Manchester', 'Birmingham', 'Glasgow', 'Liverpool', 'Edinburgh', 'Leeds', 'Sheffield', 'Bristol', 'Newcastle'],
    'Australia': ['Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide', 'Gold Coast', 'Canberra', 'Hobart', 'Darwin', 'Cairns'],
    'Germany': ['Berlin', 'Munich', 'Hamburg', 'Frankfurt', 'Cologne', 'Stuttgart', 'Dusseldorf', 'Dortmund', 'Essen', 'Leipzig'],
    'France': ['Paris', 'Marseille', 'Lyon', 'Toulouse', 'Nice', 'Nantes', 'Montpellier', 'Strasbourg', 'Bordeaux', 'Lille'],
    'Italy': ['Rome', 'Milan', 'Naples', 'Turin', 'Palermo', 'Genoa', 'Bologna', 'Florence', 'Catania', 'Venice'],
    'Spain': ['Madrid', 'Barcelona', 'Valencia', 'Seville', 'Zaragoza', 'Malaga', 'Murcia', 'Palma', 'Bilbao', 'Alicante'],
    'Mexico': ['Mexico City', 'Guadalajara', 'Monterrey', 'Puebla', 'Cancun', 'Merida', 'Tijuana', 'San Luis Potosi', 'Leon', 'Ciudad Juarez'],
    'Brazil': ['Sao Paulo', 'Rio de Janeiro', 'Salvador', 'Fortaleza', 'Belo Horizonte', 'Brasilia', 'Manaus', 'Curitiba', 'Recife', 'Porto Alegre'],
    'Argentina': ['Buenos Aires', 'Cordoba', 'Rosario', 'Mendoza', 'La Plata', 'San Miguel de Tucuman', 'Salta', 'Santa Fe', 'San Juan', 'San Salvador de Jujuy'],
    'Chile': ['Santiago', 'Valparaiso', 'Concepcion', 'La Serena', 'Temuco', 'Rancagua', 'Antofagasta', 'Iquique', 'Puerto Montt', 'Arica'],
    'Colombia': ['Bogota', 'Medellin', 'Cali', 'Barranquilla', 'Cartagena', 'Bucaramanga', 'Pereira', 'Santa Marta', 'Manizales', 'Cucuta'],
    'South Africa': ['Johannesburg', 'Cape Town', 'Durban', 'Pretoria', 'Port Elizabeth', 'Bloemfontein', 'East London', 'Polokwane', 'Nelspruit', 'George'],
    'India': ['New Delhi', 'Mumbai', 'Bangalore', 'Hyderabad', 'Ahmedabad', 'Chennai', 'Kolkata', 'Jaipur', 'Pune', 'Surat'],
    'China': ['Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen', 'Chengdu', 'Hong Kong', 'Nanjing', 'Wuhan', 'Hangzhou', 'Xi\'an'],
    'Japan': ['Tokyo', 'Osaka', 'Kyoto', 'Yokohama', 'Nagoya', 'Sapporo', 'Fukuoka', 'Kobe', 'Hiroshima', 'Sendai'],
    'South Korea': ['Seoul', 'Busan', 'Incheon', 'Daegu', 'Daejeon', 'Gwangju', 'Suwon', 'Ulsan', 'Jeonju', 'Jeju'],
    'Russia': ['Moscow', 'Saint Petersburg', 'Novosibirsk', 'Yekaterinburg', 'Nizhny Novgorod', 'Kazan', 'Chelyabinsk', 'Omsk', 'Rostov-on-Don', 'Ufa'],
    'Turkey': ['Istanbul', 'Ankara', 'Izmir', 'Bursa', 'Antalya', 'Adana', 'Gaziantep', 'Konya', 'Kayseri', 'Mersin'],
    'Nigeria': ['Lagos', 'Abuja', 'Port Harcourt', 'Kano', 'Ibadan', 'Benin City', 'Kaduna', 'Zaria', 'Aba', 'Ilorin'],
    'Kenya': ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', 'Kericho', 'Thika', 'Malindi', 'Garissa', 'Kitale'],
    'Vietnam': ['Hanoi', 'Ho Chi Minh City', 'Da Nang', 'Hai Phong', 'Hue', 'Can Tho', 'Nha Trang', 'Buon Ma Thuot', 'Vung Tau', 'Rach Gia'],
    'Thailand': ['Bangkok', 'Chiang Mai', 'Pattaya', 'Phuket', 'Hua Hin', 'Krabi', 'Nakhon Ratchasima', 'Udon Thani', 'Surat Thani', 'Chiang Rai'],
    'Malaysia': ['Kuala Lumpur', 'Penang', 'Johor Bahru', 'Kota Kinabalu', 'Kuching', 'Malacca', 'Ipoh', 'Alor Setar', 'Kuala Terengganu', 'Shah Alam'],
    'Singapore': ['Singapore'],
    'Philippines': ['Manila', 'Quezon City', 'Cebu City', 'Davao City', 'Zamboanga City', 'Taguig', 'Antipolo', 'Pasig', 'Makati', 'Cagayan de Oro'],
    'Indonesia': ['Jakarta', 'Surabaya', 'Bandung', 'Medan', 'Denpasar', 'Makassar', 'Yogyakarta', 'Semarang', 'Palembang', 'Batam'],
    'Pakistan': ['Karachi', 'Lahore', 'Islamabad', 'Faisalabad', 'Rawalpindi', 'Multan', 'Peshawar', 'Quetta', 'Sialkot', 'Gujranwala'],
    'Bangladesh': ['Dhaka', 'Chittagong', 'Khulna', 'Rajshahi', 'Sylhet', 'Barisal', 'Rangpur', 'Mymensingh', 'Jamalpur', 'Tangail'],
    'Sri Lanka': ['Colombo', 'Kandy', 'Galle', 'Jaffna', 'Negombo', 'Anuradhapura', 'Matara', 'Batticaloa', 'Trincomalee', 'Kalutara'],
    'Nepal': ['Kathmandu', 'Pokhara', 'Lalitpur', 'Biratnagar', 'Birgunj', 'Hetauda', 'Bharatpur', 'Janakpur', 'Dhangadhi', 'Itahari'],
    'Myanmar': ['Yangon', 'Mandalay', 'Naypyidaw', 'Bago', 'Taunggyi', 'Mawlamyine', 'Pathein', 'Sittwe', 'Kawthoung', 'Myitkyina'],
    'Cambodia': ['Phnom Penh', 'Siem Reap', 'Battambang', 'Sihanoukville', 'Kampong Cham', 'Kampong Speu', 'Kep', 'Koh Kong', 'Pursat', 'Ta Khmau'],
    'Laos': ['Vientiane', 'Luang Prabang', 'Pakse', 'Savannakhet', 'Xam Neua', 'Xieng Khouang', 'Vang Vieng', 'Vientiane Prefecture', 'Thakhek', 'Pakse'],
    'Brunei': ['Bandar Seri Begawan', 'Kuala Belait', 'Seria', 'Tutong', 'Bangar', 'Muara'],
    'Malawi': ['Lilongwe', 'Blantyre', 'Mzuzu', 'Zomba', 'Kasungu', 'Mangochi', 'Salima', 'Karonga', 'Chitipa', 'Ntchisi'],
    'Zambia': ['Lusaka', 'Ndola', 'Kitwe', 'Livingstone', 'Chingola', 'Mufulira', 'Kabwe', 'Solwezi', 'Chipata', 'Kasama'],
}


st.markdown("""
    <style>
    .title {
        text-align: center;
        font-size: 40px; /* Adjust as needed */
        font-weight: bold;
        color: black; /* Adjust the color as needed */
        padding-bottom: 10px
    }
    </style>
""", unsafe_allow_html=True)

# Create a centered title with HTML
st.markdown('<div class="title">🕌 Prayer Time Scheduler 🕌</div>', unsafe_allow_html=True)

with st.expander("Select Prayer Times"):
    # Get user input
    start_date = st.date_input('Start Date', datetime.today())
    country = st.selectbox('Country', list(country_city_map.keys()))   
    cities = country_city_map.get(country, [])
    city = st.selectbox('City', cities)
    color      = st.selectbox('Meeting Color', ['🔴 Red', '🟠 Orange', '🟡 Yellow', '🟢 Green', '🔵 Blue', '🟣 Purple'])
    period     = st.selectbox('Prayer Period (minutes)', [10, 15, 20, 30, 45])
    add_for    = st.selectbox('Add For', ['Month', 'Year'])

col1, col2 = st.columns([1, 1])

with col1:
    # Authenticate and create prayer times
    if st.button('Add Prayer Times to My Calendar'):
        with st.spinner('🚀 Adding prayers, please wait... ⌛'):
            if 'access_token' not in st.session_state or st.session_state['access_token'] is None:
                st.session_state['access_token'] = authenticate()

            if 'access_token' in st.session_state:
                delete_prayers_from_calendar(access_token=st.session_state['access_token'])
                prayer_times = fetch_prayer_times(date=start_date, country=country, city=city, add_for=add_for)
                add_prayers_to_calendar(st.session_state['access_token'], prayer_times, minutes_between=period, meeting_color=color)
        st.success('Prayers has been added successfully in your calendar!')

with col2:
    # Reset Button
    if st.button('Remove All Existing Prayer Meetings'):
        with st.spinner('🗑️ Processing, please wait... ⌛'):
            if 'access_token' not in st.session_state or st.session_state['access_token'] is None:
                st.session_state['access_token'] = authenticate()


            if 'access_token' in st.session_state:
                delete_prayers_from_calendar(access_token=st.session_state['access_token'])
        st.success('All prayer meetings have beed deleted successfully from your calendar!')

