# pylint: disable=C0116
import unittest
import test_helper
test_helper.setup_path()
import unittest
import streamlit as st
from unittest.mock import MagicMock, patch
from utils.step_utils import BaseFlowStep, BaseFlowStep_key_mgmt, StepConfigException

class TestFlowStep(BaseFlowStep_key_mgmt):
    def __init__(self, name):
        self._name = name
        self.pdata_prefix = "p_"
        self.vdata_prefix = "v_"

    def get_name(self):
        return self._name

class TestBaseFlowStep_key_mgmt(unittest.TestCase):
    def setUp(self):
        self.step = TestFlowStep("test_step")
        st.session_state = {}

    def test_get_unique_key_prefix(self):
        self.assertEqual(self.step.get_unique_key_prefix(True), "p_test_step")
        self.assertEqual(self.step.get_unique_key_prefix(False), "v_test_step")

    def test_get_output_key(self):
        self.assertEqual(self.step.get_output_key(), "p_test_step_output_key")

    def test_format_internal_key(self):
        self.assertEqual(self.step.format_internal_key(True, "arg1", "arg2"), "p_test_step_arg1_arg2")
        self.assertEqual(self.step.format_internal_key(False, "arg1", "arg2"), "v_test_step_arg1_arg2")
        with self.assertRaises(ValueError):
            self.step.format_internal_key(True)

    def test_get_internal_keys(self):
        st.session_state["p_test_step_key1"] = "value1"
        st.session_state["v_test_step_key2"] = "value2"
        st.session_state["p_test_step_output_key"] = "output"
        st.session_state["other_key"] = "other"

        keys = self.step.get_internal_keys()
        self.assertEqual(set(keys), {"p_test_step_key1", "v_test_step_key2"})

        keys = self.step.get_internal_keys(include_pdata=False)
        self.assertEqual(set(keys), {"v_test_step_key2"})

        keys = self.step.get_internal_keys(include_vdata=False)
        self.assertEqual(set(keys), {"p_test_step_key1"})

    def test_get_output_subkeys(self):
        self.assertEqual(self.step.get_output_subkeys(), [])

class TestBaseFlowStep(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_app.get_step_config.return_value = {}
        self.step = BaseFlowStep("test_step", self.mock_app, {"default_key": "default_value"})

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
        self.assertEqual(self.step.format_internal_key(True, "arg1", "arg2"), "pdata_test_step_arg1_arg2")
        self.assertEqual(self.step.format_internal_key(False, "arg1", "arg2"), "vdata_test_step_arg1_arg2")

    def test_get_output_key(self):
        self.assertEqual(self.step.get_output_key(), "pdata_test_step_output_key")

if __name__ == '__main__':
    unittest.main()
