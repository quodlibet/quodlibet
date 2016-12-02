import requests

headers = {'user-agent': 'quodlibet-discogs-cover-source/0.0.1'}

params = {'type': 'release',
          'artist': 'Dam Mantle',
          'release_title': 'Brothers Fowl',
          'key': 'aWfZGjHQvkMcreUECGAp',
          'secret': 'VlORkklpdvAwJMwxUjNNSgqicjuizJAl'}

r = requests.get('https://api.discogs.com/database/search', params=params, headers=headers)

print(r.json())

# curl "https://api.discogs.com/database/search?q=Nirvana&key=aWfZGjHQvkMcreUECGAp&secret=VlORkklpdvAwJMwxUjNNSgqicjuizJAl"