# Copyright 2018 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import atexit

import numpy as np
import pyaudio


class Listener:
    """
    Read audio from the microphone chunk by chunk
    Args are passed to pyaudio.Stream.

    Usage:
        >>> for chunk in Listener(frames_per_buffer=512, rate=24100):
        ...     print(chunk.mean())
    Args:
        frames_per_buffer (int): number of samples in each chunk
        rate (int): Samples per second read from the microphone
        format (int): pyaudio format id (ie. paInt16 or paFloat32)
        channels (int): Number of audio channels
    """
    default_args = dict(
        frames_per_buffer=1024,
        rate=16000,
        channels=1,
    )

    def __init__(self, **stream_args):
        """"""
        self.stream_args = self.default_args.copy()
        self.stream_args.update(stream_args)
        self.p = self.stream = None
        self.chunk_size = self.stream_args['frames_per_buffer']

    def __iter__(self):
        self.p = pyaudio.PyAudio()
        atexit.register(self.p.terminate)
        self.stream = self.p.open(**self.stream_args, format=pyaudio.paFloat32, input=True)
        atexit.register(self.stream.close)
        atexit.register(self.stream.stop_stream)
        return self

    def __next__(self):
        chunk = self.stream.read(self.chunk_size)
        return np.fromstring(chunk, dtype=np.float32).reshape((self.chunk_size, -1)).squeeze()


class WindowListener(Listener):
    """
    Read audio from a rolling buffer
    Args:
        window (int): Samples to use in buffer
        stride (int): Number of samples to shift each loop
    """

    def __init__(self, window, stride):
        super().__init__(frames_per_buffer=stride)
        self.window, self.stride = window, stride
        self.buffer = np.zeros(window)

    def __next__(self):
        chunk = super().__next__()
        self.buffer = np.concatenate([self.buffer[len(chunk):], chunk])
        return self.buffer


class FeatureListener(Listener):
    """
    Process audio into features
    Args:
        processor (Callable): Function to turn audio chunk into feature vector
        stride (int): Samples to shift each time a new feature can be generated
        num_features (int): Number of features to store in buffer window
        stream_args (dict): Arguments to pass to pyaudio.Stream
    """

    def __init__(self, processor, stride, num_features, stream_args=None):
        super().__init__(frames_per_buffer=stride, **(stream_args or {}))
        self.processor = processor
        self.stride = stride
        self.num_features = num_features
        self.features = None
        self.buffer = np.empty(0)

    def __next__(self):
        self.buffer = np.concatenate([self.buffer, super().__next__()])
        total_chunks = (len(self.buffer) // self.stride) * self.stride
        new_features = np.array(self.processor(self.buffer[:total_chunks]))
        if self.features is None:
            feature_shape = new_features.shape[1:]
            self.features = np.zeros((self.num_features, *feature_shape))
        self.features = np.concatenate([self.features[len(new_features):], new_features])
        self.buffer = self.buffer[self.stride * len(new_features):]
        return self.features
