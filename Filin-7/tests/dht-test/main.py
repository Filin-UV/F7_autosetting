import adafruit_dht
import board
import time
import subprocess
import RPi.GPIO as GPIO
##GPIO.setmode(GPIO.BOARD)

result = subprocess.run(['pgrep', 'libgpiod_pulse'], capture_output = True, text = True)
lines = result.stdout.split('\n')
for el in lines:
    result = subprocess.run(['kill', el], capture_output = True, text = True)
        
dht_device = adafruit_dht.DHT22(board.D24, use_pulseio = False)

#try:
t_c = dht_device.temperature
h = dht_device.humidity
    
print(t_c, h)
#except:
print('Error')
time.sleep(1)

dht_device.exit()