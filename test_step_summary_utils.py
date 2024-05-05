"""
Contains test_step_summary_utils.test_step_summary_utils.TestStepSummaryUtils class
author: balaji.ramansv@gmail.com
"""
# From python lib
import string
import traceback
import logging
from prettytable import ALL, PrettyTable
from datetime import datetime
from contextlib import contextmanager

# Global constants
ES_FAILURES_COL_WIDTH = 40
ES_DESCRIPTION_COL_WIDTH = 50
SUMMARY_FAILURES_COL_WIDTH = 35
SUMMARY_DESCRIPTION_COL_WIDTH = 45

class TestStepSummaryUtils(object):
    """@Class TestStepSummaryUtils
       Class to aid keeping track of steps and to do some pretty printing
       of test execution summary.
    """

    def __init__(self, *, steps, logger=None):
        """
        Constructor to initialize TestStepSummaryUtils.

        Required:
            steps - A tuple (as it is immutable) of steps
        Optional:
            logger - a logging insstance to log the outcome of this class
        Returns:
            None
        """

        if logger is None:
            self.logger = logging.getLogger(__name__)
            logging.basicConfig(level=logging.DEBUG)
        else:
            self.logger = logger
        self.logger.info('TestStepSummaryUtils initialized')
        # Check if the 'steps' passed is a tuple and assign it to a local
        # instance
        assert isinstance(steps, tuple) == True, \
            "'steps' arg passed to {}:{} to must be a tuple.".format(
                self.__class__.__name__, '__init__()')
        self.steps = steps
        # ---Initializations---
        # To track the ongoing or current step
        self.current_step = 0
        # To keep track of failed steps
        self.failed_steps = []
        # To mean that a step has started and is ongoing. False for this
        # flag means that the step has ended
        self.step_start = True
        # This will be true only for the first start_step() call to
        # differentiate the 1st step from the subsequent steps.
        self.first_start = True
        # Table which we print at the start of the test will have fields as
        # below
        start_test_field_names = ['STEP', 'TIME', 'DESCRIPTION']
        self.step_start_table = PrettyTable()
        self.step_start_table.field_names = start_test_field_names
        # Table which we print at the end of the test will have fields as
        # below
        end_test_field_names = \
            ['STEP', 'TIME', 'DESCRIPTION', 'RESULT', 'FAILURES']
        self.step_end_table = PrettyTable()
        self.step_end_table.field_names = end_test_field_names
        # Below summary table is a consolidation all steps.
        # We record these fields at the end of each step and print it
        # when called.
        summary_field_names = \
            ['STEP', 'S_TIME E_TIME', 'ELAPSED_TIME', 'DESCRIPTION', 'RESULT',
                'FAILURES']
        self.summary_table = PrettyTable()
        self.summary_table.field_names = summary_field_names
        for table in [self.summary_table, self.step_start_table,
                self.step_end_table]:
            # left align
            table.align = 'l'
            # ALL = both vertical and horizontal lines
            # This is like selecting all borders in a spreadsheet
            table.hrules = ALL

    def start_step(self, *, end_script_on_failure=False):
        """
        This method prints a table to inform that a step has started.

        Optional:
            end_script_on_failure   -   Boolean.
                                        True if test script should be exited if
                                        the step has failed. False otherwise.
                                        Defaults to False.
                                        False
        """
        assert self.step_start == False or self.first_start == True, \
            'Previous ended abruptly. Perhaps the end_step() was not ' \
            'called to end the previous step.'
        self.end_script_on_failure = end_script_on_failure
        self.step_start = True
        self.step_failures = ''
        self.first_start = False
        self.start_time = self.__get_current_time()
        self.step_start_table.add_row(
            [self.current_step+1,
                self.start_time.strftime('%H:%M:%S'),
                self.__wrap_text(self.steps[self.current_step], 100)])
        self.logger.info("\n\n" + str(self.step_start_table) + "\n\n")
        self.step_start_table.clear_rows()

    def end_step(self, *, result, failures=None):
        """
        This method prints the result of a step in the form of a table using
        the passed values.

        Required:
            result                  -   Result of the test like 'PASS', 'FAIL',
                                        etc.

        Optional:
            failures                -   String to print in the failure column.
                                        Defaults to None
        """
        assert self.step_start == True, 'end_step() called before start_step().'
        self.step_start = False
        self.end_time = self.__get_current_time()
        # Fail if invalid results are provided
        valid_results = ['PASS', 'FAIL', 'NOT RUN', 'UNKNOWN']
        assert result in valid_results, \
            "{} is an invalid value for result. Valid values are {}."\
                .format(result, valid_results)
        if result == 'FAIL':
            # Mandate printing the failures in the FAILURES column when the
            # result is 'FAIL'
            assert failures is not None, \
                "Failures column can't be blank when the result is 'FAIL'."
            self.failed_steps.append({
                    'STEP': self.current_step+1,
                    'DESCRIPTION': self.steps[self.current_step],
                    'FAILURE': failures
                }
            )
        if not isinstance(failures, str):
            failures = str(failures)
        end_result_row = [self.current_step+1,
                        self.end_time.strftime('%H:%M:%S'),
                        self.__wrap_text(self.steps[self.current_step],
                            ES_DESCRIPTION_COL_WIDTH),
                        result,
                        self.__wrap_text(failures, ES_FAILURES_COL_WIDTH)]
        # print the result table of the step, now that we are at the end of the
        # step
        self.step_end_table.add_row(end_result_row)
        self.logger.info("\n\n" + str(self.step_end_table) + "\n\n")
        self.step_end_table.clear_rows()
        start_end_time = '{}\n{}'.format(
            self.start_time.strftime('%H:%M:%S'),
            self.end_time.strftime('%H:%M:%S'))
        diff = self.end_time - self.start_time
        elapsed_time = str(diff).split('.')[0]
        # add this to the summary table to print at the end of the test suite
        summary_result_row = [self.current_step+1,
                                start_end_time,
                                elapsed_time,
                                self.__wrap_text(
                                    self.steps[self.current_step],
                                    SUMMARY_DESCRIPTION_COL_WIDTH),
                                result,
                                self.__wrap_text(
                                    failures,
                                    SUMMARY_FAILURES_COL_WIDTH)]
        self.summary_table.add_row(summary_result_row)
        self.current_step += 1
        assert not (result == 'FAIL' and self.end_script_on_failure), \
            'Test step {} failed. Check the end result table for more details.'\
            .format(self.current_step)

    def update_error(self, error):
        self.step_failures += error

    @contextmanager
    def next_step(self, *, end_script_on_failure=False):
        error = False
        try:
            self.start_step(end_script_on_failure=end_script_on_failure)
            yield
            assert self.step_failures == '', 'Errors found in step.'
        except Exception as e:
            error = True
            tb_err_str = ''
            if 'Errors found in step' not in str(e):
                tb_err_str = traceback.format_exc()
            failure_msg = self.step_failures + tb_err_str
            self.end_step(result='FAIL', failures=failure_msg)
        if not error:
            self.end_step(result='PASS')

    def print_summary(self):
        """
        This method can be used to print the summary at the end of the script
        in table format.
        """
        remaining_steps = self.steps[self.current_step:]
        start_time = 'NA'
        for ix, remaining_step in enumerate(remaining_steps):
            result = ''
            # when step started but did not end (end_step() not called).
            if ix == 0 and self.step_start:
                result = 'UNKNOWN'
                start_time = self.start_time
            else:
                result = 'NOT RUN'
            # When a step ends abruptly without end_step()
            # or when end_step() is called with end_script_on_failure=True,
            # for the rest of the steps we want to say Not Applicable (NA) in
            # failures.
            result_row = [self.current_step+1,
                start_time,
                'NA',
                self.__wrap_text(self.steps[self.current_step],
                    SUMMARY_DESCRIPTION_COL_WIDTH),
                result,
                'NA']
            self.logger.info(result_row)
            self.summary_table.add_row(result_row)
            self.current_step += 1
        self.logger.info("\n\n" + str(self.summary_table) + "\n\n")

    def get_failed_steps(self):
        """
        Method to return the failed steps.
        """
        return self.failed_steps

    def __wrap_text(self, text, width, *, delimiter=' '):
        """
        Method to wrap text within the fixed width. We need this because
        DESCRIPTION and FAILURES can be long strings that ends up breaking
        the table structure.

        Returns:
            Wrapped text.
        """
        words = text.split(delimiter)
        line_text = ''
        lines = []
        for ix, word in enumerate(words):
            if '/' in word:
                with_path = line_text + word
                wt = self.__wrap_text(with_path, width, delimiter="""/""")
                line_text = wt
                word = ''
            line_len = len(line_text) + len(word)
            if line_len > width:
                lines.append(line_text)
                line_text = ''
            if '\n' in word:
                line_text += word.rstrip()
                lines.append(line_text)
                line_text = ''
            else:
                line_text += word + delimiter
            if ix+1 == len(words):
                line_text = line_text.strip(delimiter)
                lines.append(line_text)
        wrapped_text = '\n'.join(lines)
        return wrapped_text

    def __get_current_time(self):
        """
        Method to return time.
        """
        return datetime.now()
