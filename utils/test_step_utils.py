# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import MagicMock
import streamlit as st
from utils.step_utils import BaseFlowStep, StepConfigException

class TestFlowStep(BaseFlowStep):
    """ Stub flow step for testing """

    def do(self, step_config, state_dict, step_status):
        pass

class TestBaseFlowStepKeyMgmt(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.step = TestFlowStep("test_step", self.mock_app, {"default_key": "default_value"})
        st.session_state = {}

    def test_get_unique_key_prefix(self):
        self.assertEqual(self.step.get_unique_key_prefix(True), "pdata_test_step")
        self.assertEqual(self.step.get_unique_key_prefix(False), "vdata_test_step")

    def test_get_output_key(self):
        self.assertEqual(self.step.get_output_key(), "pdata_test_step_output_key")

    def test_format_internal_key(self):
        formatted_key = self.step.format_internal_key(True, "arg1", "arg2")
        self.assertEqual(formatted_key, "pdata_test_step_arg1_arg2")
        formatted_key = self.step.format_internal_key(False, "arg1", "arg2")
        self.assertEqual(formatted_key, "vdata_test_step_arg1_arg2")
        with self.assertRaises(ValueError):
            self.step.format_internal_key(True)

    def test_get_internal_keys(self):
        st.session_state["pdata_test_step_key1"] = "value1"
        st.session_state["vdata_test_step_key2"] = "value2"
        st.session_state["pdata_test_step_output_key"] = "output"
        st.session_state["other_key"] = "other"

        keys = self.step.get_internal_keys()
        self.assertEqual(set(keys), {"pdata_test_step_key1", "vdata_test_step_key2"})

        keys = self.step.get_internal_keys(include_pdata=False)
        self.assertEqual(set(keys), {"vdata_test_step_key2"})

        keys = self.step.get_internal_keys(include_vdata=False)
        self.assertEqual(set(keys), {"pdata_test_step_key1"})

    def test_get_output_subkeys(self):
        self.assertEqual(self.step.get_output_subkeys(), [])

class TestBaseFlowStep(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_app.get_step_config.return_value = {}
        self.step = TestFlowStep("test_step", self.mock_app, {"default_key": "default_value"})

    def test_init(self):
        self.assertEqual(self.step.name, "test_step")
        self.assertEqual(self.step.app, self.mock_app)
        self.assertEqual(self.step.step_config, {"default_key": "default_value"})

    def test_get_depends_on(self):
        self.step.step_config["depends_on"] = {"dep1": "step1", "dep2": "step2"}
        self.assertEqual(self.step.get_depends_on(), {"dep1": "step1", "dep2": "step2"})
        self.assertEqual(self.step.get_depends_on("dep1"), "step1")

    def test_get_depends_on_exception(self):
        self.step.step_config["depends_on"] = {"dep1": "step1"}
        with self.assertRaises(StepConfigException):
            self.step.get_depends_on("non_existent")

    def test_format_internal_key(self):
        formatted_key = self.step.format_internal_key(True, "arg1", "arg2")
        self.assertEqual(formatted_key, "pdata_test_step_arg1_arg2")
        formatted_key = self.step.format_internal_key(False, "arg1", "arg2")
        self.assertEqual(formatted_key, "vdata_test_step_arg1_arg2")

    def test_get_output_key(self):
        self.assertEqual(self.step.get_output_key(), "pdata_test_step_output_key")

if __name__ == '__main__':
    unittest.main()
