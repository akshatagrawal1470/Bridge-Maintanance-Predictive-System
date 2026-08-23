# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l.
#
# SPDX-License-Identifier: MPL-2.0

import json
import time
import threading
from collections import deque
from datetime import datetime

import numpy as np

from arduino.app_utils import *
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.vibration_anomaly_detection import (
    VibrationAnomalyDetection
)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_THRESHOLD = 1.0

# Score above this = significant anomaly
WARNING_SCORE = 15

# Score above this = critical anomaly
CRITICAL_SCORE = 50

# Keep critical state for this amount of time
ANOMALY_HOLD_TIME = 5.0

# Number of consecutive anomalous detections
# required before changing to CRITICAL
REQUIRED_ANOMALIES = 15

# FFT buffer
FFT_BUFFER_SIZE = 256

# UI update
UI_PERIOD = 0.25


logger = Logger(
    "Bridge Predictive Maintenance"
)


# ============================================================
# EDGE IMPULSE MODEL
# ============================================================

vibration_detection = VibrationAnomalyDetection(
    anomaly_detection_threshold=MODEL_THRESHOLD
)


# ============================================================
# WEB UI
# ============================================================

ui = WebUI()


# ============================================================
# SHARED STATE
# ============================================================

state_lock = threading.Lock()


current_status = "SAFE"

current_score = 0.0

current_health = 100

last_anomaly_time = 0.0

consecutive_anomalies = 0

last_sensor_time = 0.0


latest_sensor = {
    "ax": 0.0,
    "ay": 0.0,
    "az": 0.0,
    "temperature": 0.0
}


# ============================================================
# SENSOR BUFFERS
# ============================================================

ax_buffer = deque(
    maxlen=FFT_BUFFER_SIZE
)

ay_buffer = deque(
    maxlen=FFT_BUFFER_SIZE
)

az_buffer = deque(
    maxlen=FFT_BUFFER_SIZE
)

timestamp_buffer = deque(
    maxlen=FFT_BUFFER_SIZE
)


# ============================================================
# MODEL INFORMATION
# ============================================================

model_info = (
    vibration_detection.get_model_info()
)

MODEL_FREQUENCY = 100.0

if model_info is not None:

    frequency = getattr(
        model_info,
        "frequency",
        None
    )

    if frequency:

        MODEL_FREQUENCY = float(
            frequency
        )


logger.info(
    f"Edge Impulse model frequency: "
    f"{MODEL_FREQUENCY} Hz"
)


# ============================================================
# HEALTH CALCULATION
# ============================================================

def calculate_health(score):

    score = float(score)

    # Normal
    if score <= MODEL_THRESHOLD:
        return 100

    # Critical
    if score >= CRITICAL_SCORE:
        return 0

    # Linear interpolation
    health = (
        100
        *
        (
            CRITICAL_SCORE - score
        )
        /
        (
            CRITICAL_SCORE - MODEL_THRESHOLD
        )
    )

    return int(
        max(
            0,
            min(
                100,
                health
            )
        )
    )


# ============================================================
# RECOMMENDATION
# ============================================================

def get_recommendation(
    status,
    score
):

    if status == "SAFE":

        return (
            "Bridge vibration is within "
            "the learned normal operating range. "
            "Continue routine monitoring."
        )

    if status == "WARNING":

        return (
            "Abnormal vibration has been detected. "
            "Continue monitoring the bridge and "
            "inspect if the condition persists."
        )

    return (
        "Critical vibration anomaly detected. "
        "Immediate structural inspection "
        "is recommended."
    )


# ============================================================
# AI ANOMALY CALLBACK
# ============================================================

def on_detected_anomaly(
    anomaly_score,
    classification=None
):

    global current_status
    global current_score
    global current_health
    global last_anomaly_time
    global consecutive_anomalies

    score = float(
        anomaly_score
    )

    with state_lock:

        current_score = score

        last_anomaly_time = (
            time.monotonic()
        )

        consecutive_anomalies += 1

        # ----------------------------------------------------
        # Don't immediately switch to critical from one spike
        # ----------------------------------------------------

        if (
            consecutive_anomalies
            >= REQUIRED_ANOMALIES
        ):

            current_status = "CRITICAL"

        else:

            current_status = "WARNING"

        current_health = (
            calculate_health(score)
        )

    logger.warning(
        f"AI anomaly score = "
        f"{score:.3f} | "
        f"status = {current_status}"
    )


vibration_detection.on_anomaly(
    on_detected_anomaly
)


# ============================================================
# SENSOR PROCESSING
# ============================================================

def process_sensor_sample(
    ax,
    ay,
    az,
    temperature
):

    global last_sensor_time

    now = time.monotonic()

    with state_lock:

        latest_sensor["ax"] = ax

        latest_sensor["ay"] = ay

        latest_sensor["az"] = az

        latest_sensor[
            "temperature"
        ] = temperature

        ax_buffer.append(ax)

        ay_buffer.append(ay)

        az_buffer.append(az)

        timestamp_buffer.append(now)

        last_sensor_time = now


    # --------------------------------------------------------
    # FEED EDGE IMPULSE MODEL
    # --------------------------------------------------------
    #
    # IMPORTANT:
    #
    # Arduino sends AX/AY/AZ in g.
    #
    # Convert to m/s² here ONLY if the model was trained
    # using m/s².
    #
    # If Edge Impulse was trained using g, remove this
    # multiplication.
    # --------------------------------------------------------

    G = 9.80665

    x_ms2 = ax * G
    y_ms2 = ay * G
    z_ms2 = az * G

    vibration_detection.accumulate_samples(
        (
            x_ms2,
            y_ms2,
            z_ms2
        )
    )


# ============================================================
# GET DATA FROM ARDUINO
# ============================================================

def sensor_loop():

    global consecutive_anomalies
    global current_status
    global current_score

    logger.info(
        "Starting sensor acquisition..."
    )

    while True:

        try:

            # ------------------------------------------------
            # Ask Arduino for 10 samples.
            # Arduino samples them at 100 Hz.
            # ------------------------------------------------

            result = Bridge.call(
                "get_sensor_batch",
                ""
            )

            if result is None:

                time.sleep(0.1)

                continue


            # ------------------------------------------------
            # Parse JSON
            # ------------------------------------------------

            if isinstance(
                result,
                bytes
            ):

                result = result.decode(
                    "utf-8"
                )


            data = json.loads(
                result
            )


            if not isinstance(
                data,
                list
            ):

                logger.warning(
                    "Invalid sensor batch"
                )

                time.sleep(0.1)

                continue


            # ------------------------------------------------
            # Process all samples
            # ------------------------------------------------

            for sample in data:

                ax = float(
                    sample["ax"]
                )

                ay = float(
                    sample["ay"]
                )

                az = float(
                    sample["az"]
                )

                temperature = float(
                    sample["temperature"]
                )


                process_sensor_sample(
                    ax,
                    ay,
                    az,
                    temperature
                )


                # ------------------------------------------------
                # Send sensor data to UI
                # ------------------------------------------------

                ui.send_message(
                    "sensor_data",
                    {
                        "ax": ax,
                        "ay": ay,
                        "az": az,
                        "temperature":
                            temperature,
                        "timestamp":
                            int(
                                time.time()
                                * 1000
                            )
                    }
                )


            # ------------------------------------------------
            # Approximately 10 batches/sec
            # ------------------------------------------------

            time.sleep(0.005)


        except Exception as exc:

            logger.error(
                f"Sensor loop error: {exc}"
            )

            time.sleep(0.5)


# ============================================================
# FFT / FEATURE PROCESSING
# ============================================================

def calculate_features():

    with state_lock:

        if len(az_buffer) < 32:

            return None

        az = np.asarray(
            az_buffer,
            dtype=np.float64
        )

        timestamps = np.asarray(
            timestamp_buffer,
            dtype=np.float64
        )


    # --------------------------------------------------------
    # Sampling frequency
    # --------------------------------------------------------

    if len(timestamps) > 2:

        duration = (
            timestamps[-1]
            -
            timestamps[0]
        )

        if duration > 0:

            fs = (
                len(timestamps) - 1
            ) / duration

        else:

            fs = MODEL_FREQUENCY

    else:

        fs = MODEL_FREQUENCY


    # --------------------------------------------------------
    # Remove gravity / DC
    # --------------------------------------------------------

    signal = (
        az - np.mean(az)
    )


    # --------------------------------------------------------
    # RMS
    # --------------------------------------------------------

    rms = float(
        np.sqrt(
            np.mean(
                signal ** 2
            )
        )
    )


    # --------------------------------------------------------
    # Energy
    # --------------------------------------------------------

    energy = float(
        np.mean(
            signal ** 2
        )
    )


    # --------------------------------------------------------
    # FFT
    # --------------------------------------------------------

    n = len(signal)

    window = np.hanning(n)

    fft_data = np.fft.rfft(
        signal * window
    )

    magnitude = np.abs(
        fft_data
    )

    frequencies = np.fft.rfftfreq(
        n,
        d=1.0 / max(
            fs,
            1.0
        )
    )


    # Remove DC

    if len(magnitude) > 1:

        magnitude[0] = 0


    # --------------------------------------------------------
    # Peak
    # --------------------------------------------------------

    peak_index = int(
        np.argmax(
            magnitude
        )
    )

    peak_frequency = float(
        frequencies[
            peak_index
        ]
    )

    peak_magnitude = float(
        magnitude[
            peak_index
        ]
    )


    # --------------------------------------------------------
    # Spectral centroid
    # --------------------------------------------------------

    magnitude_sum = float(
        np.sum(magnitude)
    )

    if magnitude_sum > 0:

        centroid = float(
            np.sum(
                frequencies
                *
                magnitude
            )
            /
            magnitude_sum
        )

    else:

        centroid = 0.0


    return {

        "rms": rms,

        "energy": energy,

        "peak_frequency":
            peak_frequency,

        "peak_magnitude":
            peak_magnitude,

        "spectral_centroid":
            centroid,

        "frequencies":
            frequencies.tolist(),

        "magnitude":
            magnitude.tolist()
    }


# ============================================================
# STATUS LOOP
# ============================================================

def status_loop():

    global current_status
    global current_score
    global current_health
    global consecutive_anomalies

    last_history = 0

    while True:

        try:

            now = time.monotonic()

            with state_lock:

                status = current_status

                score = current_score

                health = current_health

                last_anomaly = (
                    last_anomaly_time
                )

                last_sensor = (
                    last_sensor_time
                )

                temperature = (
                    latest_sensor[
                        "temperature"
                    ]
                )


            # ------------------------------------------------
            # Clear anomaly after hold time
            # ------------------------------------------------

            if (
                status != "SAFE"
                and last_anomaly > 0
                and
                (
                    now
                    -
                    last_anomaly
                )
                >
                ANOMALY_HOLD_TIME
            ):

                with state_lock:

                    current_status = "SAFE"

                    current_score = 0.0

                    current_health = 100

                    consecutive_anomalies = 0

                    status = "SAFE"

                    score = 0.0

                    health = 100

                logger.info(
                    "Anomaly cleared -> SAFE"
                )


            # ------------------------------------------------
            # Board status
            # ------------------------------------------------

            board_online = (
                last_sensor > 0
                and
                (
                    now
                    -
                    last_sensor
                )
                < 2.0
            )


            ui.send_message(
                "board_status",
                {
                    "online":
                        board_online
                }
            )


            # ------------------------------------------------
            # Prediction
            # ------------------------------------------------

            ui.send_message(
                "prediction",
                {
                    "status":
                        status,

                    "score":
                        float(score),

                    "health":
                        int(health),

                    "message":
                        get_recommendation(
                            status,
                            score
                        ),

                    "timestamp":
                        datetime.now()
                        .strftime(
                            "%H:%M:%S"
                        )
                }
            )


            # ------------------------------------------------
            # Features
            # ------------------------------------------------

            features = (
                calculate_features()
            )

            if features:

                ui.send_message(
                    "features",
                    {
                        "rms":
                            features[
                                "rms"
                            ],

                        "energy":
                            features[
                                "energy"
                            ],

                        "peak_frequency":
                            features[
                                "peak_frequency"
                            ],

                        "peak_magnitude":
                            features[
                                "peak_magnitude"
                            ],

                        "spectral_centroid":
                            features[
                                "spectral_centroid"
                            ],

                        "frequencies":
                            features[
                                "frequencies"
                            ],

                        "magnitude":
                            features[
                                "magnitude"
                            ]
                    }
                )


            # ------------------------------------------------
            # History
            # ------------------------------------------------

            if (
                now - last_history
                >= 2.0
            ):

                last_history = now

                ui.send_message(
                    "history",
                    {
                        "time":
                            datetime.now()
                            .strftime(
                                "%H:%M:%S"
                            ),

                        "health":
                            health,

                        "status":
                            status,

                        "temperature":
                            temperature
                    }
                )


            time.sleep(
                UI_PERIOD
            )


        except Exception as exc:

            logger.error(
                f"Status loop error: {exc}"
            )

            time.sleep(1)


# ============================================================
# START THREADS
# ============================================================

threading.Thread(
    target=sensor_loop,
    daemon=True
).start()


threading.Thread(
    target=status_loop,
    daemon=True
).start()


# ============================================================
# START APP
# ============================================================

logger.info(
    "Bridge Predictive Maintenance "
    "Application Started"
)

App.run()
