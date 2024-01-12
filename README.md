# ESP32 Force Sensor

Design of a program for an ESP32 that acquires data from an RP-C18.3-ST force sensor implemented in a flexible film. This program uses a CSV format text file as a database. In addition, it offers automatic time synchronization and storage functionality over WiFi. Synchronization can be done through an NTP server or by manually entering the date and time through a web page provided by the ESP32 server. This web page displays the last 10 readings saved in the database in a table and provides options to download the database in CSV format or delete it.

## Installation

* Install [Micropython](https://micropython.org/download/ESP32_GENERIC/)
* Upload the following files to ESP32 (you can use [Thonny](https://thonny.org/) or [esptool](https://pypi.org/project/esptool/))
  * ```main.py```
  * ```ssd1306.py```
  * ```gfx.py```
  * ```date.txt```
  * ```id_counter.txt```
* Make the connections as in the diagram
![Sketch](https://github.com/AlexXGAV/ESP32-Force-Sensor/blob/main/images/sketch.png?raw=true)

## Usage

* You can configure an access point from a cell phone or computer with internet to automatically synchronize the time, which must have the SSID and password the same as those programmed in ```main.py```.
Otherwise, esp32 will create an access point with the same credentials.
* The IP address will always be displayed on the screen so you can access the website.

## License

[MIT](https://choosealicense.com/licenses/mit/)
