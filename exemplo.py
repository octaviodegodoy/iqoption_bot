from iqoptionapi.stable_api import IQ_Option
import os
import logging, json, sys, time

from talib._ta_lib import MA_Type
from talib.abstract import *
import numpy as np

API = IQ_Option(os.environ.get('IQ_USER'), os.environ.get('IQ_PASSWORD'))
API.connect()

API.change_balance('PRACTICE')

if API.check_connect():
    print('\n\n Conectado com sucesso !!')
else:
    print('\n Erro ao conectar !')
    sys.exit()

TURBO = 'turbo'
DIGITAL = 'digital'
OPEN = 'open'
TF = 1
CANDLE_SIZE = 'candle_size'


def payout(par, tipo, timeframe):
    if tipo == TURBO:
        a = API.get_all_profit()
        return int(100 * a[par][TURBO])
    elif tipo == DIGITAL:
        API.subscribe_strike_list(par, timeframe)
        while True:
            d = API.get_digital_current_profit(par, timeframe)
            if d:
                d = int(d)
                break
            time.sleep(1)
        API.unsubscribe_strike_list(par, timeframe)
        return d


def get_indicator(par, timeframe, ind_name):
    indicators = API.get_technical_indicators(par)
    for dado in indicators:
        if CANDLE_SIZE in dado and dado[CANDLE_SIZE] == (timeframe * 60):
            if dado['name'] == ind_name:
                return dado['value']


def processa_operacao_ativo(par):
    API.start_candles_stream(par, 60, 280)
    velas = API.get_realtime_candles(par, 60)
    preco_atual = get_current_price(velas)
    up, mid, low = calcula_bollinger(velas, 8)
    sma_3 = calcula_sma(velas, 3)
    sma_8 = calcula_sma(velas, 8)
    sma_20 = calcula_sma(velas, 20)
    if sma_3 and sma_8 and sma_20:
        sma_3_sma_8_perc = sma_3 / sma_8
        sma_8_sma_20_perc = sma_8 / sma_20
        if sma_3_sma_8_perc < 1 and sma_8_sma_20_perc > 1 and preco_atual < sma_3 and preco_atual < low:
            print('Valor SMA 20,8,3 ' + str(sma_3_sma_8_perc) + ',' + str(sma_8_sma_20_perc))
            executa_call(par)
    time.sleep(1)
    API.stop_candles_stream(par, 60)


def get_current_price(velas):
    for vela in velas:
        if 'active_id' in velas[vela]:
            preco_ativo = velas[vela]
    preco_atual = (preco_ativo['ask'] + preco_ativo['bid']) / 2
    return preco_atual


def calcula_bollinger(velas, periodo):
    valores = {'open': np.array([]), 'high': np.array([]), 'low': np.array([]), 'close': np.array([]),
               'volume': np.array([])}

    for x in velas:
        valores['open'] = np.append(valores['open'], velas[x]['open'])
        valores['high'] = np.append(valores['high'], velas[x]['max'])
        valores['low'] = np.append(valores['low'], velas[x]['min'])
        valores['close'] = np.append(valores['close'], velas[x]['close'])
        valores['volume'] = np.append(valores['volume'], velas[x]['volume'])
    bbands = Function('bbands', valores)
    bbands.parameters = {
        'timeperiod': periodo,
        'nbdevup': 2.0,
        'nbdevdn': 2.0
    }
    upper, middle, lower = bbands()
    return upper[-1], middle[-1], lower[-1]


def calcula_sma(velas, periodo):
    valores = {'open': np.array([]), 'high': np.array([]), 'low': np.array([]), 'close': np.array([]),
               'volume': np.array([])}

    for x in velas:
        valores['open'] = np.append(valores['open'], velas[x]['open'])
        valores['high'] = np.append(valores['high'], velas[x]['max'])
        valores['low'] = np.append(valores['low'], velas[x]['min'])
        valores['close'] = np.append(valores['close'], velas[x]['close'])
        valores['volume'] = np.append(valores['volume'], velas[x]['volume'])

    calculo_sma = SMA(valores, timeperiod=periodo)
    return calculo_sma[-1]


def executa_call(paridade):
    print('Executando call para ' + str(paridade))
    status, id = API.buy(100, paridade, 'call', 1)

    if status:
        lucro = 0
        while True:
            try:
                status, valor = API.check_win_v3(id)
            except:
                status = True
                valor = 0

            if status:
                valor = valor if valor > 0 else float('-' + str(abs(100)))
                lucro += round(valor, 2)

                print('Resultado operação: ', end='')
                print('WIN /' if valor > 0 else 'LOSS /', round(valor, 2), '/', round(lucro, 2))

                break
    else:
        print('\nERRO AO REALIZAR OPERAÇÃO\n\n')


par = API.get_all_open_time()

while True:
    for paridade in par[TURBO]:
        if par[TURBO][paridade][OPEN]:
            print('Verificando sinal ativo ' + paridade)
            processa_operacao_ativo(paridade)
            print('Paridade TURBO disponivel ' + paridade + ' payout : ' + str(
                payout(paridade, TURBO, TF)))

"""
for paridade in par[DIGITAL]:
    if par[DIGITAL][paridade][OPEN]:
        ema5_value = get_indicator(paridade, TF, EMA5)
        ema10_value = get_indicator(paridade, TF, EMA10)
        ema20_value = get_indicator(paridade, TF, EMA20)
        if ema5_value and ema10_value and ema20_value:
            print('Paridade DIGITAL disponivel ' + paridade + ' payout : ' + str(
                payout(paridade, DIGITAL, TF)) + ' EMA 5 : ' + str(ema5_value) + ' EMA 10 : ' + str(
                ema10_value) + ' EMA 20 : ' + str(ema20_value))
"""
