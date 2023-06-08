__author__ = 'Mário Antunes'
__version__ = '1.0'
__email__ = 'mario.antunes@ua.pt'
__status__ = 'Production'
__license__ = 'MIT'

import logging
import base64
import tempfile

from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import AudioFile, save_audio 

from celery import Celery
import time
import tempfile


app = Celery('worker', backend='rpc://', broker='amqp://guest:guest@localhost:5672//')
app.config_from_object('celeryconfig')

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


@app.task
def processMusic(input, counter):
    # start timer
    start = time.time()

    # get the model
    model = get_model(name='htdemucs')
    model.cpu()
    model.eval()
    audioBytes = base64.b64decode(input)
    # audioIO = io.BytesIO(audioBytes)

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(audioBytes)
        tf_path = tf.name

    # load the audio file
    wav = AudioFile(tf_path).read(streams=0,
    samplerate=model.samplerate, channels=model.audio_channels)
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()
    
    # apply the model
    sources = apply_model(model, wav[None], device='cpu', progress=True, num_workers=1)[0]
    sources = sources * ref.std() + ref.mean()

    # array to store each part of the music
    parts = {}
    # will send each instrument to the server
    for source, name in zip(sources, model.sources):

        with tempfile.NamedTemporaryFile(suffix='.wav') as tf:
            tempPath = tf.name

            save_audio(source, str(tempPath), samplerate=model.samplerate)
            parts[name + str(counter)] = encodeMusic(tf.read())
        
    # will send the 4 parts of the music to the server

    # end timer
    end = time.time()

    return (parts, end - start)

# function to encode the music bytes to base64
def encodeMusic(musicBytes):
    encoded = base64.b64encode(musicBytes).decode('utf-8')
    return encoded