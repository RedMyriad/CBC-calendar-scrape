from __future__ import print_function
import httplib2
import os
import warnings
import tzlocal

from bs4 import BeautifulSoup
from urllib import request
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage


import datetime

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Cbc Calendar Scrape'
CBC_MAIN_URL = 'https://www.columbiabasin.edu/'
CALENDAR_PAGE_URL = 'https://www.columbiabasin.edu/index.aspx?page=371'
TIME_ZONE = tzlocal.get_localzone()

def get_credentials(cred_dir, cred_path):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, cred_dir)
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   cred_path)
    store = Storage(credential_path)
    # code: Francisco Lopez
    with warnings.catch_warnings():

        warnings.simplefilter('ignore')
        credentials = store.get()
    # code end

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

# code: Francisco Lopez
def open_client(url):
    client = request.Request(url)
    cbc_req = request.urlopen(client)
    page = cbc_req.read()
    cbc_req.close()

    return page
# code end


# code: Francisco Lopez
def get_cal_data(page):
    page_soup = BeautifulSoup(page, 'html.parser')
    half_events1 = page_soup.find_all('td', {'class', 'calendar_day'})
    half_events2 = page_soup.find_all('td', {'class', 'calendar_weekendday'})
    month_events = []
    month_events.extend(half_events1)
    month_events.extend(half_events2)

    all_events = []
    for day_events in month_events:
        event_links = day_events.find_all('a', {'class', 'calendar_eventlink'})
        extracted_links = []
        for link in event_links:
            attributes = link.attrs
            extracted_links.append(attributes['href'])
        for link in extracted_links:
            link = CBC_MAIN_URL + '/' + link
            linked_page = open_client(link)
            event_soup = BeautifulSoup(linked_page, 'html.parser')

            content = event_soup.find('div', {'class', 'content'})
            title = content.find('span', {'id': 'ctl00_titleLabel'})
            sub_title = content.find('span', {'id': 'ctl00_subtitleLabel'})
            date = content.find('span', {'id': 'ctl00_timeLabel'})
            cost = content.find('span', {'id': 'ctl00_costLabel'})
            location = content.find('span', {'id': 'ctl00_locationLabel'})
            room = content.find('span', {'id': 'ctl00_roomnumlabel'})
            campus = content.find('span', {'id': 'ctl00_campuslabel'})
            description = content.find('span', {'id': 'ctl00_descriptionLabel'})

            cal_values = [title, sub_title, date, cost, location, room, campus, description]
            for value in cal_values:
                if value is None:
                    value_temp = 'Not Applicable'
                    cal_values[cal_values.index(value)] = value_temp
                else:
                    cal_values[cal_values.index(value)] = value.text

            title = cal_values[0]
            sub_title = cal_values[1]
            date = cal_values[2]
            cost = cal_values[3]
            location = cal_values[4]
            room = cal_values[5]
            campus = cal_values[6]
            description = cal_values[7]

            temp = ''
            previous = ''
            for i in list(location):
                i = str(i)
                if i.isupper() or i.isnumeric():
                    if previous.islower() and i.isupper():
                        temp = temp + ' ' + i
                    elif previous.isalpha() and i.isnumeric():
                        temp = temp + ' ' + i
                    else:
                        temp += i
                else:
                    temp += i
                previous = i
            location = temp

            description = sub_title + '\n' + 'Room: ' + room + '\n' + 'Cost: ' + cost + '\n' + 'Date: ' + date + '\n' + description

            if date != 'Not Applicable':
                temp = ''
                date_fixed = True
                for i in list(date):
                    if i != ' ' and date_fixed is True:
                        if i == '/':
                            temp += '-'
                        else:
                            temp += i
                    else:
                        break

                temp = temp.split('-')
                temp.reverse()
                date = temp[1]
                temp[1] = temp[2]
                temp[2] = date

                date = ''
                count = 0

                for i in temp:
                    count += 1
                    if count < 3:
                        date += i + '-'
                    else:
                        date += i

            events_dict = {'summary': title, 'date': date, 'location': location, 'description': description}
            all_events.append(events_dict)
    return all_events
# code end


def main():

    # code: Francisco Lopez
    cred_dir = '.credentials'
    cred_path = cred_path = 'calendar-python-quickstart.json'
    save_account = input('Would you like to always use the same account?(y/n) ')
    save_account = save_account.lower()
    # code end


    # code: Francisco Lopez
    cal_page = open_client(CALENDAR_PAGE_URL)
    all_events = get_cal_data(cal_page)
    # code end

    credentials = get_credentials(cred_dir, cred_path)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    for event in all_events:
        event = {
            'summary': event['summary'],
            'location': event['location'],
            'description': event['description'],
            'start': {
                'dateTime': event['date'] + 'T09:00:00-07:00',
                'timeZone': str(TIME_ZONE),
            },
            'end': {
                'dateTime': event['date'] + 'T15:00:00-07:00',
                'timeZone': str(TIME_ZONE),
            },
            'recurrence': [
                'RRULE:FREQ=DAILY;COUNT=1'
            ],
            'attendees': [
            ],
            'reminders': {
                'useDefault': True,
            },
        }
        event = service.events().insert(calendarId='primary', body=event).execute()

    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    eventsResult = service.events().list(
        calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])

    # code: Francisco Lopez
    if save_account != 'y':
        full_path = os.path.join(os.path.expanduser('~'), cred_dir) + '\\' + cred_path
        print(full_path)
        os.remove(full_path)
        os.rmdir(os.path.join(os.path.expanduser('~'), cred_dir))
    # code end


if __name__ == '__main__':
    main()