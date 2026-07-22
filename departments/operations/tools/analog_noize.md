Да — для реалистичного синт-модуля лучше собрать **модель шумового тракта**, а не просто один генератор. Базой остаётся гауссов белый шум NumPy, а реализм добавляют полосовая фильтрация, лёгкий high-cut, DC-block и небольшая неидеальность уровня. [docs.scipy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.lfilter.html)

## Подход

Схема обычно такая: источник белого шума → усиление → полосовая коррекция → мягкий срез ВЧ → опциональная окраска. Для этого удобно использовать `numpy.random.Generator.normal` и `scipy.signal.butter`/`lfilter`; SciPy прямо рекомендует `butter` для дизайна фильтра и `lfilter` для применения цифровой фильтрации. [numpy](https://numpy.org/doc/2.1/reference/random/generated/numpy.random.Generator.normal.html)

## Функция

```python
import numpy as np
from scipy.signal import butter, lfilter

def synth_noise(
    duration_s=5.0,
    sr=44100,
    preset="neutral",
    seed=None,
    drive=1.0,
    output_peak=0.95,
):
    presets = {
        "neutral": {
            "band_low_hz": 20.0,
            "band_high_hz": 18000.0,
            "hf_rolloff_hz": 15000.0,
            "pinkish_amount": 0.0003,
            "dc_block_hz": 5.0,
            "gain": 1.0,
        },
        "bright": {
            "band_low_hz": 30.0,
            "band_high_hz": 20000.0,
            "hf_rolloff_hz": 18000.0,
            "pinkish_amount": 0.0,
            "dc_block_hz": 5.0,
            "gain": 1.2,
        },
        "warm": {
            "band_low_hz": 20.0,
            "band_high_hz": 12000.0,
            "hf_rolloff_hz": 9000.0,
            "pinkish_amount": 0.0010,
            "dc_block_hz": 8.0,
            "gain": 1.3,
        },
        "dirty": {
            "band_low_hz": 10.0,
            "band_high_hz": 9000.0,
            "hf_rolloff_hz": 7000.0,
            "pinkish_amount": 0.0020,
            "dc_block_hz": 12.0,
            "gain": 1.5,
        },
    }

    p = presets[preset].copy()
    rng = np.random.default_rng(seed)
    n = int(duration_s * sr)

    y = rng.normal(0.0, 1.0, n)

    nyq = sr / 2.0

    b, a = butter(
        4,
        [p["band_low_hz"] / nyq, p["band_high_hz"] / nyq],
        btype="bandpass",
    )
    y = lfilter(b, a, y)

    if p["hf_rolloff_hz"] < nyq:
        b, a = butter(2, p["hf_rolloff_hz"] / nyq, btype="lowpass")
        y = lfilter(b, a, y)

    if p["dc_block_hz"] > 0:
        b, a = butter(1, p["dc_block_hz"] / nyq, btype="highpass")
        y = lfilter(b, a, y)

    if p["pinkish_amount"] > 0:
        drift = np.cumsum(rng.normal(0.0, p["pinkish_amount"], n))
        y = y + drift

    y = y * p["gain"] * drive
    y = y - np.mean(y)

    peak = np.max(np.abs(y))
    if peak > 0:
        y = y / peak * output_peak

    return y.astype(np.float32)
```

## Пресеты

Можно мыслить так:

- **neutral**: универсальный шум для синта, близко к «чистому» аналоговому. [docs.scipy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.butter.html)
- **bright**: более открытый, почти без окраски, хорошо для хэтов и перкуссии.
- **warm**: уже и мягче по верхам, удобен для фонового шума и винтажного ощущения.
- **dirty**: имитация более дешёвого/неидеального тракта с меньшей полосой и заметной окраской.

## Использование

```python
noise = synth_noise(duration_s=10, sr=48000, preset="warm", seed=1, drive=0.9)
```

Если нужен WAV:

```python
from scipy.io.wavfile import write

noise = synth_noise(duration_s=10, sr=48000, preset="neutral", seed=1)
write("noise.wav", 48000, (noise * 32767).astype(np.int16))
```

## Что ещё можно добавить

Для ещё более правдоподобного синт-модуля обычно добавляют:

- **самоусиление с клиппингом**, чтобы шум вёл себя как перегруженный аналоговый каскад;
- **медленный random drift** параметров фильтра;
- **несколько слоёв шума**, например белый плюс слабый розовый;
- **стерео-несовпадение каналов**, если нужна естественность. [mmp.susu](https://mmp.susu.ru/article/ru/315)

Следующим шагом могу сразу дописать версию **с ADSR, стерео, сатурацией и CV-входом** под модуль синта.
