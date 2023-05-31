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

app = Celery(broker='pyamqp://guest@localhost//')
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

@app.task
def helloWorld():
    return 'hello'


@app.task
def processMusic(input):
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

    # store the model
    # for source, name in zip(sources, model.sources):
    #     stem = f'{args.o}/{name}.wav'
    #     save_audio(source, str(stem), samplerate=model.samplerate)

    return "Hello World"

    