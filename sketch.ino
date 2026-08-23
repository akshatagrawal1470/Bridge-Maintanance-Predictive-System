#include <Arduino.h>
#include <Arduino_RouterBridge.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

Adafruit_MPU6050 mpu;

// ============================================================
// CONFIGURATION
// ============================================================

#define SAMPLE_RATE_HZ 100
#define SAMPLE_PERIOD_MS 10

// Number of samples returned to Python per Bridge call
#define BATCH_SIZE 10


// ============================================================
// GET SENSOR BATCH
// ============================================================
//
// The MPU6050 is sampled at 100 Hz.
// 10 samples are collected internally.
// Python receives the entire batch.
//
// Therefore:
//
// 100 samples/sec
// 10 samples/batch
// = approximately 10 Bridge calls/sec
//
// ============================================================

String get_sensor_batch(String args)
{
    String json = "[";

    for (int i = 0; i < BATCH_SIZE; i++)
    {
        sensors_event_t accel;
        sensors_event_t gyro;
        sensors_event_t temp;

        mpu.getEvent(
            &accel,
            &gyro,
            &temp
        );

        // Convert m/s² -> g
        //
        // IMPORTANT:
        // Your Edge Impulse model must use the same
        // units that were used during training.
        //
        float ax_g =
            accel.acceleration.x ;

        float ay_g =
            accel.acceleration.y;

        float az_g =
            accel.acceleration.z ;

        // ----------------------------------------------------
        // JSON SAMPLE
        // ----------------------------------------------------

        json += "{";

        json += "\"ax\":";
        json += String(ax_g, 6);
        json += ",";

        json += "\"ay\":";
        json += String(ay_g, 6);
        json += ",";

        json += "\"az\":";
        json += String(az_g, 6);
        json += ",";

        json += "\"gx\":";
        json += String(
            gyro.gyro.x,
            6
        );
        json += ",";

        json += "\"gy\":";
        json += String(
            gyro.gyro.y,
            6
        );
        json += ",";

        json += "\"gz\":";
        json += String(
            gyro.gyro.z,
            6
        );
        json += ",";

        json += "\"temperature\":";
        json += String(
            temp.temperature,
            2
        );

        json += "}";

        if (i < BATCH_SIZE - 1)
        {
            json += ",";
        }

        // ----------------------------------------------------
        // 100 Hz sampling
        // ----------------------------------------------------

        delay(
            SAMPLE_PERIOD_MS
        );
    }

    json += "]";

    return json;
}


// ============================================================
// SETUP
// ============================================================

void setup()
{
    Serial.begin(115200);

    Wire.begin();

    // --------------------------------------------------------
    // MPU6050
    // --------------------------------------------------------

    if (!mpu.begin())
    {
        Serial.println(
            "MPU6050 NOT FOUND!"
        );

        while (1)
        {
            delay(1000);
        }
    }

    // --------------------------------------------------------
    // Accelerometer
    // --------------------------------------------------------

    mpu.setAccelerometerRange(
        MPU6050_RANGE_8_G
    );

    // --------------------------------------------------------
    // Gyroscope
    // --------------------------------------------------------

    mpu.setGyroRange(
        MPU6050_RANGE_500_DEG
    );

    // --------------------------------------------------------
    // Digital Low Pass Filter
    // --------------------------------------------------------

    mpu.setFilterBandwidth(
        MPU6050_BAND_21_HZ
    );

    // --------------------------------------------------------
    // Router Bridge
    // --------------------------------------------------------

    Bridge.begin();

    Bridge.provide(
        "get_sensor_batch",
        get_sensor_batch
    );

    Serial.println(
        "================================"
    );

    Serial.println(
        "MPU6050 + RouterBridge READY"
    );

    Serial.println(
        "Sampling: 100 Hz"
    );

    Serial.println(
        "Batch size: 10"
    );

    Serial.println(
        "================================"
    );
}


// ============================================================
// LOOP
// ============================================================

void loop()
{
    // Python requests the data batches.
    //
    // No continuous processing is required here.

    delay(10);
}
