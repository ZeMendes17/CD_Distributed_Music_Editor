from worker import processMusic
import argparse
import base64
from flask import Flask, request, send_file, render_template, jsonify, redirect, url_for

import random
from io import BytesIO
from mutagen.id3 import ID3
from pydub import AudioSegment
import decimal

# import json
# import numpy as np
# import torch
# import tempfile



app = Flask(__name__)
counter = 0
temp_files = {}
id_usados = []
musicas = []
idBytes = {}
idTracks = {}
callbacks = {}


class Music:
    def __init__(self, id, name, band, tracks):
        self.music_id = id
        self.name = name
        self.band = band
        self.tracks = tracks

    def __repr__(self):
        return f"Music({self.music_id}, {self.name}, {self.band}, {self.tracks})"

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/music', methods=['POST'])
def music_post():
    # gets the file from the request
    file = request.files['myfile']
    # gets the file to bytes
    fileBytes = file.read()

    # gets the music info, name and band
    try:
        music = ID3(fileobj=BytesIO(fileBytes))
        name = music['TIT2'].text[0] if music['TIT2'] else 'Unknown'
        band = music['TPE1'].text[0] if music['TPE1'] else 'Unknown'
    except Exception as e:
        print('Error: ', e)
        name = 'Unknown'
        band = 'Unknown'   

    # creates the music object instance
    musicObj = createMusicObj(name, band)

    # store the id and the bytes of the music
    idBytes[musicObj.music_id] = fileBytes
    
    # returns the music info
    return jsonify(toDict(musicObj))

    

@app.route('/music', methods=['GET'])
def music_get():
    result = []
    # foreach music in the musicas list converts it to a dict to return after
    for music in musicas:
        result.append(toDict(music))
        
    return jsonify(result)

@app.route('/redirect', methods=['POST'])
def redirect_post():

    # gets the music id from the request
    musicID = int (request.form.get('id'))
    
    bass = (request.form.get('bass'))
    drums = (request.form.get('drums'))
    vocals = (request.form.get('vocals'))
    other = (request.form.get('other'))

    # print('bass: ', bass)
    # print('drums: ', drums)
    # print('vocals: ', vocals)
    # print('other: ', other)
    
    if bass == None and drums == None and vocals == None and other == None:
        return 'No track was selected. Please select at least one track to separate'
    
    tracks = []
    if bass != None:
        tracks.append('bass')
    if drums != None:
        tracks.append('drums')
    if vocals != None:
        tracks.append('vocals')
    if other != None:
        tracks.append('other')

    # stores the tracks to be separated with the music id
    idTracks[musicID] = tracks

    # redirects to the music_id_post method with the music id inserted
    return redirect(url_for('music_id_post', id=musicID), code=307) # 307 is the code for redirecting to POST method instead of GET

@app.route('/music/<id>', methods=['POST'])
def music_id_post(id):
    # id is received as a string, so it is converted to int
    id = int(id)
    # if id does not exist, meaning that the music was not submitted
    if id not in id_usados:
        return 'No such ID was found. Try submitting the music again and using the generated ID'

    # the music is going to be processed by the worker here
    musicBytes = idBytes[id]

    # splits the music into chunks of 5 minutes
    chunks = splitMusic(musicBytes, 60 * 5)

    # iterate through the chunks
    for chunk in chunks:
        # process the music with the selected tracks
        callback = processMusic.apply_async(args=(encodeMusic(musicBytes), id))

        if id in callbacks.keys():
            callbacks[id].append(callback)
        else:
            callbacks[id] = [callback]

    return 'The music is being processed. To check the status of the process and later download the file, go to: localhost:5000/music/' + str(id)

@app.route('/music/<id>', methods=['GET'])
def music_id_get(id):
    ## get the state of the task, if it is at 100% it is done -> generate the file
    cbs = callbacks[int(id)]
    total = 0
    successes = 0

    for cb in cbs:
        total += 1
        if(cb.state == 'SUCCESS'):
            successes += 1
              
    # print(str(successes) + " -----> " + str(total))
    percentage = int(successes / total * 100)
    return str(percentage)

# creates the music object
def createMusicObj(name, band):
    tracks = [ 
            { 
                "name": "drums",
                "track_id": 1 
            },
            {
                "name": "bass",
                "track_id": 2
            },
            {
                "name": "vocals",
                "track_id": 3
            },
            {
                "name": "other",
                "track_id": 4
            }
             ]
    
    # if the music already exists in the server, there is no need to create a new Obj   
    # fro now if it is known --> new music
    for musica in musicas:
        if musica.name == name and musica.name != 'Unknown' and musica.band == band and musica.band != 'Unknown':
            return musica
        
    id = generateID()

    music = Music(id, name, band, tracks)


    # stores the music info into a dict
    musicas.append(music)
    
    return music

# function to convert the music object to a dict
def toDict(music: Music):
    return {
        "music_id": music.music_id,
        "name": music.name,
        "band": music.band,
        "tracks": music.tracks
    }


# generates and stores the id to a id list in order to not repeat ids
def generateID():
    id = random.randint(100000, 999999)
    while id in id_usados:
         id = random.randint(100000, 999999)
    
    id_usados.append(id)
    return id
    
# function to encode the music bytes to base64
def encodeMusic(musicBytes):
    encoded = base64.b64encode(musicBytes).decode('utf-8')
    return encoded

# function to split the audio file into segments
def splitMusic(musicBytes, chunkDuration):
    # Create an audio segment from the input music bytes
    audio = AudioSegment.from_file(BytesIO(musicBytes), format='mp3')

    # Calculate the chunk length in milliseconds
    length = int(chunkDuration * 1000)

    chunks = []
    totalDuration = len(audio)

    for start in range(0, totalDuration, length):
        end = min(start + length, totalDuration)
        chunk = audio[start:end]
        chunks.append(chunk.export(format='mp3').read())

    return chunks

# # function to encode the audio file
# def encodeSong(path):
#     with open(path, 'rb') as file:
#         data = file.read()
#     encoded = base64.b64encode(data).decode('utf-8')
#     return encoded

# # function to convert AudioSegment to path
# def convertToMp3(audioSegment):
#     path = 'temp.mp3'
#     audioSegment.export(path, format='mp3')
#     return path


# def __main__():
#     global counter  
#     parser = argparse.ArgumentParser(description='Split an audio track', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
#     parser.add_argument('-i', type=str, help='input mp3', default='music.mp3')
#     parser.add_argument('-o', type=str, help='output folder', default='tracks')
#     args = parser.parse_args()

#     segmentLenght =  1000 * 30 # 30 seconds

#     # get the audio segments
#     audioSegments = getAudioSegments(args.i, segmentLenght)

#     # loop through the audio segments
#     for i in range(len(audioSegments)):
#         print("Processing segment " + str(i))
#         processMusic.delay(encodeSong(convertToMp3(audioSegments[i])), counter)
#         counter += 1


# @app.route('/store', methods=['POST'])
# def store():
#     data = request.get_json()
#     audio_id = data["id"]
#     audio_name = data["name"]


#     stem = f'tracks/{data["name"]}{data["id"]}.wav'
#     array = np.array(json.loads(data['data']))
#     # print(torch.from_numpy(array).to(torch.float32))
    
#     ##
#     audio_bytes = array.tobytes()

#     with tempfile.NamedTemporaryFile(delete=False) as temp_file:
#         temp_file.write(audio_bytes)
#         temp_files[audio_id] = temp_file.name
#     ##
#     save_audio(torch.from_numpy(array).to(torch.float32), str(stem), data['samplerate'])

#     return send_file('test.mp3')


# @app.route('/store/<string:audio_name>', methods=['GET'])
# def download_audio(audio_id):
#     if audio_id in temp_files:
#         temp_file_path = temp_files[audio_id]
#         return send_file(temp_file_path, as_attachment=True, attachment_filename=f'audio_{audio_id}.wav')
#     else:
#         return "Audio not found."


if __name__ == '__main__':
    # __main__()
    app.run()

