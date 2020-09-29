def get_html(site):
    r = requests.get(site)
    return r.text

def get_page_data(html):
    soup = BeautifulSoup(html, 'lxml')
    wall = soup.findAll('div', class_='wall_item')

    return str(wall)

def get_data():
    timeout = eventlet.Timeout(10)
    try:
        feed = requests.get(URL_VK)
        return feed.json()
    except eventlet.timeout.Timeout:
        logging.warning('Got Timeout while retrieving VK JSON data. Cancelling...')
        return None
    finally:
        timeout.cancel()

def save_last_index(index):
    index = str(index)
    with open(FILENAME_VK, 'wt') as file:
        try:
            file.write(index)
            logging.info('New last_id (VK) is {!s}'.format(index))
        except:
            file.write(index)
            logging.info('New last_id (VK) is {!s}'.format(index))


