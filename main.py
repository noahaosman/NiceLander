import machine
import time
import uos


### Define Constants
ADC_CF = 3.3/(65536)
AUX_BATT_DIV_RATIO = 1/(2/12.200)
MELT_2BATT_DIV_RATIO = 1/(1/17.2)

### Setup ouputs
stat_led = machine.Pin(25, machine.Pin.OUT)
led_b = machine.Pin(21, machine.Pin.OUT)
led_g = machine.Pin(20, machine.Pin.OUT)
led_r = machine.Pin(19, machine.Pin.OUT)
melt_sw = machine.Pin(13, machine.Pin.OUT)

### setup thruster control
thrust_on = 1
pwm = machine.PWM(machine.Pin(18))
pwm_freq = 200
pwm.freq(pwm_freq)
def thrust(thrust_bool):
    if thrust_bool == 1:
        frac = 0.6
    else:
        frac = 0.0
    pwm.duty_u16(int( pwm_freq*(0.000001)*(1500+frac*400)*(65535) ))
thrust(0)

### setup Inputs
reed_sw_on = machine.Pin(6, machine.Pin.IN, machine.Pin.PULL_DOWN)
reed_sw_off = machine.Pin(16, machine.Pin.IN, machine.Pin.PULL_DOWN)

### Setup Analog pins
analog_adc_0 = machine.ADC(26) # melt battery pin
analog_adc_1 = machine.ADC(27) # aux battery pin

#setup default outputs 
stat_led.off()
led_r.on()
led_g.on()
led_b.on()
melt_sw.off()
melt_tip_state = 0
tim = machine.Timer()
low_aux_battery = False
low_melt_battery = False
low_batterty_indicator_leds = []
start_time=0
    
def heartbeat(timer):
    global stat_led
    stat_led.toggle()

def read_adc(p):
    res = p.read_u16()
    return res*ADC_CF
    
def reed_sw_on_callback(p):
    global melt_tip_state
    global led_b
    global led_g
    global led_r
    global start_time
    global low_aux_battery
    global low_melt_battery
    global low_batterty_indicator_leds
    
    time.sleep_ms(10)
    if reed_sw_on.value() == 1:
        if not low_aux_battery and not low_melt_battery:
            if melt_tip_state == 0: #if melt stake is currently OFF
                print("")
                print("Initializing melt tip")
                thrust(thrust_on)
                print("    - Thruster ON")
                print("    - Waiting five seconds ... ", end =" ")
                for i in range(1,8):
                    led_g.on()
                    time.sleep_ms(500)
                    led_g.off()
                    time.sleep_ms(500)
                    if i < 8:
                        print(i, end =" ")
                    else:
                        print(8)
                start_time = time.time()
                melt_sw.on() # turn on melt tip
                print("    - Melt tip ON")  
                check_battery_voltage()
                melt_tip_state = 1
        else:
            for i in [1,0,1,0,1,0,1,0]:
                for led in low_batterty_indicator_leds:
                    if i == 1:
                        led.on()
                    else:
                        led.off()
                time.sleep_ms(150)
            

def reed_sw_off_callback(p):
    global melt_tip_state
    global led_g
    global start_time
    
    time.sleep_ms(10)
    if reed_sw_off.value() == 1:
        led_g.off() # turn off blue LED
        time.sleep_ms(100)
        led_g.on()
        time.sleep_ms(100)
        #print(p)
        if melt_tip_state == 1: # if melt stake is currently ON
            print("")
            print("Deactivating melt tip")
            melt_sw.off() # turn off melt tip
            print("    - Melt tip OFF")
            thrust(0)
            print("    - Thruster OFF")
            print("    - time on: ", time.time()-start_time," seconds")
            melt_tip_state = 0
    
def check_battery_voltage():
    global melt_tip_state
    global imon_offset
    global led_g
    global led_r
    global low_aux_battery
    global low_melt_battery
    global low_batterty_indicator_leds
    
    # Read battery voltages
    aux_batt_v = read_adc(analog_adc_1)*AUX_BATT_DIV_RATIO
    print("\rAuxiliary battery voltage =", aux_batt_v, "V    |    ", end='')
    melt_batt_V = read_adc(analog_adc_0)*MELT_2BATT_DIV_RATIO
    if melt_batt_V>46:
        print("Melt battery voltage > 46 V    ", end='')
    else:
        print("Melt battery voltage =", melt_batt_V, "V    ", end='')
        
    # if aux battery is low, shut things down
    if aux_batt_v > 13.5 - (1.5*float(melt_tip_state)):
        low_aux_battery = False
        led_b.on()
    else:
        low_aux_battery = True
        led_b.off()
        low_batterty_indicator_leds.append(led_b)
        print("!!!! LOW VOLTAGE -- recharge auxiliary battery !!!!", end='')
        if melt_tip_state == 1:
            print("turning thruster & melt tip OFF")
            reed_sw_off_callback(1)
            
    # if melt battery is low, shut things down
    if melt_batt_V>41.0:
        low_melt_battery = False
        led_r.on()
        print("                                                   ", end='')
    else:
        low_melt_battery = True
        led_r.off()
        low_batterty_indicator_leds.append(led_r)
        print("!!!! LOW VOLTAGE -- recharge melt tip battery !!!! ", end='')
        if melt_tip_state == 1:
            print("turning thruster & melt tip OFF")
            reed_sw_off_callback(1)
            
            
reed_sw_on.irq(trigger=machine.Pin.IRQ_RISING, handler=reed_sw_on_callback)

reed_sw_off.irq(trigger=machine.Pin.IRQ_RISING, handler=reed_sw_off_callback)

tim.init(freq=1.5, mode=machine.Timer.PERIODIC, callback=heartbeat)

while True:
    #if not low_aux_battery and not low_melt_battery:
    check_battery_voltage()
    time.sleep_ms(1000)
