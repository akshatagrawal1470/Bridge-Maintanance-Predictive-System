/* ============================================================
   Bridge Predictive Maintenance
   Arduino App Lab WebUI
============================================================ */


// ============================================================
// GLOBALS
// ============================================================

let vibrationChart = null;

let fftChart = null;

const MAX_POINTS = 100;


// ============================================================
// HELPERS
// ============================================================

function getElement(id) {

    return document.getElementById(id);

}


function safeNumber(value, fallback = 0) {

    const n = Number(value);

    return Number.isFinite(n)
        ? n
        : fallback;

}


// ============================================================
// VIBRATION CHART
// ============================================================

function createVibrationChart() {

    const canvas =
        getElement(
            "vibration-chart"
        );

    if (!canvas)
        return;


    vibrationChart =
        new Chart(
            canvas,
            {

                type: "line",

                data: {

                    labels: [],

                    datasets: [

                        {
                            label: "AX",

                            data: [],

                            borderWidth: 2,

                            pointRadius: 0,

                            tension: 0.2
                        },

                        {
                            label: "AY",

                            data: [],

                            borderWidth: 2,

                            pointRadius: 0,

                            tension: 0.2
                        },

                        {
                            label: "AZ",

                            data: [],

                            borderWidth: 2,

                            pointRadius: 0,

                            tension: 0.2
                        }

                    ]

                },

                options: {

                    responsive: true,

                    animation: false,

                    scales: {

                        y: {

                            title: {

                                display: true,

                                text: "Acceleration (g)"

                            }

                        }

                    }

                }

            }
        );

}


// ============================================================
// FFT CHART
// ============================================================

function createFFTChart() {

    const canvas =
        getElement(
            "fft-chart"
        );

    if (!canvas)
        return;


    fftChart =
        new Chart(
            canvas,
            {

                type: "line",

                data: {

                    labels: [],

                    datasets: [

                        {

                            label:
                                "FFT Magnitude",

                            data: [],

                            borderWidth: 2,

                            pointRadius: 0,

                            tension: 0.1

                        }

                    ]

                },

                options: {

                    responsive: true,

                    animation: false,

                    scales: {

                        x: {

                            title: {

                                display: true,

                                text: "Frequency (Hz)"

                            }

                        },

                        y: {

                            title: {

                                display: true,

                                text: "Magnitude"

                            }

                        }

                    }

                }

            }
        );

}


// ============================================================
// UPDATE VIBRATION
// ============================================================

function updateVibration(data) {

    if (!vibrationChart)
        return;


    const time =
        new Date()
        .toLocaleTimeString();


    vibrationChart.data.labels.push(
        time
    );


    vibrationChart.data.datasets[0]
        .data.push(
            safeNumber(data.ax)
        );


    vibrationChart.data.datasets[1]
        .data.push(
            safeNumber(data.ay)
        );


    vibrationChart.data.datasets[2]
        .data.push(
            safeNumber(data.az)
        );


    if (
        vibrationChart.data.labels.length
        >
        MAX_POINTS
    ) {

        vibrationChart.data.labels.shift();

        vibrationChart.data.datasets
            .forEach(
                dataset =>
                    dataset.data.shift()
            );

    }


    vibrationChart.update(
        "none"
    );

}


// ============================================================
// UPDATE FFT
// ============================================================

function updateFFT(data) {

    if (!fftChart)
        return;


    const frequencies =
        data.frequencies || [];


    const magnitude =
        data.magnitude || [];


    fftChart.data.labels =
        frequencies;


    fftChart.data.datasets[0]
        .data =
        magnitude;


    fftChart.update(
        "none"
    );

}


// ============================================================
// SENSOR DATA
// ============================================================

function handleSensorData(data) {

    if (!data)
        return;


    getElement(
        "ax-value"
    ).textContent =
        safeNumber(
            data.ax
        ).toFixed(3);


    getElement(
        "ay-value"
    ).textContent =
        safeNumber(
            data.ay
        ).toFixed(3);


    getElement(
        "az-value"
    ).textContent =
        safeNumber(
            data.az
        ).toFixed(3);


    getElement(
        "temperature-value"
    ).textContent =
        safeNumber(
            data.temperature
        ).toFixed(2);


    getElement(
        "last-update"
    ).textContent =
        new Date()
        .toLocaleTimeString();


    updateVibration(
        data
    );

}


// ============================================================
// PREDICTION
// ============================================================

function handlePrediction(data) {

    if (!data)
        return;


    const status =
        String(
            data.status || "SAFE"
        ).toUpperCase();


    const score =
        safeNumber(
            data.score
        );


    const health =
        Math.max(
            0,
            Math.min(
                100,
                safeNumber(
                    data.health,
                    100
                )
            )
        );


    // --------------------------------------------------------
    // STATUS
    // --------------------------------------------------------

    const prediction =
        getElement(
            "prediction-status"
        );


    prediction.textContent =
        status;


    prediction.className =
        "prediction " +
        status.toLowerCase();


    // --------------------------------------------------------
    // SCORE
    // --------------------------------------------------------

    getElement(
        "anomaly-score"
    ).textContent =
        score.toFixed(3);


    // --------------------------------------------------------
    // HEALTH
    // --------------------------------------------------------

    getElement(
        "health-score"
    ).textContent =
        health + "%";


    const healthFill =
        getElement(
            "health-fill"
        );


    healthFill.style.width =
        health + "%";


    if (health >= 70) {

        healthFill.style.background =
            "#27ae60";

    }
    else if (health >= 40) {

        healthFill.style.background =
            "#f39c12";

    }
    else {

        healthFill.style.background =
            "#e74c3c";

    }


    // --------------------------------------------------------
    // RECOMMENDATION
    // --------------------------------------------------------

    if (data.message) {

        getElement(
            "recommendation-box"
        ).textContent =
            data.message;

    }


    // --------------------------------------------------------
    // LAST UPDATE
    // --------------------------------------------------------

    getElement(
        "last-update"
    ).textContent =
        new Date()
        .toLocaleTimeString();

}


// ============================================================
// FEATURES
// ============================================================

function handleFeatures(data) {

    if (!data)
        return;


    getElement(
        "rms-value"
    ).textContent =
        safeNumber(
            data.rms
        ).toFixed(4);


    getElement(
        "energy-value"
    ).textContent =
        safeNumber(
            data.energy
        ).toFixed(4);


    getElement(
        "frequency-value"
    ).textContent =
        safeNumber(
            data.peak_frequency
        ).toFixed(2)
        + " Hz";


    getElement(
        "magnitude-value"
    ).textContent =
        safeNumber(
            data.peak_magnitude
        ).toFixed(4);


    getElement(
        "centroid-value"
    ).textContent =
        safeNumber(
            data.spectral_centroid
        ).toFixed(3);


    updateFFT(
        data
    );

}


// ============================================================
// BOARD STATUS
// ============================================================

function handleBoardStatus(data) {

    const element =
        getElement(
            "board-status"
        );


    if (
        data &&
        data.online
    ) {

        element.textContent =
            "● Board Online";

        element.className =
            "status-card online";

    }
    else {

        element.textContent =
            "● Board Offline";

        element.className =
            "status-card offline";

    }

}


// ============================================================
// HISTORY
// ============================================================

function handleHistory(data) {

    if (!data)
        return;


    const table =
        getElement(
            "history-table"
        );


    const row =
        document.createElement(
            "tr"
        );


    row.innerHTML = `

        <td>
            ${data.time || "--"}
        </td>

        <td>
            ${safeNumber(data.health, 100)}%
        </td>

        <td>
            ${data.status || "SAFE"}
        </td>

        <td>
            ${safeNumber(data.temperature).toFixed(2)}
            °C
        </td>

    `;


    table.prepend(
        row
    );


    // Keep only latest 20 entries

    while (
        table.children.length
        > 20
    ) {

        table.removeChild(
            table.lastChild
        );

    }

}


// ============================================================
// ERROR
// ============================================================

function showError(message) {

    const box =
        getElement(
            "error-container"
        );


    box.textContent =
        message;


    box.style.display =
        "block";


    setTimeout(
        () => {

            box.style.display =
                "none";

        },
        5000
    );

}


// ============================================================
// ARDUINO WEBUI CONNECTION
// ============================================================

function setupArduinoEvents() {

    /*
     * Arduino App Lab's WebUI uses the socket connection
     * provided by arduino.js.
     *
     * The exact global API can vary between App Lab versions,
     * therefore this section checks the available interface.
     */


    if (
        typeof Arduino !==
        "undefined"
    ) {

        if (
            Arduino.on
        ) {

            Arduino.on(
                "sensor_data",
                handleSensorData
            );

            Arduino.on(
                "prediction",
                handlePrediction
            );

            Arduino.on(
                "features",
                handleFeatures
            );

            Arduino.on(
                "board_status",
                handleBoardStatus
            );

            Arduino.on(
                "history",
                handleHistory
            );

        }

    }


    /*
     * Some App Lab versions expose the socket directly.
     */

    if (
        typeof io !==
        "undefined"
    ) {

        try {

            const socket =
                io();


            socket.on(
                "sensor_data",
                handleSensorData
            );


            socket.on(
                "prediction",
                handlePrediction
            );


            socket.on(
                "features",
                handleFeatures
            );


            socket.on(
                "board_status",
                handleBoardStatus
            );


            socket.on(
                "history",
                handleHistory
            );


        }
        catch (error) {

            console.log(
                "Socket setup:",
                error
            );

        }

    }

}


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        createVibrationChart();

        createFFTChart();

        setupArduinoEvents();

        console.log(
            "Bridge Predictive Maintenance UI initialized"
        );

    }
);
