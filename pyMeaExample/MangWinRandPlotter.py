import logging
from datetime import datetime, timedelta

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

import sys
import tempfile
import random
from time import sleep
from pymeasure.log import console_log
from pymeasure.display.Qt import QtGui
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import Procedure, Results, IntegerParameter, FloatParameter, Parameter, unique_filename


class RandomProcedure(Procedure):
    iterations = IntegerParameter('Loop Iterations')
    delay = FloatParameter('Delay Time', units='s', default=0.2)
    seed = Parameter('Random Seed', default='12345')

    DATA_COLUMNS = ['Iteration', 'Random Number']

    def startup(self):
        log.info("Setting the seed of the random number generator")
        random.seed(self.seed)

    def execute(self):
        log.info("Starting the loop of %d iterations" % self.iterations)
        for i in range(self.iterations):
            data = {
                'Iteration': i,
                'Random Number': random.random()
            }
            self.emit('results', data)
            log.debug("Emitting results: %s" % data)
            self.emit('progress', 100 * i / self.iterations)
            sleep(self.delay)
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break

    def get_estimates(self, sequence_length=None, sequence=None):

        duration = self.iterations * self.delay

        estimates = [
            ("Duration", "%d s" % int(duration)),
            ("Number of lines", "%d" % int(self.iterations)),
            ("Sequence length", str(sequence_length)),
            ('Measurement finished at', str(datetime.now() + timedelta(seconds=duration))),
        ]

        return estimates

class MainWindow(ManagedWindow):

    def __init__(self):
        super().__init__(
            procedure_class=RandomProcedure,
            inputs=['iterations', 'delay', 'seed'],
            displays=['iterations', 'delay', 'seed'],
            x_axis='Iteration',
            y_axis='Random Number',

            sequencer=True,  # Added line
            sequencer_inputs=['iterations', 'delay', 'seed'],
            # sequence_file = "gui_sequencer_example_sequence.txt",  # Added line, optional
            directory_input=True,  # Added line, enables directory widget
            inputs_in_scrollarea=True,  # Added line
        )
        self.setWindowTitle('GUI Example')
        # self.directory = 'C:\\Users\\wanghubing\\PycharmProjects\\IV_py39\\pyMeaExample\\directory'  # Added line, sets default directory for GUI load
        # self.directory = r'C:\directory'
    def queue(self, procedure=None):
        # filename = tempfile.mktemp()
        directory = self.directory  # Added line
        filename = unique_filename(directory)  # Modified line

        if procedure is None:
            procedure = self.make_procedure()
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
