from datetime import datetime
import sys
import pymysql
import boto3
import logging
import os
import requests
import base64
import json
import pandas as pd
import jsonpath #pip3 install jsonpath --user



def main():
    
    # mysql(rds) artist_id
    try:
        conn = pymysql.connect(host=host, user=username, password=password, db=database, port=port, use_unicode=True, charset='utf8')
        cursor = conn.cursor()

    except:
        logging.error("could not connect to rds")
        sys.exit(1)


    headers = get_headers(client_id, client_secret)
    

    #RDS - 아티스트 ID를 가져오고
    cursor.execute('SELECT id FROM artists LIMIT 10') #일단 10개만 


    #jsonpath : key값을 입력 받아 value 값 return 
    #external_url, id, name, popularity
    top_tracks_keys = {
        'id' : 'id',
        'name' : 'name',
        'popularity' : 'popularity',
        'external_url' : 'external_urls.spotify'

    }

    top_tracks = []
    for (id, ) in cursor.fetchall():

        URL = 'https://api.spotify.com/v1/artists/{}/top-tracks'.format(id)
        params = {
            'country' : 'US'
        }
        r = requests.get(URL, params=params, headers=headers)
        raw = json.loads(r.text)

        for i in raw['tracks']:
            top_track = {}
            for k, v in top_tracks_keys.items():
                top_track.update({k: jsonpath.jsonpath(i, v)})
                top_track.update({'artist_id': id})
                top_tracks.append(top_track)


    #track_ids
    track_ids = [i['id'][0] for i in top_tracks]


    top_tracks = pd.DataFrame(raw)
    top_tracks.to_parquet('top-tracks.parquet', engine ='pyarrow', compression='snappy') #name, engine, 압축방식


    #Json 으로 저장 -> json 보다는 parquet() 선호
    # with open('top_tracks.json','w') as f:
    #     for i in top_tracks:
    #         json.dump(i, f)
    #         f.write(os.linesep)
 
    dt = datetime.utcnow().strftime('%Y-%m-%d')
    s3 = boto3.resource('s3')
    object = s3.Object('spotify-artists-cy', 'top-tracks/dt={}/top-tracks.parquet'.format(dt)) #bucket, partition
    data = open('top-tracks.parquet','rb')
    object.put(Body = data)
    #S3 import

    #Maximum: 100 IDs. audio features
    tracks_batch = [track_ids[i:i+100] for i in range(0, len(track_ids), 100)]

    #audio-features
    audio_features = []
    for i in tracks_batch:

        ids = ','.join(i)
        URL = 'https://api.spotify.com/v1/audio-features/?ids={}'.format(ids)

        r = requests.get(URL, headers=headers)
        raw = json.loads(r.text)

        audio_features.extend(raw['audio_features'])


    audio_features = pd.DataFrame(audio_features)
    audio_features.to_parquet('audio-features.parquet', engine ='pyarrow', compression='snappy')

    s3 = boto3.resource('s3')
    object = s3.Object('spotify-artists-cy', 'audio-features/dt={}/top-tracks.parquet'.format(dt)) #bucket, partition
    data = open('audio-features.parquet','rb')
    object.put(Body = data)






def get_headers(client_id, client_secret):
    endpoint = "https://accounts.spotify.com/api/token"
    encoded = base64.b64encode("{}:{}".format(client_id, client_secret).encode('utf-8')).decode('ascii')

    headers = {
        "Authorization": "Basic {}".format(encoded)
    }

    payload = {
        "grant_type": "client_credentials"
    }

    r = requests.post(endpoint, data=payload, headers=headers)

    access_token = json.loads(r.text)

    access_token = json.loads(r.text)['access_token']

    headers = {
        "Authorization": "Bearer {}".format(access_token)
    }
    return headers




if __name__ == '__main__':

    main()
