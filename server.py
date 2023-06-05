from worker import helloWorld, processMusic
import argparse
import base64
from pydub import AudioSegment
from flask import Flask, request, send_file, render_template, jsonify

from demucs.audio import save_audio

import random
from io import BytesIO
from mutagen.id3 import ID3

import json
import numpy as np
import torch
import tempfile


app = Flask(__name__)
counter = 0
temp_files = {}
id_usados = []
musicas = []
idBytes = {}


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

@app.route('/music/<int:id>', methods=['POST'])
def music_id_post(id):
    
    # gets the music bytes
    musicBytes = idBytes[id]

    


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
    

# # function to split the audio file into segments
# def getAudioSegments(audioFile, segmentLength):
#     audio = AudioSegment.from_mp3(audioFile)
#     audioLength = len(audio)
#     start = 0
#     end = 0
#     audioSegments = []
#     while end < audioLength:
#         end = start + segmentLength
#         if end > audioLength:
#             end = audioLength
#         audioSegments.append(audio[start:end])
#         start = end
#     return audioSegments

# # fubction to encode the audio file
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

