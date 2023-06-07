from worker import processMusic
import base64
from flask import Flask, request, send_file, render_template, jsonify, redirect, url_for

import random
from io import BytesIO
from mutagen.id3 import ID3
from pydub import AudioSegment

# to remove the files and directories of the static directory
import os
import shutil

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


# remove all the directories and files inside the static folder
# this is done so that the files are not stored in the server
# after the server is closed
# as no database is used, this is the best way to do it
# eleminates the directory and all the files inside it

for root, dirs, files in os.walk('static', topdown=False):
    for file in files:
        # Remove files
        print('Removing file: ', file)
        filePath = os.path.join(root, file)
        os.remove(filePath)
    for dir in dirs:
        # Remove directories
        print('Removing directory: ', dir)
        dirPath = os.path.join(root, dir)
        shutil.rmtree(dirPath)


# define the classes
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
    taskCounter = 0

    # id is received as a string, so it is converted to int
    id = int(id)
    # if id does not exist, meaning that the music was not submitted
    if id not in id_usados:
        return 'No such ID was found. Try submitting the music again and using the generated ID'

    # the music is going to be processed by the worker here
    musicBytes = idBytes[id]

    # splits the music into chunks of 5 minutes
    chunks = splitMusic(musicBytes, 10)

    # iterate through the chunks
    for chunk in chunks:
        # process the music with the selected tracks
        callback = processMusic.apply_async(args=(encodeMusic(chunk), taskCounter))

        if id in callbacks.keys():
            callbacks[id].append(callback)
        else:
            callbacks[id] = [callback]

        taskCounter += 1

    return 'The music is being processed. To check the status of the process and later download the file, go to: localhost:5000/music/' + str(id)

@app.route('/music/<id>', methods=['GET'])
def music_id_get(id):
    ## get the state of the task, if it is at 100% it is done -> generate the file
    cbs = callbacks[int(id)]
    total = 0
    successes = 0

    temp = None

    for cb in cbs:
        print(cb.state) # shows the state of each task sent SUCCESS, PENDING, FAILURE
        total += 1
        if(cb.state == 'SUCCESS'):
            successes += 1
              
    # print(str(successes) + " -----> " + str(total))
    percentage = int(successes / total * 100)

    # if the music is still being processed
    if percentage != 100:
        return str(percentage)

    # if it is at 100% but info is not yet available (should not happen)
    for cb in cbs:
        if(cb.info == None):
            return str(percentage) 

    # get the instruments selected by the user
    instruments = idTracks[int(id)]

    # create the music directory to store the .wav files
    if not os.path.exists('static/' + str(id)):
        os.makedirs('static/' + str(id))


    # join the files from each task into one file
    # for example, bass0.wav, bass1.wav, bass2.wav --> bass.wav
    bass = []
    drums = []
    vocals = []
    other = []

    allInstruments = {}

    for cb in cbs:
        for key in cb.info.keys():
            if 'bass' in key:
                bass.append(key)
            elif 'drums' in key:
                drums.append(key)
            elif 'vocals' in key:
                vocals.append(key)
            elif 'other' in key:
                other.append(key)

            # store all the instruments in a list to access them easily
            allInstruments[key] = base64.b64decode(cb.info[key])
            

    # now with them in the lists, we can join them in order 0, ... ,n
    bass = sorted(bass, key=lambda x: int(x[4:]))
    drums = sorted(drums, key=lambda x: int(x[5:]))
    vocals = sorted(vocals, key=lambda x: int(x[6:]))
    other = sorted(other, key=lambda x: int(x[5:]))


    # finnaly, we can join them using AudioSegment


    # bass
    final = AudioSegment.from_file(BytesIO(allInstruments[bass[0]]), format="wav")
    for i in range(1, len(bass)):
        final += AudioSegment.from_file(BytesIO(allInstruments[bass[i]]), format="wav")
    final.export('static/' + str(id) + '/bass.wav', format='wav')
    
    # drums
    final = AudioSegment.from_file(BytesIO(allInstruments[drums[0]]), format="wav")
    for i in range(1, len(drums)):
        final += AudioSegment.from_file(BytesIO(allInstruments[drums[i]]), format="wav")
    final.export('static/' + str(id) + '/drums.wav', format='wav')

    # vocals
    final = AudioSegment.from_file(BytesIO(allInstruments[vocals[0]]), format="wav")
    for i in range(1, len(vocals)):
        final += AudioSegment.from_file(BytesIO(allInstruments[vocals[i]]), format="wav")
    final.export('static/' + str(id) + '/vocals.wav', format='wav')

    # other
    final = AudioSegment.from_file(BytesIO(allInstruments[other[0]]), format="wav")
    for i in range(1, len(other)):
        final += AudioSegment.from_file(BytesIO(allInstruments[other[i]]), format="wav")
    final.export('static/' + str(id) + '/other.wav', format='wav')


    # overlay the files in files to create the final .wav file
    # using the pydub library with the AudioSegment class
    files = []

    for instrument in instruments:
        files.append('static/' + str(id) + '/' + instrument + '.wav')

    returnFile = AudioSegment.from_file(files[0])

    for i in range(1, len(files)):
        returnFile = returnFile.overlay(AudioSegment.from_file(files[i]))
    returnFile.export('static/' + str(id) + '/returnFile.wav', format='wav')

    # the return will render the html page with links to the files
    links = [
        {'name': 'Bass', 'url': 'localhost:5000/static/' + str(id) + '/bass.wav'},
        {'name': 'Drums', 'url': 'localhost:5000/static/' + str(id) + '/drums.wav'},
        {'name': 'Vocals', 'url': 'localhost:5000/static/' + str(id) + '/vocals.wav'},
        {'name': 'Other', 'url': 'localhost:5000/static/' + str(id) + '/other.wav'},
        {'name': 'Generated File', 'url': 'localhost:5000/static/' + str(id) + '/returnFile.wav'}
    ]

    return render_template('generatedLinks.html', links=links)
    

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
    

if __name__ == '__main__':
    app.run()

