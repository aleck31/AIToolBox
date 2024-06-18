# Copyright iX.
# SPDX-License-Identifier: MIT-0
import os
from io import BytesIO
from contextlib import closing
from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError


AUDIO_FORMATS = {
    "ogg_vorbis": "audio/ogg",
    "mp3": "audio/mpeg",
    "pcm": "audio/wave; codecs=1"
}
CHUNK_SIZE = 1024


session = Session(profile_name="default")
polly = session.client("polly")


def get_voice_stream(text, voice_id):
    '''

    '''
    try:
        # Request speech synthesis
        resp = polly.synthesize_speech(
            Text=text,
            VoiceId=voice_id,
            OutputFormat="ogg_vorbis",
            Engine="neural"
        )
    except (BotoCoreError, ClientError) as ex:
        # The service returned an error
        raise str(ex)

    return resp.get("AudioStream")


def read_stream(stream):
    """Consumes a stream in chunks to produce the response's output'"""
    print("Streaming started...")

    if stream:
        # Note: Closing the stream is important as the service throttles on the number of parallel connections. 
        # Here we are using contextlib.closing to ensure the close method of the stream object will be called automatically at the end of the with statement's
        # scope.
        with closing(stream) as managed_stream:
            # Push out the stream's content in chunks
            while True:
                data = managed_stream.read(CHUNK_SIZE)
                # self.wfile.write(b"%X\r\n%s\r\n" % (len(data), data))

                # If there's no more data to read, stop streaming
                if not data:
                    break

            # Ensure any buffered output has been transmitted and close the
            # stream
            # self.wfile.flush()

        print("Streaming completed.")
    else:
        # The stream passed in is empty
        # self.wfile.write(b"0\r\n\r\n")
        print("Nothing to stream.")