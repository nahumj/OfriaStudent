#!/usr/bin/env python3
import subprocess
from subprocess import call, check_call, check_output
import os.path
from os.path import exists
import functools
import os
import glob
import sys
import itertools
import re
import argparse
import contextlib
import collections

PROJECT_EXECUTABLE = "project0_cli.py"
TEST_SUITE_FOLDER = "Test_Suite"
TEST_FILES = ["Test_Suite/input_01.txt",
              "Test_Suite/input_02.txt"]
EXTRA_CREDIT_TEST_FILES = []
TEST_TIMEOUT = 5

def error(message):
    print(message, file=sys.stderr)
    exit(1)

TestOutcome = collections.namedtuple('TestOutcome', ['file', 'passed', 'output'])

class TestResult(Exception): pass

class TestFailed(TestResult): pass

class TestPassed(TestResult): pass

class InternalTestSuiteException(Exception):
    def __init__(self, message):
        super(InternalTestSuiteException, self).__init__(message)
        long_message = """
Test Suite or Script is broken:
{}
Contact instructors on Piazza so they can fix it (entirely their fault).
Please include this message and stack trace to assist debugging.""".format(message)
        self.args = [long_message]



def calculate_grade(outcomes, print_output=True):
    def grade_tests(file_token, test_to_passed, weight, proportional=False):
        score = 0
        pattern = re.compile(file_token)
        tests = []
        output = []
        output.append("Grading tests with {} in their name.".format(file_token))
        for test, passed in test_to_passed.items():
            if pattern.search(test):
                tests.append(passed)
        if not proportional:
            if all(tca_tests):
                score = weight
                output.append("All tests passed: {0} of {1} points".format(score, weight))
            else:
                output.append("Not all tests tests passed: {0} of {1} points".format(
                        score, weight))
            return output, score
        number_of_passes = sum(tests)
        number_of_tests = len(tests)
        output.append("Passed {} of {} tests.".format(number_of_passes, number_of_tests))
        score = weight * ( number_of_passes / number_of_tests )
        output.append("Proportional Score is: {} of {} points".format(score, weight))
        return output, score
        
    test_to_passed = {outcome.file : outcome.passed for outcome in outcomes}
    output = ["Grade Calculation (Provisional)"]
    total = 0

    criteria_name = "Pre-test checks for needed files: "
    if test_to_passed["has_needed_files"]:
        total += 1
        output += [criteria_name + "1 of 1 points"]
    else:
        output += [criteria_name + "0 of 1 points"]

    txt_output, txt_score = grade_tests(
        "input", test_to_passed, weight=1, proportional=True)
    output += txt_output
    total += txt_score
    if print_output:
        print("\n".join(output))
        print("Current tentative grade is: {} of 2 (not real points just demonstration)".format(total)) 
    return total



def rm(path):
    try:
        os.remove(path)
    except OSError:
        pass

def check_needed_files():
    if not exists("README.txt"):
        raise TestFailed(["Failed (README.txt file doesn't exist)"])


def call_and_get_output(args, timeout=None):
    try:
        output = check_output(args, stderr=subprocess.STDOUT,
                              universal_newlines=True, timeout=timeout)
        returncode = 0
    except subprocess.CalledProcessError as cpe:
        output = cpe.output
        returncode = cpe.returncode
    except subprocess.TimeoutExpired as te:
        output = ["Command: " + " ".join(args) + " took too long.\n",
                  "Process took longer than " + str(te.timeout) + " seconds. Killing.\n",
                  "Failed (execution took too long)"]
        raise TestFailed(output)
    except OSError as ose:
        output = ["Command: \"" + " ".join(args) + "\" raised OSError",
                  ose.strerror,
                  "Failed (couldn't run command {})".format(" ".join(args))]
        raise TestFailed(output)
        
    return output, returncode

def clean_up(paths):
    def wrap(func):
        @functools.wraps(func) 
        def wrapped(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                for path in paths:
                    rm(path)
                raise e
            return result
        return wrapped
    return wrap


#@clean_up(["ref.tca", "stu.tca", "ref.tic", "stu.tic"])
def run_test(test_file_path):

    @contextlib.contextmanager
    def add_lines_to_TestResult(lines):
        try:
            yield
        except TestResult as tr:
            tr.args = (lines + tr.args[0],)
            raise tr
    
    def check_if_files_created(output_path, correct_path):
        if not exists(correct_path):
            pass
            raise InternalTestSuiteException(
                "Test_Suite doesn't have a file named {}".format(correct_path))

        if not exists(output_path):
            raise TestFailed([
                "Falied (student executable didn't create {} file)".format(output_path)])

    def run_executable(args):
        command = ["./" + PROJECT_EXECUTABLE] + args 
        stdout, returncode = call_and_get_output(command, timeout=TEST_TIMEOUT)

        lines = ["Executable Output:", stdout,
                 "Executable Returncode:", str(returncode)]
        if returncode:
            lines += ["Failed (Executable returned a non-zero error code)"]
            raise TestFailed(lines)
        return lines

    def get_output_and_correct_path(test_path):
        output = "output_"
        num_ext = test_path.split("_")[-1]
        num = num_ext.partition(".")[0]
        output += num + ".txt"
        correct = os.path.join(TEST_SUITE_FOLDER, output)
        return output, correct

    
    def run_diff(output_path, correct_path):
        args = ["diff", "--text", output_path, correct_path]
        stdout, returncode = call_and_get_output(args, timeout=TEST_TIMEOUT)
        rm(output_path)
        if returncode == 0:
            raise TestPassed(["Passed ({} and {} match)".format(output_path, correct_path)])
        elif returncode == 1:
            lines = ["Diff Output:", stdout,
                     "Failed ({} and {} have differences)".format(output_path, correct_path)]
            raise TestFailed(lines)
        else:
            raise InternalTestSuiteException("""
Diff reports an error in comparing {} to {}. 
Diff output:
{}
            """.format(output_path, correct_path, stdout))
                             

    
    lines = ["Testing: " + test_file_path]
    with add_lines_to_TestResult(lines):
        output_path, correct_path = get_output_and_correct_path(test_file_path)
        lines += run_executable([test_file_path, output_path])
        check_if_files_created(output_path, correct_path)
        run_diff(output_path, correct_path)


def test_files_in_order(test_globs):
    for test_glob in test_globs:
        test_files = sorted(glob.glob(test_glob))
        for test_file in test_files:
            yield test_file

def get_test_result(test_file_path):
    try:
        run_test(test_file_path)
    except TestFailed as tf:
        passed = False
        output = tf.args[0]
    except TestPassed as tp:
        passed = True
        output = tp.args[0]
    else:
        message = "No TestResult Exception Raised On Test: {}".format(test_file_path)
        raise InternalTestSuiteException(message)
    return passed, output


def print_first_failure(outcomes):
    try:
        first_failure = next(itertools.dropwhile(
                lambda outcome: outcome.passed, outcomes))
    except StopIteration as si:
        print("No Failures To Display!")
    else:
        print("\n".join(first_failure.output))

def run_tests(test_globs):
    outcomes = []
    for test_file_path in test_files_in_order(test_globs):
        passed, output = get_test_result(test_file_path)
        outcome = TestOutcome(test_file_path, passed, output)
        outcomes.append(outcome)
    return outcomes
            
def get_cmd_args():
    parser = argparse.ArgumentParser(description="""
Tests the students code.
By default it tests all files in the Test_Suite and shows detailed output for the first failure.
""")
    parser.add_argument('--run-machine-mode', action="store_true", help="""
Outputs the test result as 1's and 0's. For instructor use only.
""")
    return parser.parse_args()



def get_all_outcomes(tests):
    all_outcomes = []

    check = try_to_outcome_wrapper("has_needed_files", check_needed_files)
    all_outcomes.append(check())

    tests = run_tests(tests)
    all_outcomes.extend(tests)
    return all_outcomes


def machine_mode():
    def print_outcomes(outcomes):
        lines = []
        for outcome in outcomes:
            file_basename = os.path.basename(outcome.file)
            passed = 1 if outcome.passed else 0
            lines.append("{}, {}".format(file_basename, passed))
        grade = calculate_grade(outcomes, print_output=False)
        lines.append("{}, {}".format("grade", grade))
        print("\n".join(lines))

    tests = TEST_FILES #+ EXTRA_CREDIT_TEST_FILES
    outcomes = get_all_outcomes(tests)
    print_outcomes(outcomes)


def try_to_outcome_wrapper(test_name, func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        passed = TestOutcome(test_name, True, ["Passed"])
        try:
            func(*args, **kwargs)
        except TestFailed as tf:
            return TestOutcome(test_name, False, tf.args[0])
        except TestPassed as tp:
            return passed
        else:
            return passed
    return wrapper


def normal_mode(args):
    print("Starting Tests...")
    sys.stdout.flush()

    tests = TEST_FILES
    outcomes = get_all_outcomes(tests)
    
    def passed_all(outcomes):
        return all(map(lambda outcome: outcome.passed, outcomes))        
    
    for outcome in outcomes:
        print("{:<40} {}".format(outcome.file, outcome.output[-1]))
    print()
    calculate_grade(outcomes, print_output=True)
    print()
    if passed_all(outcomes):
        print("Passes all tests!")
        exit(0)
    else:
        print("\nFirst Failure's Details:")
        print_first_failure(outcomes)
        exit(1)

def main():
    args = get_cmd_args()
    if args.run_machine_mode:
        machine_mode()
    else:
        normal_mode(args)

if __name__ == "__main__":
    main()
