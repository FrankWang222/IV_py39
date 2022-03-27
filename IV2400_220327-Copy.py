"""
这个脚本用于测量 TES 的 I-V 曲线，采用2400源表的四端测量法。

一、脚本使用
1. I为Keithley2400加的偏置电流，V为SQUID的读出电压，i_TES为换算后的TES电流，v_TES为换算后的TES电压。

二、参数的设置和使用
需要设置的参数有7个GUI界面参数
1.Keithley2400（默认GPIB：24）:
    Source Limit Current: 电压源2400的输出range。请设置成略高于整个测量中所需的最大输出电流。
    Source Compliance Voltage: 是2400作为电流源的 compliance voltage。请设置成略高于整个测量中所需的最大输出电压。
    Source Start Current: 扫描电流的起始值
    Source Step Current: 扫描电流的步长
    Source End Current: 扫描电流的终止值
2.其它参数
    Temperature: 扫描IV时的工作温度
    TES name: 器件编号
"""

import logging

log = logging.getLogger('_name_')
log.addHandler(logging.NullHandler())

import sys
import numpy as np

from pymeasure.instruments.keithley import Keithley2400
from pymeasure.display.Qt import QtGui
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import Procedure, IntegerParameter, FloatParameter, unique_filename, Results


class fourwires(Procedure):
    # 测量参数：
    # 电压源 Keithley2400:
    limitI = FloatParameter('Source Limit Current', units='mA', default=3)
    cmplV = FloatParameter('Source Compliance Voltage', units='V', default=10)
    startI = FloatParameter('Source Start Current', units='uA', default=0)
    endI = FloatParameter('Source End Current', units='uA', default=3000)
    stepI = FloatParameter('Source Step Current', units='uA', default=1)
    name = IntegerParameter('TES name', units='TES', default=1)
    temp = FloatParameter('Temperature', units='mK', default=100)

    DATA_COLUMNS = ['I (A)', 'V (V)', 'I_TES (A)', 'V_TES (V)']

    def startup(self):
        # 链接仪器： Keithley2400
        self.source = Keithley2400('GPIB::23')

        # 配置仪器
        self.source.reset()
        self.source.wires = 4
        self.source.apply_current(current_range=self.limitI * 1e-3, compliance_voltage=self.cmplV)
        self.source.measure_voltage(nplc=1, voltage=self.cmplV, auto_range=False)

    def execute(self):
        # listI = np.arange(self.startI, self.endI, self.stepI) * 1e-6

        listIup = np.arange(self.startI, self.endI+self.stepI, self.stepI) * 1e-6
        listIdown = np.arange(self.endI, self.startI-self.stepI, -self.stepI) * 1e-6
        listI = np.concatenate([listIup, listIdown], axis=0)

        # 正反扫描电流
        # listIup = np.arange(self.startI, self.endI, self.stepI) * 1e-6
        # listIcenter = np.arange(self.endI, -self.endI, -self.stepI) * 1e-6
        # listIdown = np.arange(-self.endI, self.startI, self.stepI) * 1e-6
        # listI = np.concatenate([listIup, listIcenter, listIdown], axis=0)

        self.source.source_current = 0
        self.source.enable_source()

        for index, i in enumerate(listI):
            self.source.ramp_to_current(target_current=i, steps=3, pause=5e-3)

            v = self.source.voltage
            if i == 0:
                offset = v
                print('offset:', offset)
            # 扣除SQUID的输出电压offset
            v = v - offset
            #print('length1:', len(listI))
            #SQUID反馈电路高灵敏度：0.06---100kohm, SQUID反馈电路中灵敏度：0.006---10kohm, Rshunt = 250uohm
            i_TES = v / 0.006 * 1e-6
            v_TES = 250 * 1e-6 * (i - i_TES)
            data = {
                'I (A)': i,
                'V (V)': v,
                'I_TES (A)': i_TES,
                'V_TES (V)': v_TES
            }
            self.emit('results', data)
            self.emit('progress', 100. * index / len(listI))
            if self.should_stop():
                log.warning("Catch stop command！")
                break

    def shutdown(self):
        self.source.shutdown()
        log.info('Finished!')


class FourWiresWindow(ManagedWindow):
    EDITOR = 'notepad'

    def __init__(self):
        super().__init__(
            procedure_class=fourwires,
            inputs=[
                'limitI', 'cmplV', 'startI', 'endI', 'stepI', 'temp', 'name'
            ],
            displays=[
                'limitI', 'cmplV', 'startI', 'endI', 'stepI', 'temp', 'name'
            ],
            x_axis='I (A)',
            y_axis='V (V)',
        )

        self.setWindowTitle('I-V Measurement')

    def queue(self):
        directory = './'
        # filename = unique_filename(directory, prefix='I-V-' + str(getattr(self.inputs, 'temp').parameter.value) + 'mk-')
        filename = unique_filename(directory, prefix=str(getattr(self.inputs, 'name').parameter) + '-IV-' +
                                                     str(getattr(self.inputs, 'temp').parameter) + '-')
        procedure = self.make_procedure()

        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = FourWiresWindow()
    window.show()
    sys.exit(app.exec_())
