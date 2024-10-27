import unittest
import test_helper
test_helper.setup_path()
import unittest
from unittest.mock import MagicMock, patch
from utils.step_utils import BaseFlowStep, ChooseLLMFlavour, StepConfigException

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

    def test_format_item_key(self):
        self.assertEqual(self.step.format_item_key(True, "arg1", "arg2"), "pdata_test_step_arg1_arg2")
        self.assertEqual(self.step.format_item_key(False, "arg1", "arg2"), "vdata_test_step_arg1_arg2")

    @patch.object(BaseFlowStep, 'get_depends_on')
    @patch.object(BaseFlowStep, 'step_name_from_path')
    def test_input_data_ready(self, mock_step_name, mock_get_depends_on):
        mock_get_depends_on.return_value = {"dep1": "step1", "dep2": "step2"}
        mock_step_name.side_effect = lambda x: x

        mock_step1 = MagicMock()
        mock_step1.get_output_key.return_value = "pdata_step1"
        mock_step2 = MagicMock()
        mock_step2.get_output_key.return_value = "pdata_step2"

        self.step.app.get_step = MagicMock(side_effect=lambda x: mock_step1 if x == "step1" else mock_step2)

        state = {"pdata_step1": "data1", "pdata_step2": "data2"}
        self.assertTrue(self.step.input_data_ready(state))

        state = {"pdata_step1": "data1"}
        self.assertFalse(self.step.input_data_ready(state))

    def test_get_output_key(self):
        self.assertEqual(self.step.get_output_key(), "pdata_test_step")

if __name__ == '__main__':
    unittest.main()
