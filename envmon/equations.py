def sea_level_pressure(altitude, pressure):
    '''
    Convert measured pressure to sea level pressure
    https://glossary.ametsoc.org/wiki/Sea_level_pressure

    :param float altitude: Altitude in meters
    :param float pressure: Pressure in hectopascals (hPa)
    '''

    return pressure * (293.0 / (293.0 - altitude * 0.0065))

def bytes_to_pressure(adc_raw: float, temp_fine: int, cal_buffer: list[float]):
    # Algorithm from the BMP280 driver
    # https://github.com/BoschSensortec/BMP280_driver/blob/master/bmp280.c
    var1 = float(temp_fine) / 2.0 - 64000.0
    var2 = var1 * var1 * cal_buffer[5] / 32768.0
    var2 = var2 + var1 * cal_buffer[4] * 2.0
    var2 = var2 / 4.0 + cal_buffer[3] * 65536.0
    var3 = cal_buffer[2] * var1 * var1 / 524288.0
    var1 = (var3 + cal_buffer[1] * var1) / 524288.0
    var1 = (1.0 + var1 / 32768.0) * cal_buffer[0]
    if not var1:  # avoid exception caused by division by zero
        raise ArithmeticError(
                "Invalid result possibly related to error while reading the calibration registers"
                )
    pressure = 1048576.0 - adc_raw
    pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
    var1 = cal_buffer[8] * pressure * pressure / 2147483648.0
    var2 = pressure * cal_buffer[7] / 32768.0
    pressure = pressure + (var1 + var2 + cal_buffer[6]) / 16.0
    pressure /= 100

