# PyListen

*A simple pyaudio microphone interface*

PyListen abstracts creating an audio stream and converting
raw byte data into numpy arrays.

## Usage

```python
from pylisten import Listener, WindowListener, FeatureListener

for chunk in Listener(frames_per_buffer=512, rate=24100):
    print('Current volume:', abs(chunk).mean())

for window in WindowListener(1024 * 10, 1024):
    print('Volume of last 10 chunks:', abs(window).mean())

for features in FeatureListener(lambda x: [abs(x).mean()], 1024, 20):
    print('Past 20 volumes:', features)
```


## Installation

```bash
pip install pylisten
```
