import unittest
import test_helper
test_helper.setup_path()
from unittest.mock import MagicMock, patch
from utils.step_utils import BaseFlowStep, StepConfigException
from utils.app_utils import BaseFlowApp

class TestBaseFlowApp(unittest.TestCase):

    def setUp(self):
        self.config = {
            'title': 'Test App',
            'description': 'Test Description',
            'steps': {
                'step1': {'class': 'TestStep1'},
                'step2': {'class': 'TestStep2'}
            }
        }
        self.state_manager = MagicMock()
        self.app = BaseFlowApp(self.config, self.state_manager)

    def test_init(self):
        self.assertEqual(self.app.config, self.config)
        self.assertEqual(self.app.state_manager, self.state_manager)
        self.assertEqual(len(self.app.steps), 0)

    @patch('streamlit.title')
    @patch('streamlit.write')
    def test_init_streamlit_calls(self, mock_write, mock_title):
        BaseFlowApp(self.config, self.state_manager)
        mock_title.assert_called_once_with('Test App')
        mock_write.assert_called_once_with('Test Description')

    def test_get_step_config(self):
        step_config = self.app.get_step_config('step1')
        self.assertEqual(step_config, {'class': 'TestStep1'})

    @patch('streamlit.session_state', {'key1': 'value1'})
    def test_get_state(self):
        state = self.app.get_state()
        self.assertEqual(state, {'key1': 'value1'})

    @patch('streamlit.session_state', {})
    def test_set_state(self):
        self.app.set_state('key2', 'value2')
        self.assertEqual(self.app.get_state(), {'key2': 'value2'})

    @patch('streamlit.session_state', {'key3': 'value3'})
    def test_clear_state(self):
        self.app.clear_state('key3')
        self.assertEqual(self.app.get_state(), {})

    def test_get_step(self):
        mock_step = MagicMock()
        self.app.steps['test_step'] = mock_step
        self.assertEqual(self.app.get_step('test_step'), mock_step)

    def test_add_step(self):
        mock_step = MagicMock(spec=BaseFlowStep)
        mock_step.get_name.return_value = 'new_step'
        mock_step.get_depends_on.return_value = {}
        self.app.add_step(mock_step)
        self.assertIn('new_step', self.app.steps)

    def test_add_step_duplicate(self):
        mock_step = MagicMock(spec=BaseFlowStep)
        mock_step.get_name.return_value = 'duplicate_step'
        mock_step.get_depends_on.return_value = {}
        self.app.add_step(mock_step)
        with self.assertRaises(StepConfigException):
            self.app.add_step(mock_step)

    def test_add_step_missing_dependency(self):
        mock_step = MagicMock(spec=BaseFlowStep)
        mock_step.get_name.return_value = 'test_step'
        mock_step.get_depends_on.return_value = {'dep': 'missing_step.output'}
        mock_step.step_name_from_path.return_value = 'missing_step'
        with self.assertRaises(StepConfigException):
            self.app.add_step(mock_step)

    @patch.object(BaseFlowStep, 'create_instance')
    def test_load_steps(self, mock_create_instance):
        mock_step1 = MagicMock(spec=BaseFlowStep)
        mock_step2 = MagicMock(spec=BaseFlowStep)
        mock_step1.get_name.return_value = 'step1'
        mock_step2.get_name.return_value = 'step2'
        mock_create_instance.side_effect = [mock_step1, mock_step2]
        
        self.app.load_steps()
        
        self.assertEqual(len(self.app.steps), 2)
        self.assertIn('step1', self.app.steps)
        self.assertIn('step2', self.app.steps)
        mock_create_instance.assert_any_call(class_name='TestStep1', name='step1', app=self.app)
        mock_create_instance.assert_any_call(class_name='TestStep2', name='step2', app=self.app)

    @patch.object(BaseFlowStep, 'input_data_ready')
    @patch.object(BaseFlowStep, 'show')
    def test_show_steps(self, mock_show, mock_input_data_ready):
        mock_step1 = MagicMock(spec=BaseFlowStep)
        mock_step2 = MagicMock(spec=BaseFlowStep)
        self.app.steps = {'step1': mock_step1, 'step2': mock_step2}
        mock_input_data_ready.return_value = True
        
        self.app.show_steps()
        
        mock_step1.show.assert_called_once()
        mock_step2.show.assert_called_once()
        self.state_manager.save_session_to_state.assert_called_once()

if __name__ == '__main__':
    unittest.main()