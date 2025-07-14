import time
import json
import network
import socket

from umqtt.simple import MQTTClient
from pms5003 import PMS5003
from machine import Pin, I2C, UART
from ssd1306 import SSD1306_I2C

led = Pin("LED", machine.Pin.OUT)
led.on()


def led_signal_error():
    while True:
        led.toggle()
        time.sleep_ms(250)


def init_oled():
    pix_res_x = 128  # SSD1306 horizontal resolution
    pix_res_y = 32  # SSD1306 vertical resolution

    i2c_dev = I2C(
        1, scl=Pin(27), sda=Pin(26), freq=200000
    )  # start I2C on I2C1 (GPIO 26/27)
    i2c_addr = [hex(ii) for ii in i2c_dev.scan()]  # get I2C address in hex format
    if i2c_addr == []:
        print("No I2C Display Found")
        return None
    else:
        print("I2C Address      : {}".format(i2c_addr[0]))  # I2C device address
        print("I2C Configuration: {}".format(i2c_dev))  # print I2C params
        return SSD1306_I2C(pix_res_x, pix_res_y, i2c_dev)


def print_message(oled, msg):
    if oled is None:
        led.toggle()
        return

    oled.fill(0)
    oled.text(msg, 0, 0)
    oled.show()


def init_wifi():
    ssid = "Ceci nest pas une wifi"
    password = "LaTrahisonDesImages"

    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(ssid, password)

        # Wait for connect or fail
        max_wait = 100
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            print("waiting for connection...")
            time.sleep(1)

        # Handle connection error
        if wlan.status() != 3:
            raise RuntimeError("network connection failed")
        else:
            print("connected")
            status = wlan.ifconfig()
            print("ip = " + status[0])
    except:
        print_message(oled, "Network error")
        led_signal_error()


def show_data(oled, data, next_data_in_sec):
    if oled is None:
        led.toggle()
        return

    oled.fill(0)

    if "pm1_0" in data:
        oled.text(f"PM1.0  {data['pm1_0']:.1f}", 0, 0)
        oled.text(f"PM2.5  {data['pm2_5']:.1f}", 0, 8)
        oled.text(f"PM10   {data['pm10']:.1f}", 0, 16)
    else:
        oled.text("Waiting for data", 0, 0)

    oled.text(f"Next in {next_data_in_sec}", 0, 24)
    oled.show()


def main():
    oled = init_oled()

    if oled is not None:
        led.off()

    print_message(oled, "Init driver...")

    # Configure the PMS5003
    pms5003 = PMS5003(
        uart=UART(1, tx=Pin(8), rx=Pin(9), baudrate=9600),
        pin_enable=Pin(16),
        pin_reset=Pin(19),
        mode="active",
    )

    print_message(oled, "Setup network...")

    # setup wifi
    init_wifi()

    mqtt = MQTTClient("pms5003", "raspberrypi", port=1883, keepalive=30)
    mqtt.connect()

    print_message(oled, "Getting data...")

    smooth_steps = 60

    accum = {"pm1_0": [], "pm2_5": [], "pm10": []}

    smooth_data = {}

    while True:
        data = pms5003.read()
        # print(data)

        pm1 = data.pm_ug_per_m3(1.0)
        pm2_5 = data.pm_ug_per_m3(2.5)
        pm10 = data.pm_ug_per_m3(10)

        data_obj = {"pm1_0": pm1, "pm2_5": pm2_5, "pm10": pm10}

        for size, vals in accum.items():
            vals.append(data_obj[size])

        if len(accum["pm10"]) == smooth_steps:
            for size, vals in accum.items():
                smooth_data[size] = sum(vals) / len(vals)
                accum[size] = []

            mqtt.publish(
                "home/living_room/pms5003_json_smooth", json.dumps(smooth_data)
            )

        show_data(oled, smooth_data, smooth_steps - len(accum["pm10"]))

        mqtt.publish("home/living_room/pms5003/heartbeat", "pong")

        time.sleep(1.0)


main()
