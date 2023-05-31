from worker import helloWorld, processMusic
import argparse
import base64
from pydub import AudioSegment

# function to split the audio file into segments
def getAudioSegments(audioFile, segmentLength):
    audio = AudioSegment.from_mp3(audioFile)
    audioLength = len(audio)
    start = 0
    end = 0
    audioSegments = []
    while end < audioLength:
        end = start + segmentLength
        if end > audioLength:
            end = audioLength
        audioSegments.append(audio[start:end])
        start = end
    return audioSegments

# fubction to encode the audio file
def encodeSong(path):
    with open(path, 'rb') as file:
        data = file.read()
    encoded = base64.b64encode(data).decode('utf-8')
    return encoded

# function to convert AudioSegment to path
def convertToMp3(audioSegment):
    path = 'temp.mp3'
    audioSegment.export(path, format='mp3')
    return path


def __main__():
    parser = argparse.ArgumentParser(description='Split an audio track', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', type=str, help='input mp3', default='music.mp3')
    parser.add_argument('-o', type=str, help='output folder', default='tracks')
    args = parser.parse_args()

    segmentLenght =  1000 * 60 * 5 # 5 minutes

    # get the audio segments
    audioSegments = getAudioSegments(args.i, segmentLenght)

    # loop through the audio segments
    for i in range(len(audioSegments)):
        print("Processing segment " + str(i))
        processMusic.delay(encodeSong(convertToMp3(audioSegments[i])))



if __name__ == '__main__':
    __main__()
